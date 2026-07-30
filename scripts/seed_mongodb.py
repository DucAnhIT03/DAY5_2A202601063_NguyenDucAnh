from __future__ import annotations

import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from codebase.core import session_files, transcript_from_path  # noqa: E402
from codebase.mongo_repository import (  # noqa: E402
    MongoTranscriptRepository,
    mongo_database,
    mongo_uri,
)


QUIZ_BANK = [
    "Quan hệ giữa AI, machine learning, deep learning và generative AI là gì?",
    "Vì sao symbolic AI chạm trần?",
    "Deep learning khác feature engineering truyền thống ở điểm nào?",
]


def main() -> None:
    repository = MongoTranscriptRepository(mongo_uri(), mongo_database())
    repository.ping()
    repository.ensure_indexes()

    now = datetime.now(timezone.utc)
    segment_count = 0
    for session_order, path in enumerate(session_files(), start=1):
        transcript = transcript_from_path(path)
        raw = path.read_bytes()
        repository.transcripts.update_one(
            {"name": transcript.name},
            {
                "$set": {
                    "schema_version": 1,
                    "session_id": path.stem,
                    "session_order": session_order,
                    "name": transcript.name,
                    "title": transcript.title,
                    "segments": [
                        {"id": segment.id, "text": segment.text}
                        for segment in transcript.segments
                    ],
                    "segment_count": len(transcript.segments),
                    "source": "vlearn-pack-anonymized",
                    "source_sha256": hashlib.sha256(raw).hexdigest(),
                    "updated_at": now,
                },
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )
        segment_count += len(transcript.segments)

    repository.quiz_bank.update_one(
        {"bank_id": "vlearn-core"},
        {
            "$set": {
                "schema_version": 1,
                "questions": QUIZ_BANK,
                "updated_at": now,
            },
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )

    snapshot = repository.snapshot()
    repository.close()
    print(
        f"MongoDB ready: database={snapshot.database}, "
        f"transcripts={len(snapshot.transcripts)}, segments={segment_count}, "
        f"quiz_questions={len(snapshot.quiz_questions)}"
    )


if __name__ == "__main__":
    main()
