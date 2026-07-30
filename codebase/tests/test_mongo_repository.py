from datetime import datetime, timezone

from codebase.core import Segment, TranscriptDocument
from codebase.mongo_repository import MongoTranscriptRepository


TRANSCRIPT = TranscriptDocument(
    name="lesson.md",
    title="Buổi thật",
    segments=(
        Segment("T99-001", "Nội dung thật thứ nhất."),
        Segment("T99-002", "Nội dung thật thứ hai."),
        Segment("T99-003", "Nội dung thật thứ ba."),
    ),
    fingerprint="fingerprint-123",
)


def _points():
    return [
        {
            "title": f"Điểm {index}",
            "summary": "Tóm tắt có nguồn.",
            "citations": [f"T99-00{index}"],
            "quiz": False,
            "quiz_reason": "",
            "confidence": "cao",
        }
        for index in range(1, 4)
    ]


def test_stored_analysis_filters_invalid_citations():
    class Analyses:
        def find_one(self, query, projection):
            points = _points()
            points.append(
                {
                    "title": "Sai nguồn",
                    "summary": "Không hợp lệ",
                    "citations": ["T00-999"],
                }
            )
            return {
                "points": points,
                "model": "gemini-test",
                "generated_at": datetime(2026, 7, 31, tzinfo=timezone.utc),
                "quiz_question_count": 0,
            }

    repository = MongoTranscriptRepository.__new__(MongoTranscriptRepository)
    repository.analyses = Analyses()
    result = repository.get_analysis(TRANSCRIPT)
    assert result is not None
    assert len(result["points"]) == 3
    assert all(point["origin"] == "gemini-mongodb" for point in result["points"])


def test_save_analysis_upserts_without_api_keys():
    class Analyses:
        def __init__(self):
            self.query = None
            self.update = None

        def update_one(self, query, update, upsert):
            self.query = query
            self.update = update
            assert upsert is True

    repository = MongoTranscriptRepository.__new__(MongoTranscriptRepository)
    repository.analyses = Analyses()
    repository.save_analysis(TRANSCRIPT, _points(), quiz_question_count=0)

    assert repository.analyses.query == {
        "transcript_name": "lesson.md",
        "transcript_fingerprint": "fingerprint-123",
    }
    stored = repository.analyses.update["$set"]
    assert stored["source"] == "gemini-api"
    assert "api_key" not in stored
