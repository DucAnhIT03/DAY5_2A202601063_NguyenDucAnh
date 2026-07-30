from pathlib import Path

from codebase.core import answer_question, default_summary, load_segments


TRANSCRIPT = Path("data/vlearn-pack/transcript/transcript-04-clean.md")


def test_parser_keeps_source_ids():
    segments = load_segments(TRANSCRIPT)
    assert len(segments) >= 90
    assert segments[0].id == "T04-001"


def test_demo_summary_has_three_to_five_grounded_points():
    valid = {segment.id for segment in load_segments(TRANSCRIPT)}
    summary = default_summary(TRANSCRIPT)
    assert 3 <= len(summary) <= 5
    assert all(set(item["citations"]) <= valid for item in summary)


def test_out_of_scope_question_is_refused_without_api_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    result = answer_question(TRANSCRIPT, "Buổi này hướng dẫn nấu phở thế nào?")
    assert result["grounded"] is False
    assert result["citations"] == []

