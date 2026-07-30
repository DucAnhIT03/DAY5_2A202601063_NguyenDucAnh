from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

import streamlit as st


_HTML = """
<div id="selection-root">
  <div id="selection-toolbar" role="status">
    <span id="selection-hint">Bôi đen một phần trong một đoạn để hỏi AI.</span>
    <button id="selection-ask" type="button" hidden>Giải thích bằng AI</button>
  </div>
  <div id="selection-stage"></div>
</div>
"""

_CSS = """
#selection-root {
  color: var(--st-text-color);
  font-family: var(--st-font);
  height: 100%;
}
#selection-toolbar {
  align-items: center;
  background: color-mix(in srgb, var(--st-primary-color) 8%, white);
  border: 1px solid color-mix(in srgb, var(--st-primary-color) 24%, transparent);
  border-radius: var(--st-border-radius);
  display: flex;
  gap: .75rem;
  justify-content: space-between;
  margin-bottom: .75rem;
  min-height: 2.75rem;
  padding: .55rem .7rem;
  position: sticky;
  top: 0;
  z-index: 2;
}
#selection-hint {
  color: var(--st-text-color);
  font-size: .9rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
#selection-ask {
  background: var(--st-primary-color);
  border: 0;
  border-radius: var(--st-button-radius, var(--st-border-radius));
  color: var(--st-primary-color-text, white);
  cursor: pointer;
  flex: none;
  font: inherit;
  font-weight: 650;
  padding: .52rem .78rem;
}
#selection-ask:hover { filter: brightness(.96); }
#selection-stage {
  display: grid;
  gap: .75rem;
  max-height: 480px;
  overflow-y: auto;
  padding: .05rem .2rem .4rem .05rem;
  scrollbar-gutter: stable;
}
#selection-root.compact #selection-stage { max-height: 270px; }
.catchup-selection-segment {
  background: var(--st-background-color);
  border: 1px solid var(--st-border-color);
  border-radius: var(--st-border-radius);
  padding: .8rem .9rem;
}
.catchup-selection-segment-id {
  color: var(--st-primary-color);
  font-size: .82rem;
  font-weight: 700;
  letter-spacing: .02em;
  margin: 0 0 .38rem;
}
.catchup-selection-segment-text {
  cursor: text;
  line-height: 1.62;
  margin: 0;
  user-select: text;
}
.catchup-selection-segment-text::selection {
  background: color-mix(in srgb, var(--st-primary-color) 28%, transparent);
}
.catchup-selection-segment-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: .55rem;
}
.catchup-selection-segment-ask-all {
  background: transparent;
  border: 1px solid var(--st-border-color);
  border-radius: var(--st-button-radius, var(--st-border-radius));
  color: var(--st-primary-color);
  cursor: pointer;
  font: inherit;
  font-size: .8rem;
  font-weight: 600;
  padding: .35rem .55rem;
}
.catchup-selection-segment-ask-all:hover {
  background: color-mix(in srgb, var(--st-primary-color) 8%, transparent);
}
.catchup-selection-thread {
  background: color-mix(in srgb, var(--st-primary-color) 4%, var(--st-background-color));
  border: 1px solid color-mix(in srgb, var(--st-primary-color) 18%, var(--st-border-color));
  border-radius: var(--st-border-radius);
  display: grid;
  gap: .7rem;
  margin-top: .75rem;
  padding: .75rem;
}
.catchup-selection-thread-title {
  align-items: center;
  color: var(--st-primary-color);
  display: flex;
  font-size: .82rem;
  font-weight: 750;
  gap: .35rem;
  margin: 0;
}
.catchup-selection-turn {
  display: grid;
  gap: .48rem;
}
.catchup-selection-question {
  background: color-mix(in srgb, var(--st-primary-color) 11%, var(--st-background-color));
  border-left: 3px solid var(--st-primary-color);
  border-radius: 0 var(--st-border-radius) var(--st-border-radius) 0;
  color: var(--st-text-color);
  font-size: .88rem;
  line-height: 1.5;
  margin: 0 0 0 1.5rem;
  padding: .55rem .65rem;
}
.catchup-selection-answer {
  background: var(--st-background-color);
  border: 1px solid var(--st-border-color);
  border-radius: var(--st-border-radius);
  line-height: 1.58;
  margin: 0;
  padding: .7rem .75rem;
  white-space: pre-wrap;
}
.catchup-selection-answer.is-error {
  border-color: color-mix(in srgb, #ef4444 45%, var(--st-border-color));
}
.catchup-selection-meta {
  color: color-mix(in srgb, var(--st-text-color) 62%, transparent);
  font-size: .75rem;
  margin: 0 .15rem;
}
.catchup-selection-pending {
  align-items: center;
  color: var(--st-primary-color);
  display: flex;
  font-size: .86rem;
  font-weight: 650;
  gap: .55rem;
  padding: .2rem .1rem;
}
.catchup-selection-followup {
  border-top: 1px solid color-mix(in srgb, var(--st-primary-color) 14%, var(--st-border-color));
  display: grid;
  gap: .42rem;
  margin-top: .1rem;
  padding-top: .72rem;
}
.catchup-selection-followup-label {
  color: var(--st-text-color);
  font-size: .82rem;
  font-weight: 700;
  margin: 0;
}
.catchup-selection-followup-row {
  display: flex;
  gap: .45rem;
}
.catchup-selection-followup-input {
  background: var(--st-background-color);
  border: 1px solid var(--st-border-color);
  border-radius: var(--st-button-radius, var(--st-border-radius));
  color: var(--st-text-color);
  flex: 1;
  font: inherit;
  min-width: 0;
  padding: .58rem .68rem;
}
.catchup-selection-followup-input:focus {
  border-color: var(--st-primary-color);
  box-shadow: 0 0 0 1px var(--st-primary-color);
  outline: none;
}
.catchup-selection-followup-send {
  background: var(--st-primary-color);
  border: 0;
  border-radius: var(--st-button-radius, var(--st-border-radius));
  color: var(--st-primary-color-text, white);
  cursor: pointer;
  font: inherit;
  font-size: .86rem;
  font-weight: 700;
  padding: .58rem .78rem;
}
.catchup-selection-followup-send:disabled,
.catchup-selection-followup-input:disabled {
  cursor: not-allowed;
  opacity: .58;
}
.catchup-selection-followup-help {
  color: color-mix(in srgb, var(--st-text-color) 58%, transparent);
  font-size: .74rem;
  margin: 0;
}
.catchup-selection-spinner {
  animation: catchup-spin .8s linear infinite;
  border: 2px solid color-mix(in srgb, var(--st-primary-color) 22%, transparent);
  border-radius: 999px;
  border-top-color: var(--st-primary-color);
  height: .9rem;
  width: .9rem;
}
@keyframes catchup-spin { to { transform: rotate(360deg); } }
"""

_JS = r"""
export default function(component) {
  const { data, parentElement, setTriggerValue } = component
  const root = parentElement.querySelector("#selection-root")
  const stage = parentElement.querySelector("#selection-stage")
  const hint = parentElement.querySelector("#selection-hint")
  const askButton = parentElement.querySelector("#selection-ask")
  if (!root || !stage || !hint || !askButton) return

  root.classList.toggle("compact", Boolean(data?.compact))
  stage.replaceChildren()

  for (const item of data?.segments ?? []) {
    const article = document.createElement("article")
    article.className = "catchup-selection-segment"
    article.dataset.segmentId = String(item.id ?? "")

    const heading = document.createElement("p")
    heading.className = "catchup-selection-segment-id"
    heading.textContent = `[${item.id ?? ""}]`

    const paragraph = document.createElement("p")
    paragraph.className = "catchup-selection-segment-text"
    paragraph.textContent = String(item.text ?? "")

    const actions = document.createElement("div")
    actions.className = "catchup-selection-segment-actions"
    const wholeButton = document.createElement("button")
    wholeButton.className = "catchup-selection-segment-ask-all"
    wholeButton.type = "button"
    wholeButton.textContent = "Hỏi AI về cả đoạn"
    wholeButton.onclick = () => {
      setTriggerValue("ask", {
        text: String(item.text ?? "").slice(0, 1600),
        segment_id: String(item.id ?? ""),
      })
    }
    actions.appendChild(wholeButton)

    article.append(heading, paragraph, actions)

    const turns = data?.explanations?.[String(item.id ?? "")] ?? []
    const pending = data?.pending
    const isPending = String(pending?.segment_id ?? "") === String(item.id ?? "")
    if (turns.length || isPending) {
      const thread = document.createElement("section")
      thread.className = "catchup-selection-thread"

      const threadTitle = document.createElement("p")
      threadTitle.className = "catchup-selection-thread-title"
      threadTitle.textContent = "AI · Giải thích ngay tại đoạn này"
      thread.appendChild(threadTitle)

      for (const turn of turns) {
        const turnElement = document.createElement("div")
        turnElement.className = "catchup-selection-turn"

        const question = document.createElement("p")
        question.className = "catchup-selection-question"
        question.textContent = turn.question
          ? `Bạn hỏi tiếp: ${String(turn.question)}`
          : `Bạn đã chọn: “${String(turn.selected_text ?? "")}”`

        const answer = document.createElement("p")
        answer.className = "catchup-selection-answer"
        if (turn.mode === "error") answer.classList.add("is-error")
        answer.textContent = String(turn.answer ?? "")

        const meta = document.createElement("p")
        meta.className = "catchup-selection-meta"
        const source = String(turn.segment_id ?? item.id ?? "")
        const provider = turn.mode === "ai" ? "Gemini" : "Trích xuất từ transcript"
        const slot = Number.isInteger(turn.slot) ? ` · key slot ${turn.slot + 1}` : ""
        meta.textContent = `Nguồn [${source}] · ${provider}${slot}`

        turnElement.append(question, answer, meta)
        thread.appendChild(turnElement)
      }

      if (isPending) {
        const pendingTurn = document.createElement("div")
        pendingTurn.className = "catchup-selection-turn"

        const pendingQuestion = document.createElement("p")
        pendingQuestion.className = "catchup-selection-question"
        pendingQuestion.textContent = pending.kind === "followup"
          ? `Bạn hỏi tiếp: ${String(pending.question ?? "")}`
          : `Bạn đã chọn: “${String(pending.text ?? "")}”`

        const pendingStatus = document.createElement("div")
        pendingStatus.className = "catchup-selection-pending"
        const spinner = document.createElement("span")
        spinner.className = "catchup-selection-spinner"
        spinner.setAttribute("aria-hidden", "true")
        const pendingText = document.createElement("span")
        pendingText.textContent = pending.kind === "followup"
          ? "Gemini đang trả lời tiếp từ đúng ngữ cảnh này…"
          : "Gemini đang đọc đúng đoạn này và chuẩn bị câu trả lời…"
        pendingStatus.append(spinner, pendingText)
        pendingTurn.append(pendingQuestion, pendingStatus)
        thread.appendChild(pendingTurn)
      }

      const anchorTurn = [...turns].reverse().find(turn => turn.selected_text)
      if (anchorTurn) {
        const followup = document.createElement("form")
        followup.className = "catchup-selection-followup"

        const followupLabel = document.createElement("p")
        followupLabel.className = "catchup-selection-followup-label"
        followupLabel.textContent = "Bạn chưa rõ? Hỏi tiếp ngay tại đây"

        const followupRow = document.createElement("div")
        followupRow.className = "catchup-selection-followup-row"
        const followupInput = document.createElement("input")
        followupInput.className = "catchup-selection-followup-input"
        followupInput.type = "text"
        followupInput.maxLength = 600
        followupInput.placeholder = "Hỏi tiếp về phần này…"
        followupInput.setAttribute("aria-label", `Hỏi tiếp về đoạn ${item.id ?? ""}`)
        followupInput.disabled = isPending

        const followupButton = document.createElement("button")
        followupButton.className = "catchup-selection-followup-send"
        followupButton.type = "submit"
        followupButton.textContent = "Gửi"
        followupButton.disabled = isPending

        const followupHelp = document.createElement("p")
        followupHelp.className = "catchup-selection-followup-help"
        followupHelp.textContent = "Ví dụ: Tại sao? · Giải thích đơn giản hơn · Ý này liên quan gì trong đoạn?"

        followup.append(followupLabel, followupRow, followupHelp)
        followupRow.append(followupInput, followupButton)
        followup.onsubmit = event => {
          event.preventDefault()
          const question = followupInput.value.replace(/\s+/g, " ").trim()
          if (question.length < 2 || isPending) return
          followupInput.disabled = true
          followupButton.disabled = true
          setTriggerValue("followup", {
            question: question.slice(0, 600),
            segment_id: String(item.id ?? ""),
            selected_text: String(anchorTurn.selected_text ?? "").slice(0, 1600),
          })
        }
        thread.appendChild(followup)
      }

      article.appendChild(thread)
    }
    stage.appendChild(article)
  }

  const focusedSegment = String(data?.focus_segment_id ?? data?.pending?.segment_id ?? "")
  if (focusedSegment) {
    const target = Array.from(stage.querySelectorAll("[data-segment-id]")).find(
      element => element.dataset.segmentId === focusedSegment
    )
    requestAnimationFrame(() => {
      target?.querySelector(".catchup-selection-thread")?.scrollIntoView({
        behavior: "smooth",
        block: "nearest",
      })
    })
  }

  let selected = null

  const textElementFor = (node) => {
    const element = node?.nodeType === Node.TEXT_NODE ? node.parentElement : node
    return element?.closest?.(".catchup-selection-segment-text") ?? null
  }

  const readSelection = () => {
    const selection = parentElement.getSelection?.() ?? document.getSelection()
    const text = selection?.toString().replace(/\s+/g, " ").trim() ?? ""
    if (!text) {
      selected = null
      askButton.hidden = true
      hint.textContent = "Bôi đen một phần trong một đoạn để hỏi AI."
      return
    }

    const startText = textElementFor(selection.anchorNode)
    const endText = textElementFor(selection.focusNode)
    if (!startText || startText !== endText) {
      selected = null
      askButton.hidden = true
      hint.textContent = "Hãy bôi đen nội dung trong cùng một đoạn transcript."
      return
    }

    const clipped = text.slice(0, 1600)
    const segment = startText.closest("[data-segment-id]")
    selected = { text: clipped, segment_id: segment.dataset.segmentId }
    const preview = clipped.length > 105 ? `${clipped.slice(0, 105)}…` : clipped
    hint.textContent = `Đã chọn: “${preview}”`
    askButton.hidden = false
  }

  const scheduleSelectionRead = () => setTimeout(readSelection, 0)
  const handleDocumentSelection = () => {
    if (document.getSelection()?.toString().trim()) scheduleSelectionRead()
  }

  stage.onmouseup = scheduleSelectionRead
  stage.onpointerup = scheduleSelectionRead
  stage.onkeyup = scheduleSelectionRead
  document.addEventListener("selectionchange", handleDocumentSelection)
  askButton.onclick = () => {
    if (!selected) return
    setTriggerValue("ask", selected)
  }

  return () => {
    stage.onmouseup = null
    stage.onpointerup = null
    stage.onkeyup = null
    askButton.onclick = null
    document.removeEventListener("selectionchange", handleDocumentSelection)
  }
}
"""


_SELECTABLE_TRANSCRIPT = st.components.v2.component(
    "catchup_selectable_transcript",
    html=_HTML,
    css=_CSS,
    js=_JS,
    isolate_styles=False,
)


def selectable_transcript(
    segments: Sequence[dict[str, str]],
    *,
    key: str,
    compact: bool = False,
    height: int = 560,
    explanations: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
    pending: Mapping[str, Any] | None = None,
    focus_segment_id: str | None = None,
    on_ask_change: Callable[[], None] | None = None,
    on_followup_change: Callable[[], None] | None = None,
) -> Any:
    """Render selectable transcript text with an inline, grounded AI thread."""
    return _SELECTABLE_TRANSCRIPT(
        key=key,
        data={
            "segments": list(segments),
            "compact": compact,
            "explanations": dict(explanations or {}),
            "pending": dict(pending) if pending else None,
            "focus_segment_id": focus_segment_id,
        },
        height=height,
        width="stretch",
        on_ask_change=on_ask_change,
        on_followup_change=on_followup_change,
    )
