from pathlib import Path

from codebase import core
from codebase.core import (
    answer_question,
    answer_with_key_rotation,
    default_summary,
    load_segments,
    masked_key_label,
    parse_api_keys,
    summarize_with_key_rotation,
)


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


def test_key_parser_deduplicates_and_masks():
    keys = parse_api_keys("alpha-key-12345, beta-key-67890; alpha-key-12345")
    assert keys == ["alpha-key-12345", "beta-key-67890"]
    assert masked_key_label(keys[0]) == "alph••••2345"


def test_key_parser_accepts_one_key_per_line_and_comments():
    raw = """# Gemini pool
first-key-12345

second-key-67890
first-key-12345  # duplicate
"""
    assert parse_api_keys(raw) == ["first-key-12345", "second-key-67890"]


def test_key_rotation_fails_over_and_advances_cursor(monkeypatch):
    class QuotaError(Exception):
        code = 429

    calls = []

    def fake_summary(path, quiz_questions, api_key):
        calls.append(api_key)
        if api_key == "quota-key":
            raise QuotaError()
        return [{"title": "ok", "citations": ["T04-015"]}]

    monkeypatch.setattr(core, "summarize_with_gemini", fake_summary)
    rotated = summarize_with_key_rotation(
        TRANSCRIPT, [], ["quota-key", "working-key", "third-key"], cursor=0
    )
    assert calls == ["quota-key", "working-key"]
    assert rotated.used_slot == 1
    assert rotated.next_cursor == 2
    assert rotated.attempts == 2


def test_guardrail_does_not_consume_key_slot():
    rotated = answer_with_key_rotation(
        TRANSCRIPT,
        "Buổi này hướng dẫn nấu phở thế nào?",
        ["unused-key-1", "unused-key-2"],
        cursor=1,
    )
    assert rotated.value["grounded"] is False
    assert rotated.used_slot is None
    assert rotated.next_cursor == 1
