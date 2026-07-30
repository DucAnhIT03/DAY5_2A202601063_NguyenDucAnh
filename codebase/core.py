from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, TypeAlias


ROOT = Path(__file__).resolve().parents[1]
TRANSCRIPT_DIR = ROOT / "data" / "vlearn-pack" / "transcript"
LOG_DIR = Path(__file__).resolve().parent / "logs"
SEGMENT_RE = re.compile(r"\*\*\[(T\d{2}-\d{3})\]\*\*\s*(.*?)(?=\n\*\*\[T|\Z)", re.S)
STOPWORDS = {
    "buổi", "này", "thế", "nào", "như", "thế nào", "được", "không", "hướng",
    "dẫn", "trong", "về", "cách", "có", "nói", "cho", "mình", "là", "và",
}


@dataclass(frozen=True)
class Segment:
    id: str
    text: str


@dataclass(frozen=True)
class TranscriptDocument:
    """Normalized transcript with a stable fingerprint of its real source."""

    name: str
    title: str
    segments: tuple[Segment, ...]
    fingerprint: str = ""


TranscriptSource: TypeAlias = Path | TranscriptDocument


@dataclass(frozen=True)
class RotationResult:
    value: Any
    next_cursor: int
    used_slot: int | None
    attempts: int


class KeyPoolError(RuntimeError):
    """Safe error that never includes an API key or raw provider response."""


AttemptCallback: TypeAlias = Callable[[int, int, int], None]


def session_files() -> list[Path]:
    return sorted(TRANSCRIPT_DIR.glob("transcript-*-clean.md"))


def transcript_from_path(path: Path) -> TranscriptDocument:
    raw_bytes = path.read_bytes()
    raw = raw_bytes.decode("utf-8")
    title_line = next((line for line in raw.splitlines() if line.startswith("# ")), path.stem)
    return TranscriptDocument(
        name=path.name,
        title=title_line.removeprefix("# ").strip(),
        segments=tuple(
            Segment(segment_id, re.sub(r"\s+", " ", text).strip())
            for segment_id, text in SEGMENT_RE.findall(raw)
        ),
        fingerprint=hashlib.sha256(raw_bytes).hexdigest(),
    )


def local_transcripts() -> list[TranscriptDocument]:
    return [transcript_from_path(path) for path in session_files()]


def load_segments(source: TranscriptSource) -> list[Segment]:
    if isinstance(source, TranscriptDocument):
        return list(source.segments)
    raw = source.read_text(encoding="utf-8")
    return [
        Segment(segment_id, re.sub(r"\s+", " ", text).strip())
        for segment_id, text in SEGMENT_RE.findall(raw)
    ]


def segment_map(source: TranscriptSource) -> dict[str, Segment]:
    return {segment.id: segment for segment in load_segments(source)}


def transcript_fingerprint(source: TranscriptSource) -> str:
    if isinstance(source, TranscriptDocument) and source.fingerprint:
        return source.fingerprint
    if isinstance(source, Path):
        return hashlib.sha256(source.read_bytes()).hexdigest()
    payload = "\n".join(f"{segment.id}:{segment.text}" for segment in source.segments)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def default_summary(source: TranscriptSource) -> list[dict[str, Any]]:
    """Build a grounded extractive preview directly from the real transcript."""
    segments = [
        s for s in load_segments(source)
        if len(s.text) > 180 and "[Hoạt động lớp:" not in s.text
    ]
    picks = segments[:: max(1, len(segments) // 4)][:4]
    return [
        {
            "title": s.text.split(".")[0][:90],
            "summary": s.text[:260] + ("…" if len(s.text) > 260 else ""),
            "citations": [s.id],
            "quiz": False,
            "quiz_reason": "",
            "confidence": "thấp",
            "origin": "transcript-extractive",
        }
        for s in picks
    ]


def _api_key(explicit_key: str | None = None) -> str | None:
    return explicit_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


def ai_available(explicit_key: str | None = None) -> bool:
    return bool(_api_key(explicit_key))


def parse_api_keys(raw: str | None) -> list[str]:
    """Parse comma/semicolon/whitespace-separated keys and preserve order."""
    if not raw:
        return []
    cleaned = "\n".join(
        line.split("#", 1)[0] for line in raw.replace("\ufeff", "").splitlines()
    )
    keys: list[str] = []
    seen: set[str] = set()
    for candidate in re.split(r"[,;\s]+", cleaned.strip()):
        key = candidate.strip()
        if key and key not in seen:
            keys.append(key)
            seen.add(key)
    return keys


def configured_api_keys(explicit_raw: str | None = None) -> list[str]:
    """Use UI keys first, then batch env, then legacy single-key env vars."""
    explicit = parse_api_keys(explicit_raw)
    if explicit:
        return explicit
    batch = parse_api_keys(os.getenv("GEMINI_API_KEYS"))
    if batch:
        return batch
    return parse_api_keys(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))


def masked_key_label(key: str) -> str:
    if len(key) < 9:
        return "••••••••"
    return f"{key[:4]}••••{key[-4:]}"


def normalize_confidence(value: Any) -> str:
    """Normalize provider variants to the three Vietnamese UI labels."""
    normalized = str(value or "").strip().lower()
    return {
        "high": "cao",
        "cao": "cao",
        "medium": "vừa",
        "moderate": "vừa",
        "vừa": "vừa",
        "low": "thấp",
        "thấp": "thấp",
    }.get(normalized, "chưa rõ")


def _is_retryable_provider_error(error: Exception) -> bool:
    if isinstance(error, (json.JSONDecodeError, ValueError, TypeError, KeyError)):
        # Changing API keys cannot repair a malformed/invalid model response.
        return False
    status = getattr(error, "status_code", None) or getattr(error, "code", None)
    try:
        status_number = int(status) if status is not None else None
    except (TypeError, ValueError):
        status_number = None
    if status_number == 400:
        return False
    return status_number in {401, 403, 408, 409, 429, 500, 502, 503, 504} or status_number is None


def _run_with_rotation(
    operation: Callable[[str], Any],
    api_keys: list[str],
    cursor: int = 0,
    on_attempt: AttemptCallback | None = None,
) -> RotationResult:
    if not api_keys:
        raise KeyPoolError("Chưa có Gemini API key khả dụng.")

    start = cursor % len(api_keys)
    for offset in range(len(api_keys)):
        slot = (start + offset) % len(api_keys)
        if on_attempt is not None:
            on_attempt(offset + 1, len(api_keys), slot)
        try:
            value = operation(api_keys[slot])
            return RotationResult(
                value=value,
                next_cursor=(slot + 1) % len(api_keys),
                used_slot=slot,
                attempts=offset + 1,
            )
        except Exception as error:
            if not _is_retryable_provider_error(error):
                raise KeyPoolError("Gemini từ chối yêu cầu do dữ liệu gửi lên không hợp lệ.") from None

    raise KeyPoolError(
        f"Không key nào trong pool hoạt động sau {len(api_keys)} lần thử. "
        "Hãy kiểm tra quota, trạng thái key hoặc kết nối mạng."
    )


def _extract_json(text: str) -> Any:
    match = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    payload = match.group(1) if match else text
    return json.loads(payload.strip())


def _gemini_timeout_ms() -> int:
    try:
        configured = int(os.getenv("GEMINI_REQUEST_TIMEOUT_MS", "45000"))
    except ValueError:
        configured = 45_000
    return min(max(configured, 5_000), 120_000)


def _gemini_client(api_key: str | None):
    from google import genai

    return genai.Client(
        api_key=_api_key(api_key),
        http_options={"timeout": _gemini_timeout_ms()},
    )


def summarize_with_gemini(
    source: TranscriptSource,
    quiz_questions: list[str],
    api_key: str | None = None,
) -> list[dict[str, Any]]:
    segments = load_segments(source)
    context = "\n".join(f"[{s.id}] {s.text}" for s in segments)
    quiz_context = (
        json.dumps(quiz_questions, ensure_ascii=False)
        if quiz_questions
        else "KHÔNG CÓ NGÂN HÀNG QUIZ ĐƯỢC CẤP"
    )
    prompt = f"""Bạn là Catch-up Assistant. Chỉ dùng transcript bên dưới.
Trả về JSON array gồm đúng 3-5 object với keys:
title, summary, citations (mã đoạn có thật), quiz (boolean),
quiz_reason (chỉ nêu khi câu hỏi quiz thực sự khớp), confidence (cao/vừa/thấp).
Ưu tiên khái niệm, lập luận, ví dụ quan trọng; bỏ chuyển ý, hành chính, hỏi đáp ngoài lề.
Không thêm kiến thức ngoài nguồn. Một ý chỉ được confidence cao khi mọi mệnh đề có căn cứ.
Nếu không có ngân hàng quiz được cấp, bắt buộc đặt quiz=false và quiz_reason="" cho mọi ý.

QUIZ CŨ:
{quiz_context}

TRANSCRIPT:
{context}
"""
    client = _gemini_client(api_key)
    response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    result = _extract_json(response.text)
    valid_ids = {s.id for s in segments}
    for item in result:
        item["citations"] = [c for c in item.get("citations", []) if c in valid_ids]
        if not item["citations"]:
            raise ValueError("AI trả về điểm chính không có trích dẫn hợp lệ.")
        if not quiz_questions:
            item["quiz"] = False
            item["quiz_reason"] = ""
        item["confidence"] = normalize_confidence(item.get("confidence"))
        item["origin"] = "gemini"
    log_trace("summary", source.name, {"count": len(result), "model": "gemini-2.5-flash"})
    return result[:5]


def answer_question(
    source: TranscriptSource,
    question: str,
    api_key: str | None = None,
) -> dict[str, Any]:
    segments = load_segments(source)
    tokens = {
        token for token in re.findall(r"\w{3,}", question.lower(), re.UNICODE)
        if token not in STOPWORDS
    }
    if not tokens:
        return {
            "answer": "Câu hỏi chưa đủ cụ thể để đối chiếu transcript. Bạn hãy thêm tên khái niệm hoặc nội dung muốn tìm.",
            "citations": [],
            "grounded": False,
            "mode": "guardrail",
        }
    segment_tokens = {
        s.id: set(re.findall(r"\w{3,}", s.text.lower(), re.UNICODE)) for s in segments
    }
    ranked = sorted(
        segments,
        key=lambda s: len(tokens & segment_tokens[s.id]),
        reverse=True,
    )
    minimum_overlap = 1 if len(tokens) == 1 else 2
    relevant = [s for s in ranked[:5] if len(tokens & segment_tokens[s.id]) >= minimum_overlap]
    if not relevant:
        return {
            "answer": "Mình chưa tìm thấy căn cứ đủ rõ trong transcript buổi này để trả lời. Bạn có thể hỏi lại bằng tên khái niệm xuất hiện trong bài.",
            "citations": [],
            "grounded": False,
            "mode": "guardrail",
        }
    if not ai_available(api_key):
        best = relevant[0]
        return {
            "answer": f"Chưa gọi Gemini; đây là đoạn transcript thật liên quan nhất: “{best.text[:420]}{'…' if len(best.text) > 420 else ''}”",
            "citations": [best.id],
            "grounded": True,
            "mode": "extractive",
        }

    context = "\n".join(f"[{s.id}] {s.text}" for s in relevant)
    prompt = f"""Chỉ trả lời từ CONTEXT. Nếu không đủ căn cứ, trả đúng chuỗi KHONG_DU_CAN_CU.
Trả JSON: {{"answer":"...", "citations":["Txx-NNN"]}}. Không dùng kiến thức ngoài.
CÂU HỎI: {question}
CONTEXT:
{context}"""
    client = _gemini_client(api_key)
    response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    data = _extract_json(response.text)
    if data.get("answer") == "KHONG_DU_CAN_CU":
        return {"answer": "Mình chưa tìm thấy căn cứ đủ rõ trong transcript buổi này.", "citations": [], "grounded": False, "mode": "ai"}
    valid_ids = {s.id for s in relevant}
    citations = [c for c in data.get("citations", []) if c in valid_ids]
    if not citations:
        return {"answer": "Mình chưa tìm thấy căn cứ đủ rõ trong transcript buổi này.", "citations": [], "grounded": False, "mode": "ai"}
    log_trace("qa", source.name, {"question": question, "citations": citations, "model": "gemini-2.5-flash"})
    return {"answer": data["answer"], "citations": citations, "grounded": True, "mode": "ai"}


def summarize_with_key_rotation(
    source: TranscriptSource,
    quiz_questions: list[str],
    api_keys: list[str],
    cursor: int = 0,
    on_attempt: AttemptCallback | None = None,
) -> RotationResult:
    return _run_with_rotation(
        lambda key: summarize_with_gemini(source, quiz_questions, key),
        api_keys,
        cursor,
        on_attempt,
    )


def answer_with_key_rotation(
    source: TranscriptSource,
    question: str,
    api_keys: list[str],
    cursor: int = 0,
    on_attempt: AttemptCallback | None = None,
) -> RotationResult:
    if not api_keys:
        return RotationResult(
            value=answer_question(source, question),
            next_cursor=cursor,
            used_slot=None,
            attempts=0,
        )

    result = _run_with_rotation(
        lambda key: answer_question(source, question, key),
        api_keys,
        cursor,
        on_attempt,
    )
    # Guardrail questions never call Gemini, so do not consume a key slot.
    if result.value.get("mode") == "guardrail":
        return RotationResult(
            value=result.value,
            next_cursor=cursor % len(api_keys),
            used_slot=None,
            attempts=0,
        )
    return result


def log_trace(event: str, session: str, data: dict[str, Any]) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "session": session,
        **data,
    }
    with (LOG_DIR / "ai-trace.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
