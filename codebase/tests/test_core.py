import pickle
from pathlib import Path

import pytest

from codebase import core
from codebase.core import (
    answer_question,
    answer_with_key_rotation,
    default_summary,
    load_segments,
    masked_key_label,
    normalize_confidence,
    parse_api_keys,
    summarize_with_key_rotation,
    transcript_fingerprint,
    transcript_from_path,
)
from codebase.mongo_repository import (
    MongoSnapshot,
    document_to_transcript,
    snapshot_from_cache_payload,
    snapshot_to_cache_payload,
)


TRANSCRIPT = Path("data/vlearn-pack/transcript/transcript-04-clean.md")


def test_parser_keeps_source_ids():
    segments = load_segments(TRANSCRIPT)
    assert len(segments) >= 90
    assert segments[0].id == "T04-001"


def test_extractive_summary_uses_only_real_transcript_segments():
    valid = {segment.id for segment in load_segments(TRANSCRIPT)}
    summary = default_summary(TRANSCRIPT)
    assert 3 <= len(summary) <= 5
    assert all(set(item["citations"]) <= valid for item in summary)
    assert all(item["origin"] == "transcript-extractive" for item in summary)
    assert all(item["quiz"] is False for item in summary)


def test_normalized_transcript_keeps_parsed_segments_in_memory():
    transcript = transcript_from_path(TRANSCRIPT)
    assert transcript.name == TRANSCRIPT.name
    assert load_segments(transcript)[0].id == "T04-001"
    assert len(transcript_fingerprint(transcript)) == 64


def test_mongo_document_is_mapped_to_a_grounded_transcript():
    transcript = document_to_transcript(
        {
            "name": "transcript-99-clean.md",
            "title": "Buổi kiểm thử",
            "source_sha256": "abc123",
            "segments": [{"id": "T99-001", "text": "Nội dung có căn cứ."}],
        }
    )
    assert transcript.title == "Buổi kiểm thử"
    assert transcript.segments[0].id == "T99-001"
    assert transcript.fingerprint == "abc123"


def test_mongo_cache_payload_only_contains_pickle_safe_values():
    transcript = transcript_from_path(TRANSCRIPT)
    snapshot = MongoSnapshot(
        transcripts=(transcript,),
        quiz_questions=("Câu hỏi kiểm thử",),
        database="catchup_assistant",
        collection="transcripts",
        segment_count=len(transcript.segments),
    )
    payload = pickle.loads(pickle.dumps(snapshot_to_cache_payload(snapshot)))
    restored = snapshot_from_cache_payload(payload)
    assert restored.transcripts[0].name == transcript.name
    assert restored.transcripts[0].fingerprint == transcript.fingerprint
    assert restored.segment_count == len(transcript.segments)


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


def test_confidence_labels_are_normalized_for_vietnamese_ui():
    assert normalize_confidence("high") == "cao"
    assert normalize_confidence("medium") == "vừa"
    assert normalize_confidence("low") == "thấp"


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
    attempts = []

    def fake_summary(path, quiz_questions, api_key):
        calls.append(api_key)
        if api_key == "quota-key":
            raise QuotaError()
        return [{"title": "ok", "citations": ["T04-015"]}]

    monkeypatch.setattr(core, "summarize_with_gemini", fake_summary)
    rotated = summarize_with_key_rotation(
        TRANSCRIPT,
        [],
        ["quota-key", "working-key", "third-key"],
        cursor=0,
        on_attempt=lambda attempt, total, slot: attempts.append((attempt, total, slot)),
    )
    assert calls == ["quota-key", "working-key"]
    assert attempts == [(1, 3, 0), (2, 3, 1)]
    assert rotated.used_slot == 1
    assert rotated.next_cursor == 2
    assert rotated.attempts == 2


def test_key_rotation_stops_on_local_response_validation_error(monkeypatch):
    calls = []

    def malformed_summary(path, quiz_questions, api_key):
        calls.append(api_key)
        raise ValueError("malformed JSON")

    monkeypatch.setattr(core, "summarize_with_gemini", malformed_summary)
    with pytest.raises(core.KeyPoolError):
        summarize_with_key_rotation(
            TRANSCRIPT,
            [],
            ["first-key", "second-key", "third-key"],
        )
    assert calls == ["first-key"]


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


def test_greeting_gets_a_friendly_reply_without_consuming_key():
    rotated = answer_with_key_rotation(
        TRANSCRIPT,
        "hi",
        ["unused-key-1", "unused-key-2"],
        cursor=1,
    )
    assert rotated.value["mode"] == "conversation"
    assert "Chào bạn" in rotated.value["answer"]
    assert rotated.used_slot is None
    assert rotated.next_cursor == 1


def test_overview_question_is_grounded_in_real_transcript_without_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    result = answer_question(TRANSCRIPT, "Tóm tắt buổi học này")
    assert result["mode"] == "extractive"
    assert result["grounded"] is True
    assert result["citations"]
