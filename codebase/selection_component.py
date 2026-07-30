from __future__ import annotations

from collections.abc import Callable, Sequence
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
    stage.appendChild(article)
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
    on_ask_change: Callable[[], None] | None = None,
) -> Any:
    """Render trusted transcript text and emit an ask trigger for one selection."""
    return _SELECTABLE_TRANSCRIPT(
        key=key,
        data={"segments": list(segments), "compact": compact},
        height=height,
        width="stretch",
        on_ask_change=on_ask_change,
    )
