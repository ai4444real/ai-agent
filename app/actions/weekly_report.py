from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from statistics import mean
from zoneinfo import ZoneInfo

from app.settings import get_settings


@dataclass
class WeeklyReportData:
    start_utc: datetime
    end_utc: datetime
    values: list[int]


def compute_week_window_utc(now_utc: datetime | None = None) -> tuple[datetime, datetime]:
    settings = get_settings()
    now_utc = now_utc or datetime.now(timezone.utc)
    local_tz = ZoneInfo(settings.app_timezone)

    local_now = now_utc.astimezone(local_tz)
    local_start = local_now - timedelta(days=7)

    return local_start.astimezone(timezone.utc), local_now.astimezone(timezone.utc)


def extract_mood_values(rows: list[dict]) -> list[int]:
    values: list[int] = []
    for row in rows:
        value = row.get("value_num")
        if value is None:
            continue
        as_decimal = Decimal(str(value))
        if as_decimal == int(as_decimal):
            values.append(int(as_decimal))
    return values


def calculate_metrics(values: list[int]) -> dict:
    count = len(values)
    if count == 0:
        return {
            "count": 0,
            "avg": "n/a",
            "min": "n/a",
            "max": "n/a",
            "trend": "n/a",
        }

    avg_value = round(mean(values), 2)
    min_value = min(values)
    max_value = max(values)

    first_slice = values[:3]
    last_slice = values[-3:]
    trend_value = round(mean(last_slice) - mean(first_slice), 2)

    return {
        "count": count,
        "avg": avg_value,
        "min": min_value,
        "max": max_value,
        "trend": trend_value,
    }


def deterministic_signal_and_action(metrics: dict) -> tuple[str, str, str]:
    count = metrics["count"]
    trend = metrics["trend"]

    if count == 0:
        return (
            "No mood entries in last 7 days.",
            "Stability cannot be inferred due to missing data.",
            "Add one mood check-in at a fixed hour each day this week.",
        )

    if count < 4:
        summary = "Tracking volume is low."
    else:
        summary = "Tracking volume is sufficient for a rough trend."

    if isinstance(trend, (int, float)) and trend < 0:
        signal = "Mood trend is slightly down versus the first half of the week."
        micro_action = "Block one 15-minute recovery slot tomorrow morning and protect it."
    elif isinstance(trend, (int, float)) and trend > 0:
        signal = "Mood trend is up versus the first half of the week."
        micro_action = "Repeat the most stable routine from the strongest day once next week."
    else:
        signal = "Mood trend is flat across the week."
        micro_action = "Introduce one small variation in routine and re-check mood the same day."

    return summary, signal, micro_action


def render_weekly_report(metrics: dict, summary: str, signal: str, micro_action: str) -> str:
    template_path = Path(__file__).resolve().parents[1] / "templates" / "weekly_report_deterministic.txt"
    template = template_path.read_text(encoding="utf-8")
    return template.format(
        summary=summary,
        count=metrics["count"],
        avg=metrics["avg"],
        min=metrics["min"],
        max=metrics["max"],
        trend=metrics["trend"],
        signal=signal,
        micro_action=micro_action,
    ).strip()
