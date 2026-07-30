from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from codebase.core import summarize_with_key_rotation  # noqa: E402
from codebase.key_vault import load_key_pool  # noqa: E402
from codebase.mongo_repository import MongoTranscriptRepository  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate grounded Gemini analyses and persist them in MongoDB."
    )
    parser.add_argument(
        "--session",
        default="transcript-04-clean.md",
        help="Transcript name in MongoDB.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Analyze every transcript instead of one session.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    api_keys = load_key_pool()
    if not api_keys:
        raise SystemExit("No encrypted Gemini key pool found on this Windows account.")

    repository = MongoTranscriptRepository()
    snapshot = repository.snapshot()
    targets = list(snapshot.transcripts)
    if not args.all:
        targets = [item for item in targets if item.name == args.session]
    if not targets:
        raise SystemExit(f"Transcript not found in MongoDB: {args.session}")

    cursor = 0
    for transcript in targets:
        print(
            f"Analyzing {transcript.name}: segments={len(transcript.segments)}, "
            f"key_pool={len(api_keys)}"
        )

        def report_attempt(attempt: int, total: int, slot: int) -> None:
            print(f"  attempt={attempt}/{total}, slot={slot + 1}", flush=True)

        rotation = summarize_with_key_rotation(
            transcript,
            list(snapshot.quiz_questions),
            api_keys,
            cursor,
            on_attempt=report_attempt,
        )
        repository.save_analysis(
            transcript,
            rotation.value,
            model="gemini-2.5-flash",
            quiz_question_count=len(snapshot.quiz_questions),
        )
        cursor = rotation.next_cursor
        print(
            f"  saved={len(rotation.value)} points, used_slot={rotation.used_slot + 1}, "
            f"attempts={rotation.attempts}"
        )

    repository.close()


if __name__ == "__main__":
    main()
