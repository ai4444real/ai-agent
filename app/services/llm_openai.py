from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from openai import OpenAI

from app.settings import get_settings


class OpenAIReportHelper:
    def __init__(self) -> None:
        self._settings = get_settings()

    def generate_signal_and_micro_action(self, report_payload: dict, rules_text: str | None = None) -> tuple[str, str] | None:
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

        tool_trace: list[dict[str, Any]] = []
        rounds = 0
        while rounds < max_rounds:
            rounds += 1
            outputs = getattr(response, "output", []) or []
            function_calls = [item for item in outputs if getattr(item, "type", None) == "function_call"]
            if not function_calls:
                text = (response.output_text or "").strip()
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

        text = (response.output_text or "").strip()
        return (text or None), tool_trace
