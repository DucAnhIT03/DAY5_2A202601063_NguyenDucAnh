from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from pymongo import ASCENDING, MongoClient
from pymongo.errors import PyMongoError

try:
    from codebase.core import Segment, TranscriptDocument
except ModuleNotFoundError:
    from core import Segment, TranscriptDocument


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

    def close(self) -> None:
        self.client.close()
