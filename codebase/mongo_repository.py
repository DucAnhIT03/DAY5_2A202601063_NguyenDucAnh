from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from pymongo import ASCENDING, MongoClient
from pymongo.errors import PyMongoError

try:
    from codebase.core import (
        Segment,
        TranscriptDocument,
        normalize_confidence,
        transcript_fingerprint,
    )
except ModuleNotFoundError:
    from core import (
        Segment,
        TranscriptDocument,
        normalize_confidence,
        transcript_fingerprint,
    )


DEFAULT_MONGO_URI = "mongodb://127.0.0.1:27020"
DEFAULT_MONGO_DATABASE = "catchup_assistant"


class MongoUnavailable(RuntimeError):
    """A sanitized database error safe to display in the application."""


@dataclass(frozen=True)
class MongoSnapshot:
    transcripts: tuple[TranscriptDocument, ...]
    quiz_questions: tuple[str, ...]
    database: str
    collection: str
    segment_count: int


def snapshot_to_cache_payload(snapshot: MongoSnapshot) -> dict[str, Any]:
    """Convert domain objects to plain values that Streamlit can cache reliably."""
    return {
        "transcripts": [
            {
                "name": transcript.name,
                "title": transcript.title,
                "fingerprint": transcript.fingerprint,
                "segments": [
                    {"id": segment.id, "text": segment.text}
                    for segment in transcript.segments
                ],
            }
            for transcript in snapshot.transcripts
        ],
        "quiz_questions": list(snapshot.quiz_questions),
        "database": snapshot.database,
        "collection": snapshot.collection,
        "segment_count": snapshot.segment_count,
    }


def snapshot_from_cache_payload(payload: dict[str, Any]) -> MongoSnapshot:
    """Restore the typed snapshot after retrieving its plain cached payload."""
    transcripts = tuple(
        document_to_transcript(document)
        for document in payload.get("transcripts", [])
    )
    return MongoSnapshot(
        transcripts=transcripts,
        quiz_questions=tuple(payload.get("quiz_questions", [])),
        database=str(payload.get("database", DEFAULT_MONGO_DATABASE)),
        collection=str(payload.get("collection", "transcripts")),
        segment_count=int(
            payload.get(
                "segment_count",
                sum(len(transcript.segments) for transcript in transcripts),
            )
        ),
    )


def mongo_uri() -> str:
    return os.getenv("MONGO_URI", DEFAULT_MONGO_URI)


def mongo_database() -> str:
    return os.getenv("MONGO_DATABASE", DEFAULT_MONGO_DATABASE)


def document_to_transcript(document: dict[str, Any]) -> TranscriptDocument:
    segments = tuple(
        Segment(id=str(item["id"]), text=str(item["text"]))
        for item in document.get("segments", [])
        if item.get("id") and item.get("text")
    )
    if not segments:
        raise ValueError("Transcript trong MongoDB không có đoạn nội dung hợp lệ.")

    name = str(document.get("name") or document.get("session_id") or "")
    if not name:
        raise ValueError("Transcript trong MongoDB thiếu định danh.")
    return TranscriptDocument(
        name=name,
        title=str(document.get("title") or name),
        segments=segments,
        fingerprint=str(
            document.get("fingerprint") or document.get("source_sha256") or ""
        ),
    )


class MongoTranscriptRepository:
    def __init__(self, uri: str | None = None, database: str | None = None) -> None:
        self.database_name = database or mongo_database()
        self.client = MongoClient(
            uri or mongo_uri(),
            appname="catchup-assistant",
            connectTimeoutMS=2_000,
            serverSelectionTimeoutMS=2_000,
        )
        self.database = self.client[self.database_name]
        self.transcripts = self.database["transcripts"]
        self.quiz_bank = self.database["quiz_bank"]
        self.analyses = self.database["analyses"]

    def ping(self) -> None:
        try:
            self.client.admin.command("ping")
        except PyMongoError as error:
            raise MongoUnavailable(
                "Không kết nối được MongoDB của Catch-up Assistant."
            ) from error

    def ensure_indexes(self) -> None:
        self.transcripts.create_index(
            [("session_order", ASCENDING)], name="session_order_idx"
        )
        self.transcripts.create_index(
            [("name", ASCENDING)], unique=True, name="transcript_name_unique"
        )
        self.analyses.create_index(
            [("transcript_name", ASCENDING), ("transcript_fingerprint", ASCENDING)],
            unique=True,
            name="analysis_transcript_version_unique",
        )

    def snapshot(self) -> MongoSnapshot:
        try:
            self.ping()
            documents = list(
                self.transcripts.find(
                    {},
                    {
                        "_id": 0,
                        "name": 1,
                        "session_id": 1,
                        "title": 1,
                        "segments": 1,
                        "source_sha256": 1,
                        "session_order": 1,
                    },
                ).sort([("session_order", ASCENDING), ("name", ASCENDING)])
            )
            transcripts = tuple(document_to_transcript(item) for item in documents)
            if not transcripts:
                raise MongoUnavailable(
                    "MongoDB đang trống. Hãy chạy scripts/seed_mongodb.py trước."
                )

            quiz_document = self.quiz_bank.find_one(
                {"bank_id": "vlearn-core"}, {"_id": 0, "questions": 1}
            )
            questions = tuple(
                str(question)
                for question in (quiz_document or {}).get("questions", [])
                if str(question).strip()
            )
            return MongoSnapshot(
                transcripts=transcripts,
                quiz_questions=questions,
                database=self.database_name,
                collection=self.transcripts.name,
                segment_count=sum(len(item.segments) for item in transcripts),
            )
        except MongoUnavailable:
            raise
        except (PyMongoError, ValueError, KeyError, TypeError) as error:
            raise MongoUnavailable(
                "Không thể đọc dữ liệu Catch-up Assistant từ MongoDB."
            ) from error

    def get_analysis(self, transcript: TranscriptDocument) -> dict[str, Any] | None:
        fingerprint = transcript_fingerprint(transcript)
        try:
            document = self.analyses.find_one(
                {
                    "transcript_name": transcript.name,
                    "transcript_fingerprint": fingerprint,
                    "status": "completed",
                },
                {
                    "_id": 0,
                    "points": 1,
                    "model": 1,
                    "generated_at": 1,
                    "quiz_question_count": 1,
                },
            )
        except PyMongoError as error:
            raise MongoUnavailable("Không thể đọc phân tích AI từ MongoDB.") from error
        if not document:
            return None

        valid_ids = {segment.id for segment in transcript.segments}
        safe_points: list[dict[str, Any]] = []
        for point in document.get("points", []):
            citations = [
                str(citation)
                for citation in point.get("citations", [])
                if str(citation) in valid_ids
            ]
            if not citations:
                continue
            safe_points.append(
                {
                    "title": str(point.get("title", "Trọng điểm")),
                    "summary": str(point.get("summary", "")),
                    "citations": citations,
                    "quiz": bool(point.get("quiz", False)),
                    "quiz_reason": str(point.get("quiz_reason", "")),
                    "confidence": normalize_confidence(point.get("confidence")),
                    "origin": "gemini-mongodb",
                }
            )
        if not 3 <= len(safe_points) <= 5:
            return None

        generated_at = document.get("generated_at")
        return {
            "points": safe_points,
            "model": str(document.get("model", "gemini-2.5-flash")),
            "generated_at": (
                generated_at.isoformat()
                if isinstance(generated_at, datetime)
                else str(generated_at or "")
            ),
            "quiz_question_count": int(document.get("quiz_question_count", 0)),
        }

    def save_analysis(
        self,
        transcript: TranscriptDocument,
        points: list[dict[str, Any]],
        *,
        model: str = "gemini-2.5-flash",
        quiz_question_count: int = 0,
    ) -> None:
        valid_ids = {segment.id for segment in transcript.segments}
        if not 3 <= len(points) <= 5:
            raise ValueError("Phân tích phải có từ 3 đến 5 trọng điểm.")
        if any(
            not point.get("citations")
            or not set(point["citations"]).issubset(valid_ids)
            for point in points
        ):
            raise ValueError("Phân tích chứa mã trích dẫn không hợp lệ.")

        now = datetime.now(timezone.utc)
        try:
            self.analyses.update_one(
                {
                    "transcript_name": transcript.name,
                    "transcript_fingerprint": transcript_fingerprint(transcript),
                },
                {
                    "$set": {
                        "schema_version": 1,
                        "status": "completed",
                        "source": "gemini-api",
                        "model": model,
                        "points": points,
                        "quiz_question_count": quiz_question_count,
                        "generated_at": now,
                        "updated_at": now,
                    },
                    "$setOnInsert": {"created_at": now},
                },
                upsert=True,
            )
        except PyMongoError as error:
            raise MongoUnavailable("Không thể lưu phân tích AI vào MongoDB.") from error

    def close(self) -> None:
        self.client.close()
