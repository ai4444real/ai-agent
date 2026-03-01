from app.actions.weekly_report import summarize_tracker_activity


def test_summarize_tracker_activity_counts_types_and_values():
    rows = [
        {"type": "mood", "value_num": 4},
        {"type": "mood", "value_num": 4},
        {"type": "mood", "value_num": 2},
        {"type": "allenamento", "value_text": "bene"},
        {"type": "allenamento", "value_text": "male"},
        {"type": "allenamento", "value_text": "bene"},
    ]

    summary = summarize_tracker_activity(rows)

    assert summary["total_entries"] == 6
    assert summary["by_type"]["mood"]["count"] == 3
    assert summary["by_type"]["mood"]["num_values"]["4"] == 2
    assert summary["by_type"]["allenamento"]["count"] == 3
    assert summary["by_type"]["allenamento"]["text_values"]["bene"] == 2
