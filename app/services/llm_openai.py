from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from openai import OpenAI

from app.settings import get_settings


class OpenAIReportHelper:
    def __init__(self) -> None:
        self._settings = get_settings()
        self.last_usage: dict[str, Any] = self._zero_usage()

    @staticmethod
    def _zero_usage() -> dict[str, Any]:
        return {
            "requests": 0,
            "model": None,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
        }

    @staticmethod
    def _usage_from_response(response: Any, model: str | None = None) -> dict[str, Any]:
        usage = getattr(response, "usage", None)
        input_tokens = 0
        output_tokens = 0
        total_tokens = 0
        if usage is not None:
            input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
            output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
            total_tokens = int(getattr(usage, "total_tokens", 0) or (input_tokens + output_tokens))
        return {
            "requests": 1,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
        }

    def generate_signal_and_micro_action(self, report_payload: dict, rules_text: str | None = None) -> tuple[str, str] | None:
        self.last_usage = self._zero_usage()
        if not self._settings.openai_api_key:
            return None

        client = OpenAI(api_key=self._settings.openai_api_key)
        prompts_dir = Path(__file__).resolve().parents[1] / "prompts"
        system_prompt = (prompts_dir / "weekly_report_system.md").read_text(encoding="utf-8")
        user_template = (prompts_dir / "weekly_report_user.md").read_text(encoding="utf-8")
        user_prompt = user_template.format(metrics_json=json.dumps(report_payload, ensure_ascii=True))
        if rules_text:
            user_prompt += f"\n\nCustom rules context:\n{rules_text[:8000]}"

        response = client.responses.create(
            model=self._settings.openai_model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        self.last_usage = self._usage_from_response(response, model=self._settings.openai_model)
        text = (response.output_text or "").strip()
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if len(lines) < 2:
            return None
        signal = lines[0].removeprefix("Signal:").strip()
        micro_action = lines[1].removeprefix("Micro-action:").strip()
        if not signal or not micro_action:
            return None
        return signal, micro_action

    def generate_smart_weekly_report(
        self,
        context_payload: dict[str, Any],
        rules_text: str | None,
        tool_executor: Callable[[str, dict[str, Any]], dict[str, Any]],
        max_rounds: int = 6,
    ) -> tuple[str | None, list[dict[str, Any]]]:
        self.last_usage = self._zero_usage()
        if not self._settings.openai_api_key:
            return None, []

        client = OpenAI(api_key=self._settings.openai_api_key)
        prompts_dir = Path(__file__).resolve().parents[1] / "prompts"
        system_prompt = (prompts_dir / "weekly_report_smart_system.md").read_text(encoding="utf-8")
        user_template = (prompts_dir / "weekly_report_smart_user.md").read_text(encoding="utf-8")
        user_prompt = user_template.format(context_json=json.dumps(context_payload, ensure_ascii=False))
        if rules_text:
            user_prompt += f"\n\nRegole utente:\n{rules_text[:12000]}"

        tools = [
            {
                "type": "function",
                "name": "get_window_coverage",
                "description": "Ritorna copertura dati su una finestra in giorni: giorni con dati, primo/ultimo evento e conteggio.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "days": {"type": "integer", "minimum": 1, "maximum": 31},
                    },
                    "required": ["days"],
                    "additionalProperties": False,
                },
            },
            {
                "type": "function",
                "name": "get_daily_counts",
                "description": "Ritorna conteggi per giorno per un tipo specifico nella finestra richiesta.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "days": {"type": "integer", "minimum": 1, "maximum": 31},
                        "type": {"type": "string", "minLength": 1},
                    },
                    "required": ["days", "type"],
                    "additionalProperties": False,
                },
            },
        ]

        response = client.responses.create(
            model=self._settings.openai_model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            tools=tools,
        )
        aggregate_usage = self._usage_from_response(response, model=self._settings.openai_model)

        tool_trace: list[dict[str, Any]] = []
        rounds = 0
        while rounds < max_rounds:
            rounds += 1
            outputs = getattr(response, "output", []) or []
            function_calls = [item for item in outputs if getattr(item, "type", None) == "function_call"]
            if not function_calls:
                text = (response.output_text or "").strip()
                self.last_usage = aggregate_usage
                return (text or None), tool_trace

            tool_outputs = []
            for call in function_calls:
                name = getattr(call, "name", "")
                call_id = getattr(call, "call_id", "")
                raw_args = getattr(call, "arguments", "{}") or "{}"
                try:
                    args = json.loads(raw_args)
                except Exception:
                    args = {}

                result = tool_executor(name, args)
                tool_trace.append({"name": name, "args": args, "result": result})
                tool_outputs.append(
                    {
                        "type": "function_call_output",
                        "call_id": call_id,
                        "output": json.dumps(result, ensure_ascii=False),
                    }
                )

            response = client.responses.create(
                model=self._settings.openai_model,
                previous_response_id=response.id,
                input=tool_outputs,
                tools=tools,
            )
            step_usage = self._usage_from_response(response, model=self._settings.openai_model)
            aggregate_usage["requests"] += step_usage["requests"]
            aggregate_usage["input_tokens"] += step_usage["input_tokens"]
            aggregate_usage["output_tokens"] += step_usage["output_tokens"]
            aggregate_usage["total_tokens"] += step_usage["total_tokens"]

        text = (response.output_text or "").strip()
        self.last_usage = aggregate_usage
        return (text or None), tool_trace
