from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


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


DEMO_SUMMARIES: dict[str, list[dict[str, Any]]] = {
    "transcript-04-clean.md": [
        {
            "title": "AI → machine learning → deep learning → generative AI",
            "summary": "Các lớp nằm theo quan hệ tập con; generative AI là lớp trong cùng đứng sau các chatbot hiện đại.",
            "citations": ["T04-015"],
            "quiz": True,
            "quiz_reason": "Quiz mẫu hỏi trực tiếp về quan hệ giữa bốn khái niệm.",
            "confidence": "cao",
        },
        {
            "title": "Symbolic AI chạm trần vì bùng nổ tổ hợp",
            "summary": "Luật viết tay làm tốt tác vụ hẹp nhưng không thể bao phủ mọi bối cảnh và ngoại lệ của thế giới.",
            "citations": ["T04-024", "T04-025", "T04-027"],
            "quiz": True,
            "quiz_reason": "Quiz mẫu hỏi giới hạn cốt lõi của symbolic AI.",
            "confidence": "cao",
        },
        {
            "title": "Hai mùa đông AI đến từ khoảng cách giữa kỳ vọng và điều kiện",
            "summary": "Thiếu dữ liệu, phần cứng và khả năng duy trì luật khiến niềm tin và nguồn vốn nghiên cứu suy giảm.",
            "citations": ["T04-022", "T04-023", "T04-029"],
            "quiz": False,
            "quiz_reason": "",
            "confidence": "cao",
        },
        {
            "title": "Deep learning tự học đặc trưng từ dữ liệu",
            "summary": "Mạng neuron nhiều tầng giảm nhu cầu viết đặc trưng bằng tay, nhưng vẫn phụ thuộc mạnh vào dữ liệu chất lượng.",
            "citations": ["T04-030", "T04-031", "T04-032"],
            "quiz": True,
            "quiz_reason": "Quiz mẫu đối chiếu feature engineering và deep learning.",
            "confidence": "cao",
        },
    ]
}

DEFAULT_GEMINI_MODEL = "gemini-3.5-flash"


def session_files() -> list[Path]:
    return sorted(TRANSCRIPT_DIR.glob("transcript-*-clean.md"))


def load_segments(path: Path) -> list[Segment]:
    raw = path.read_text(encoding="utf-8")
    return [
        Segment(segment_id, re.sub(r"\s+", " ", text).strip())
        for segment_id, text in SEGMENT_RE.findall(raw)
    ]


def segment_map(path: Path) -> dict[str, Segment]:
    return {segment.id: segment for segment in load_segments(path)}


def default_summary(path: Path) -> list[dict[str, Any]]:
    if path.name in DEMO_SUMMARIES:
        return DEMO_SUMMARIES[path.name]
    segments = [
        s for s in load_segments(path)
        if len(s.text) > 180 and "[Hoạt động lớp:" not in s.text
    ]
    picks = segments[:: max(1, len(segments) // 4)][:4]
    return [
        {
            "title": s.text.split(".")[0][:90],
            "summary": s.text[:260] + ("…" if len(s.text) > 260 else ""),
            "citations": [s.id],
            "quiz": index == 0,
            "quiz_reason": "Cần đối chiếu lại với ngân hàng quiz của khoá.",
            "confidence": "thấp",
        }
        for index, s in enumerate(picks)
    ]


def _api_key(explicit_key: str | None = None) -> str | None:
    return explicit_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


def ai_available(explicit_key: str | None = None) -> bool:
    return bool(_api_key(explicit_key))


def _model_name() -> str:
    return os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)


def _extract_json(text: str) -> Any:
    match = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    payload = match.group(1) if match else text
    return json.loads(payload.strip())


def summarize_with_gemini(
    path: Path,
    quiz_questions: list[str],
    api_key: str | None = None,
) -> list[dict[str, Any]]:
    from google import genai

    segments = load_segments(path)
    context = "\n".join(f"[{s.id}] {s.text}" for s in segments)
    prompt = f"""Bạn là Catch-up Assistant. Chỉ dùng transcript bên dưới.
Trả về JSON array gồm đúng 3-5 object với keys:
title, summary, citations (mã đoạn có thật), quiz (boolean),
quiz_reason (chỉ nêu khi câu hỏi quiz thực sự khớp), confidence (cao/vừa/thấp).
Ưu tiên khái niệm, lập luận, ví dụ quan trọng; bỏ chuyển ý, hành chính, hỏi đáp ngoài lề.
Không thêm kiến thức ngoài nguồn. Một ý chỉ được confidence cao khi mọi mệnh đề có căn cứ.

QUIZ CŨ:
{json.dumps(quiz_questions, ensure_ascii=False)}

TRANSCRIPT:
{context}
"""
    client = genai.Client(api_key=_api_key(api_key))
    model = _model_name()
    response = client.models.generate_content(model=model, contents=prompt)
    result = _extract_json(response.text)
    valid_ids = {s.id for s in segments}
    for item in result:
        item["citations"] = [c for c in item.get("citations", []) if c in valid_ids]
        if not item["citations"]:
            raise ValueError("AI trả về điểm chính không có trích dẫn hợp lệ.")
    log_trace("summary", path.name, {"count": len(result), "model": model})
    return result[:5]


def answer_question(
    path: Path,
    question: str,
    api_key: str | None = None,
) -> dict[str, Any]:
    segments = load_segments(path)
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
            "answer": f"Chế độ demo chỉ tìm đoạn liên quan, chưa diễn giải bằng AI: “{best.text[:420]}{'…' if len(best.text) > 420 else ''}”",
            "citations": [best.id],
            "grounded": True,
            "mode": "demo",
        }

    from google import genai

    context = "\n".join(f"[{s.id}] {s.text}" for s in relevant)
    prompt = f"""Chỉ trả lời từ CONTEXT. Nếu không đủ căn cứ, trả đúng chuỗi KHONG_DU_CAN_CU.
Trả JSON: {{"answer":"...", "citations":["Txx-NNN"]}}. Không dùng kiến thức ngoài.
CÂU HỎI: {question}
CONTEXT:
{context}"""
    client = genai.Client(api_key=_api_key(api_key))
    model = _model_name()
    response = client.models.generate_content(model=model, contents=prompt)
    data = _extract_json(response.text)
    if data.get("answer") == "KHONG_DU_CAN_CU":
        return {"answer": "Mình chưa tìm thấy căn cứ đủ rõ trong transcript buổi này.", "citations": [], "grounded": False, "mode": "ai"}
    valid_ids = {s.id for s in relevant}
    citations = [c for c in data.get("citations", []) if c in valid_ids]
    if not citations:
        return {"answer": "Mình chưa tìm thấy căn cứ đủ rõ trong transcript buổi này.", "citations": [], "grounded": False, "mode": "ai"}
    log_trace("qa", path.name, {"question": question, "citations": citations, "model": model})
    return {"answer": data["answer"], "citations": citations, "grounded": True, "mode": "ai"}


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
