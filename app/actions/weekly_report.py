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


def compute_week_window_utc(now_utc: datetime | None = None, window_days: int | None = None) -> tuple[datetime, datetime]:
    settings = get_settings()
    now_utc = now_utc or datetime.now(timezone.utc)
    local_tz = ZoneInfo(settings.app_timezone)
    days = window_days if window_days is not None else settings.report_window_days

    local_now = now_utc.astimezone(local_tz)
    local_start = local_now - timedelta(days=days)

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
            "No mood entries in the report window.",
            "Stability cannot be inferred due to missing data.",
            "Add one mood check-in at a fixed hour each day.",
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


def summarize_tracker_activity(rows: list[dict]) -> dict:
    summary: dict = {"total_entries": len(rows), "by_type": {}}
    by_type: dict = summary["by_type"]

    for row in rows:
        thing_type = (row.get("type") or "unknown").strip().lower()
        slot = by_type.setdefault(thing_type, {"count": 0, "num_values": {}, "text_values": {}})
        slot["count"] += 1

        value_num = row.get("value_num")
        if value_num is not None:
            as_decimal = Decimal(str(value_num))
            normalized = str(int(as_decimal)) if as_decimal == int(as_decimal) else str(float(as_decimal))
            slot["num_values"][normalized] = slot["num_values"].get(normalized, 0) + 1

        value_text = row.get("value_text")
        if value_text:
            normalized_text = str(value_text).strip().lower()
            slot["text_values"][normalized_text] = slot["text_values"].get(normalized_text, 0) + 1

    return summary


def render_tracker_snapshot(summary: dict, max_types: int = 5, max_values: int = 4) -> str:
    by_type = summary.get("by_type", {})
    if not by_type:
        return "No tracker entries in window."

    ordered = sorted(by_type.items(), key=lambda item: item[1].get("count", 0), reverse=True)
    lines: list[str] = []
    for tracker_type, data in ordered[:max_types]:
        count = data.get("count", 0)
        parts: list[str] = [f"{tracker_type}={count}"]
        text_values = data.get("text_values", {})
        if text_values:
            top_text = sorted(text_values.items(), key=lambda kv: kv[1], reverse=True)[:max_values]
            parts.append("text:" + ", ".join([f"{k}({v})" for k, v in top_text]))
        num_values = data.get("num_values", {})
        if num_values:
            top_num = sorted(num_values.items(), key=lambda kv: kv[1], reverse=True)[:max_values]
            parts.append("num:" + ", ".join([f"{k}({v})" for k, v in top_num]))
        lines.append(" - " + " | ".join(parts))
    return "\n".join(lines)
