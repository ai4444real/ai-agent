from __future__ import annotations

import json
from pathlib import Path

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
