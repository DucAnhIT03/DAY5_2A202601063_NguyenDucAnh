import json

import streamlit as st

try:
    from codebase.core import (
        KeyPoolError,
        LessonInputError,
        answer_selection_followup_with_key_rotation,
        answer_with_key_rotation,
        configured_api_keys,
        default_summary,
        explain_selection_with_key_rotation,
        masked_key_label,
        parse_api_keys,
        segment_map,
        summarize_with_key_rotation,
        user_transcript_from_text,
    )
    from codebase.key_vault import (
        KeyVaultError,
        clear_key_pool,
        load_key_pool,
        save_key_pool,
    )
    from codebase.mongo_repository import (
        MongoTranscriptRepository,
        MongoUnavailable,
        mongo_database,
        mongo_uri,
        snapshot_from_cache_payload,
        snapshot_to_cache_payload,
    )
    from codebase.selection_component import selectable_transcript
except ModuleNotFoundError:
    from core import (
        KeyPoolError,
        LessonInputError,
        answer_selection_followup_with_key_rotation,
        answer_with_key_rotation,
        configured_api_keys,
        default_summary,
        explain_selection_with_key_rotation,
        masked_key_label,
        parse_api_keys,
        segment_map,
        summarize_with_key_rotation,
        user_transcript_from_text,
    )
    from key_vault import (
        KeyVaultError,
        clear_key_pool,
        load_key_pool,
        save_key_pool,
    )
    from mongo_repository import (
        MongoTranscriptRepository,
        MongoUnavailable,
        mongo_database,
        mongo_uri,
        snapshot_from_cache_payload,
        snapshot_to_cache_payload,
    )
    from selection_component import selectable_transcript


BRAND_NAME = "taphoammo"
AI_DISPLAY_NAME = f"{BRAND_NAME} AI"


st.set_page_config(
    page_title=f"{BRAND_NAME} · Trợ lý học tập",
    page_icon=":material/school:",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Người dùng yêu cầu giao diện tối giản. CSS chỉ tinh chỉnh các vùng có key ổn
# định; luồng tương tác vẫn dùng widget native của Streamlit.
st.html(
    """
    <style>
    .stApp {background:#F7F8FC;}
    .stMainBlockContainer {max-width:1160px; padding:1.35rem 1.5rem 4rem;}
    .st-key-brandbar {padding:.1rem 0 .7rem;}
    .st-key-brandbar h3 {margin:0; letter-spacing:-.025em;}
    .st-key-lesson_header {
        background:#FFFFFF; border:1px solid #E6E8F0 !important;
        border-radius:20px; padding:1.25rem 1.4rem .9rem;
        box-shadow:0 8px 28px rgba(30,41,59,.055); margin-bottom:1rem;
    }
    .st-key-lesson_header h1 {font-size:2rem !important; margin:.15rem 0 .25rem;}
    .st-key-lesson_header p {color:#667085; max-width:760px;}
    .st-key-modebar {padding:.15rem 0 .55rem;}
    .st-key-outline {
        background:#FFFFFF; border:1px solid #E6E8F0 !important;
        border-radius:16px; padding:.55rem .75rem;
    }
    .st-key-detail_card {
        background:#FFFFFF; border:1px solid #E6E8F0 !important;
        border-radius:18px; padding:.8rem 1rem;
        box-shadow:0 6px 22px rgba(30,41,59,.045);
    }
    .st-key-source_card {
        background:#FAFAFF; border:1px solid #E1E4F0 !important;
        border-radius:15px; padding:.5rem .75rem;
    }
    .st-key-chat_card {
        background:#FFFFFF; border:1px solid #E6E8F0 !important;
        border-radius:18px; padding:.8rem 1rem 1rem;
        box-shadow:0 6px 22px rgba(30,41,59,.045);
    }
    .st-key-chat_history_scroll {
        max-height:420px; overflow-y:auto; overscroll-behavior:contain;
        padding-right:.45rem; scrollbar-gutter:stable;
    }
    .st-key-overview_main, .st-key-quiz_panel, .st-key-transcript_panel {
        background:#FFFFFF; border:1px solid #E6E8F0 !important;
        border-radius:18px; padding:.75rem 1rem;
        box-shadow:0 6px 22px rgba(30,41,59,.04);
    }
    .st-key-stat_row [data-testid="stMetric"] {
        background:#FFFFFF; border:1px solid #E6E8F0; border-radius:15px;
        padding:.65rem .8rem;
    }
    .st-key-outline [data-testid="stRadio"] label {
        padding:.42rem .25rem; border-bottom:1px solid #F0F1F5;
    }
    .st-key-outline [data-testid="stRadio"] label:last-child {border-bottom:0;}
    [data-testid="stChatMessage"] {padding:.55rem .7rem; border-radius:13px;}
    @media (max-width:760px) {
        .stMainBlockContainer {padding:.8rem .85rem 3rem;}
        .st-key-lesson_header {padding:1rem; border-radius:16px;}
        .st-key-lesson_header h1 {font-size:1.65rem !important;}
    }
    </style>
    """
)

@st.cache_resource
def get_mongo_repository(uri: str, database: str) -> MongoTranscriptRepository:
    return MongoTranscriptRepository(uri, database)


@st.cache_data(ttl="30s", max_entries=4)
def load_mongo_data(uri: str, database: str):
    snapshot = get_mongo_repository(uri, database).snapshot()
    return snapshot_to_cache_payload(snapshot)


mongo_error = None
try:
    mongo_snapshot = snapshot_from_cache_payload(
        load_mongo_data(mongo_uri(), mongo_database())
    )
    files = list(mongo_snapshot.transcripts)
    default_quiz_questions = list(mongo_snapshot.quiz_questions)
except MongoUnavailable as exc:
    mongo_error = str(exc)
    st.error(
        f"{mongo_error} Ứng dụng yêu cầu MongoDB thật và không dùng dữ liệu fallback.",
        icon=":material/database_off:",
    )
    st.code(
        "docker compose up -d mongodb\n"
        ".\\.venv\\Scripts\\python.exe scripts\\seed_mongodb.py",
        language="powershell",
    )
    st.stop()

if not files:
    st.error("Không có transcript nào để hiển thị.", icon=":material/database_off:")
    st.stop()

lessons_by_name = {transcript.name: transcript for transcript in files}

try:
    persisted_api_keys = load_key_pool()
    initial_vault_error = None
except KeyVaultError as exc:
    persisted_api_keys = []
    initial_vault_error = str(exc)

st.session_state.setdefault("messages", [])
st.session_state.setdefault("pending_inline_selection", None)
st.session_state.setdefault("inline_explanations", {})
st.session_state.setdefault("inline_focus", {})
st.session_state.setdefault("inline_request_counter", 0)
st.session_state.setdefault("gemini_api_keys_raw", "")
if st.session_state.get("key_input_security_version") != 1:
    # Xóa giá trị mà các bản cũ từng nạp vào widget; key đã nằm trong DPAPI vault.
    st.session_state.gemini_api_keys_raw = ""
    st.session_state.key_input_security_version = 1
st.session_state.setdefault("gemini_key_cursor", 0)
st.session_state.setdefault("last_key_slot", None)
st.session_state.setdefault("key_vault_saved_count", len(persisted_api_keys))
st.session_state.setdefault("key_vault_error", initial_vault_error)
st.session_state.setdefault("point_selector", 0)
st.session_state.setdefault("active_view", "Tổng quan")
st.session_state.setdefault("qa_include_web", False)


def reset_lesson() -> None:
    st.session_state.messages = []
    st.session_state.pending_inline_selection = None
    st.session_state.inline_explanations = {}
    st.session_state.inline_focus = {}
    st.session_state.point_selector = 0
    st.session_state.active_view = "Tổng quan"
    st.session_state.qa_include_web = False


def go_to_view(view_name: str) -> None:
    st.session_state.active_view = view_name


def queue_inline_explanation(component_key: str) -> None:
    component_state = st.session_state.get(component_key)
    if component_state is None:
        return
    payload = (
        component_state.get("ask")
        if hasattr(component_state, "get")
        else getattr(component_state, "ask", None)
    )
    if not isinstance(payload, dict):
        return
    selected_text = str(payload.get("text", "")).strip()
    segment_id = str(payload.get("segment_id", "")).strip()
    if len(selected_text) < 3 or not segment_id:
        return
    st.session_state.inline_request_counter += 1
    st.session_state.pending_inline_selection = {
        "request_id": st.session_state.inline_request_counter,
        "kind": "explanation",
        "component_key": component_key,
        "text": selected_text[:1_600],
        "segment_id": segment_id,
    }


def queue_inline_followup(component_key: str) -> None:
    component_state = st.session_state.get(component_key)
    if component_state is None:
        return
    payload = (
        component_state.get("followup")
        if hasattr(component_state, "get")
        else getattr(component_state, "followup", None)
    )
    if not isinstance(payload, dict):
        return
    question = " ".join(str(payload.get("question", "")).split()).strip()
    segment_id = str(payload.get("segment_id", "")).strip()
    component_threads = st.session_state.inline_explanations.get(component_key, {})
    segment_thread = component_threads.get(segment_id, [])
    anchor = next(
        (
            str(turn.get("selected_text", "")).strip()
            for turn in reversed(segment_thread)
            if str(turn.get("selected_text", "")).strip()
        ),
        "",
    )
    if len(question) < 2 or not segment_id or len(anchor) < 3:
        return
    st.session_state.inline_request_counter += 1
    st.session_state.pending_inline_selection = {
        "request_id": st.session_state.inline_request_counter,
        "kind": "followup",
        "component_key": component_key,
        "text": anchor[:1_600],
        "question": question[:600],
        "segment_id": segment_id,
    }


def inline_explanations_for(component_key: str) -> dict:
    return st.session_state.inline_explanations.get(component_key, {})


def inline_pending_for(component_key: str) -> dict | None:
    pending = st.session_state.get("pending_inline_selection")
    if isinstance(pending, dict) and pending.get("component_key") == component_key:
        return pending
    return None


def render_answer_sources(sources: list[dict], citations: list[str]) -> None:
    """Show a compact source line plus server-built evidence details."""
    safe_sources = [source for source in sources if isinstance(source, dict)]
    if not safe_sources:
        if citations:
            st.caption(
                ":material/source: Nguồn: "
                + ", ".join(f"[{citation}]" for citation in citations)
            )
        return

    source_labels: list[str] = []
    for source in safe_sources:
        title = str(source.get("title") or "Nguồn")
        reference = str(source.get("id") or "")
        source_labels.append(
            f"{title} · [{reference}]"
            if source.get("type") == "lesson"
            else f"{title} · web"
        )
    st.caption(
        ":material/verified: Nguồn kiểm chứng: "
        + " · ".join(source_labels)
    )

    with st.expander(
        f"Xem nội dung nguồn ({len(safe_sources)})",
        icon=":material/library_books:",
    ):
        for index, source in enumerate(safe_sources, 1):
            with st.container(border=True):
                title = str(source.get("title") or "Nguồn")
                reference = str(source.get("id") or "")
                origin = str(source.get("origin") or "")
                if source.get("type") == "web":
                    st.markdown(f"**{index}. {title}**")
                    url = str(source.get("url") or "")
                    if url.startswith(("https://", "http://")):
                        st.link_button(
                            "Mở nguồn web",
                            url,
                            icon=":material/open_in_new:",
                        )
                else:
                    st.markdown(f"**{index}. {title} · [{reference}]**")
                if origin:
                    st.caption(origin)
                excerpt = str(source.get("excerpt") or "").strip()
                if excerpt:
                    st.caption(
                        str(source.get("excerpt_label") or "Nội dung hỗ trợ")
                    )
                    st.write(f"“{excerpt}”")


def reset_key_pool() -> None:
    st.session_state.gemini_key_cursor = 0
    st.session_state.last_key_slot = None


def persist_manual_key_pool() -> None:
    reset_key_pool()
    keys = parse_api_keys(st.session_state.get("gemini_api_keys_raw", ""))
    if not keys:
        return
    try:
        save_key_pool(keys)
        st.session_state.key_vault_saved_count = len(keys)
        st.session_state.key_vault_error = None
        # Không nạp ngược bí mật vào DOM sau khi đã lưu. Kho DPAPI mới là
        # nguồn key đang hoạt động; ô này chỉ dùng để nhập một lần.
        st.session_state.gemini_api_keys_raw = ""
    except KeyVaultError as exc:
        st.session_state.key_vault_error = str(exc)


def clear_persisted_key_pool() -> None:
    try:
        clear_key_pool()
        st.session_state.gemini_api_keys_raw = ""
        st.session_state.key_vault_saved_count = 0
        st.session_state.key_vault_error = None
        reset_key_pool()
    except KeyVaultError as exc:
        st.session_state.key_vault_error = str(exc)


@st.dialog("Thêm dữ liệu bài học")
def add_lesson_dialog() -> None:
    st.write(
        "Nhập một buổi mỗi lần. Sáu bài demo có sẵn vẫn được giữ nguyên; "
        "bài mới sẽ lưu riêng trong MongoDB với nhãn “Bạn thêm”."
    )
    st.caption(
        "Dán transcript hoặc tải TXT/Markdown. JSON có thể dùng đúng ba trường "
        "`buoi_hoc`, `transcript`, `cau_hoi_quiz`. Nếu vừa tải file vừa dán, file được ưu tiên."
    )

    with st.form("lesson_import_form", border=False):
        lesson_title = st.text_input(
            "Tên buổi học",
            placeholder="Ví dụ: Buổi 5 — Prompt engineering",
            max_chars=160,
        )
        lesson_file = st.file_uploader(
            "Tệp transcript hoặc JSON",
            type=["txt", "md", "json"],
            help="Tối đa 512 KB · mã hóa UTF-8.",
        )
        lesson_transcript = st.text_area(
            "Transcript",
            placeholder=(
                "Dán toàn bộ nội dung buổi học tại đây. Có thể để trống khi đã tải tệp."
            ),
            height=220,
            max_chars=500_000,
        )
        lesson_quiz = st.text_area(
            "Quiz cũ (tùy chọn · mỗi dòng một câu)",
            placeholder="Câu 1: ...\nCâu 2: ...",
            height=110,
            max_chars=50_000,
        )
        submitted = st.form_submit_button(
            "Lưu bài học vào MongoDB",
            icon=":material/save:",
            type="primary",
            width="stretch",
        )

    if not submitted:
        return

    effective_title = lesson_title
    effective_transcript = lesson_transcript
    quiz_values: list[str] = list(lesson_quiz.splitlines())
    if lesson_file is not None:
        if lesson_file.size > 512 * 1024:
            st.error("Tệp bài học vượt quá giới hạn 512 KB.")
            return
        try:
            uploaded_text = lesson_file.getvalue().decode("utf-8-sig")
        except UnicodeDecodeError:
            st.error("Tệp bài học phải sử dụng mã hóa UTF-8.")
            return

        if lesson_file.name.lower().endswith(".json"):
            try:
                payload = json.loads(uploaded_text)
            except json.JSONDecodeError:
                st.error("Tệp JSON không đúng định dạng.")
                return
            if not isinstance(payload, dict):
                st.error("JSON bài học phải là một object.")
                return
            effective_title = effective_title.strip() or str(payload.get("buoi_hoc", ""))
            effective_transcript = str(payload.get("transcript", ""))
            payload_quiz = payload.get("cau_hoi_quiz", [])
            if payload_quiz and not isinstance(payload_quiz, list):
                st.error("Trường `cau_hoi_quiz` trong JSON phải là một danh sách.")
                return
            quiz_values = [str(value) for value in payload_quiz] + quiz_values
        else:
            effective_transcript = uploaded_text

    try:
        transcript = user_transcript_from_text(
            effective_title,
            effective_transcript,
            quiz_values,
        )
        get_mongo_repository(mongo_uri(), mongo_database()).save_user_lesson(transcript)
    except (LessonInputError, MongoUnavailable, ValueError) as exc:
        st.error(str(exc), icon=":material/error:")
        return

    load_mongo_data.clear()
    reset_lesson()
    st.session_state.lesson_import_target = transcript.name
    st.session_state.lesson_import_notice = (
        f"Đã lưu “{transcript.title}” · {len(transcript.segments)} đoạn"
        + (
            f" · {len(transcript.quiz_questions)} câu quiz"
            if transcript.quiz_questions
            else " · không có quiz cũ"
        )
    )
    st.rerun()


with st.sidebar:
    st.markdown("## :material/settings: Cài đặt")
    st.markdown("**Nguồn dữ liệu**")
    st.success("MongoDB đang kết nối", icon=":material/database:")
    st.caption(
        f"`{mongo_snapshot.database}.{mongo_snapshot.collection}` · "
        f"{len(files)} buổi · {mongo_snapshot.segment_count} đoạn thật"
    )
    st.divider()
    st.markdown(f"**API cho {AI_DISPLAY_NAME}**")
    uploaded_key_file = st.file_uploader(
        f"File Gemini API key cho {AI_DISPLAY_NAME} (.txt)",
        type=["txt"],
        key="gemini_key_file",
        on_change=reset_key_pool,
        help="Mỗi dòng chứa đúng một API key. File chỉ được đọc trong RAM.",
    )
    uploaded_key_text = ""
    if uploaded_key_file is not None:
        if uploaded_key_file.size > 256 * 1024:
            st.error("File key vượt quá giới hạn 256 KB.")
        else:
            try:
                uploaded_key_text = uploaded_key_file.getvalue().decode("utf-8-sig")
            except UnicodeDecodeError:
                st.error("File key phải sử dụng mã hoá UTF-8.")

    mask_key_input = st.toggle(
        "Che key trên màn hình",
        value=True,
        key="mask_gemini_key_input",
        help="Nên bật khi trình chiếu. Tắt tạm thời nếu cần kiểm tra từng dòng.",
    )
    if mask_key_input:
        st.html(
            """
            <style>
            .st-key-gemini_api_keys_raw textarea {
                -webkit-text-security: disc;
                font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
            }
            </style>
            """
        )

    st.text_area(
        "Dán danh sách key · mỗi dòng một key",
        height=150,
        max_chars=256 * 1024,
        key="gemini_api_keys_raw",
        placeholder="gemini-key-1\ngemini-key-2\ngemini-key-3",
        help="Nhấn Enter để xuống dòng, sau đó chọn Lưu danh sách key.",
    )
    st.button(
        "Lưu danh sách key",
        icon=":material/save:",
        type="primary",
        on_click=persist_manual_key_pool,
        disabled=not bool(st.session_state.gemini_api_keys_raw.strip()),
        width="stretch",
    )
    st.caption(
        "Mỗi dòng đúng một key · tự bỏ dòng trống, comment bắt đầu bằng # và key trùng. "
        "Sau khi lưu, ô nhập được xóa và key chỉ còn trong kho mã hóa."
    )

    combined_key_input = "\n".join(
        part
        for part in (
            "\n".join(persisted_api_keys),
            uploaded_key_text,
            st.session_state.gemini_api_keys_raw,
        )
        if part
    )
    api_keys = configured_api_keys(combined_key_input)
    if uploaded_key_text:
        try:
            save_key_pool(api_keys)
            st.session_state.key_vault_saved_count = len(api_keys)
            st.session_state.key_vault_error = None
        except KeyVaultError as exc:
            st.session_state.key_vault_error = str(exc)

    if api_keys:
        st.success(f"{len(api_keys)} key sẵn sàng", icon=":material/key:")
        cursor = st.session_state.gemini_key_cursor % len(api_keys)
        st.caption(f"Request tiếp theo: slot {cursor + 1}")
        for index, key in enumerate(api_keys[:6]):
            marker = " ← tiếp theo" if index == cursor else ""
            st.caption(f"Slot {index + 1}: `{masked_key_label(key)}`{marker}")
        if len(api_keys) > 6:
            st.caption(f"… và {len(api_keys) - 6} key khác")
        if st.session_state.last_key_slot is not None:
            st.caption(f"Request gần nhất dùng slot {st.session_state.last_key_slot + 1}")
        if st.session_state.key_vault_saved_count:
            st.caption(
                f":material/lock: Đã mã hóa {st.session_state.key_vault_saved_count} key "
                "trên máy này · tải lại trang không bị mất"
            )
            st.button(
                "Xóa key đã lưu",
                icon=":material/delete:",
                on_click=clear_persisted_key_pool,
                help="Xóa bản mã hóa cục bộ và làm trống vùng nhập trực tiếp.",
            )
    else:
        st.info(f"Chưa cấu hình {AI_DISPLAY_NAME}", icon=":material/key_off:")
    if st.session_state.key_vault_error:
        st.warning(st.session_state.key_vault_error, icon=":material/lock_open:")
    st.markdown("**Nguyên tắc an toàn**")
    st.caption(
        "Round-robin sau mỗi request · tự chuyển khi hết quota · "
        "chỉ dùng transcript đang mở · không đủ căn cứ thì từ chối."
    )

api_keys = configured_api_keys(combined_key_input)

lesson_options = [lesson.name for lesson in files]
import_target = st.session_state.pop("lesson_import_target", None)
selected_lesson_index = 3 if len(files) > 3 else 0
if import_target in lesson_options:
    st.session_state.pop("session_selector", None)
    selected_lesson_index = lesson_options.index(import_target)
import_notice = st.session_state.pop("lesson_import_notice", None)
if import_notice:
    st.toast(import_notice, icon=":material/check_circle:")


def lesson_option_label(name: str) -> str:
    lesson = lessons_by_name[name]
    clean_title = lesson.title.replace("Transcript bài giảng (bản sạch) — ", "")
    origin = "Bạn thêm" if lesson.source == "user-submitted" else "Demo"
    return f"{origin} · {clean_title}"

with st.container(horizontal=True, vertical_alignment="center", key="brandbar"):
    st.markdown(f"### :material/school: {BRAND_NAME}")
    st.space("stretch")
    st.badge(
        f"MongoDB thật · {len(files)} buổi",
        color="blue",
        icon=":material/database:",
    )
    if api_keys:
        st.badge(
            f"{AI_DISPLAY_NAME} · {len(api_keys)} key",
            color="green",
            icon=":material/check_circle:",
        )
    else:
        st.badge(
            f"{AI_DISPLAY_NAME} chưa cấu hình",
            color="gray",
            icon=":material/key_off:",
        )

with st.container(border=True, key="lesson_header"):
    st.caption("TAPHOAMMO · TRỢ LÝ BẮT KỊP BÀI HỌC")
    st.title("Hôm nay bạn muốn bắt kịp buổi nào?")
    st.write(
        f"Chọn một buổi. {AI_DISPLAY_NAME} sẽ chỉ giữ lại phần cần đọc trước "
        "và dẫn về đúng nguồn."
    )
    with st.container(horizontal=True, vertical_alignment="bottom"):
        selected_name = st.selectbox(
            "Buổi học đã bỏ lỡ",
            options=lesson_options,
            index=selected_lesson_index,
            format_func=lesson_option_label,
            key="session_selector",
            on_change=reset_lesson,
        )
        if st.button(
            "Thêm bài học",
            icon=":material/upload_file:",
            type="primary",
            help="Dán transcript hoặc tải TXT, Markdown, JSON.",
        ):
            add_lesson_dialog()

path = next(p for p in files if p.name == selected_name)
segments = segment_map(path)
cache_key = path.name
quiz_questions = (
    list(path.quiz_questions)
    if path.source == "user-submitted"
    else list(default_quiz_questions)
)
repository = get_mongo_repository(mongo_uri(), mongo_database())
try:
    stored_analysis = repository.get_analysis(path)
except MongoUnavailable as exc:
    st.error(str(exc), icon=":material/database_off:")
    st.stop()
summary = stored_analysis["points"] if stored_analysis else default_summary(path)
if not quiz_questions:
    summary = [
        {**point, "quiz": False, "quiz_reason": ""}
        for point in summary
    ]
if not summary:
    st.error("Transcript này chưa có đủ nội dung để tạo trọng điểm.", icon=":material/warning:")
    st.stop()
if not isinstance(st.session_state.point_selector, int) or not (
    0 <= st.session_state.point_selector < len(summary)
):
    st.session_state.point_selector = 0
summary_is_ai = stored_analysis is not None
quiz_count = sum(bool(point.get("quiz")) for point in summary)

analyze_requested = False
with st.container(horizontal=True, vertical_alignment="center", key="modebar"):
    view = st.segmented_control(
        "Khu vực",
        ["Tổng quan", "Trọng điểm", "Transcript", f"Hỏi {AI_DISPLAY_NAME}"],
        key="active_view",
        label_visibility="collapsed",
    )
    st.space("stretch")
    st.caption(f"{len(summary)} trọng điểm · {quiz_count} liên quan quiz · {len(segments)} đoạn transcript")
    if summary_is_ai:
        st.badge(
            f"{AI_DISPLAY_NAME} · đã lưu MongoDB",
            color="green",
            icon=":material/verified:",
        )
    else:
        st.badge("Trích xuất từ transcript thật", color="blue", icon=":material/article:")
    if api_keys:
        analyze_requested = st.button(
            "Phân tích lại" if summary_is_ai else f"Phân tích bằng {AI_DISPLAY_NAME}",
            icon=":material/refresh:" if summary_is_ai else ":material/auto_awesome:",
            help=f"Chỉ bắt đầu gọi {AI_DISPLAY_NAME} khi bạn bấm nút này.",
            type="secondary" if summary_is_ai else "primary",
        )

if summary_is_ai:
    st.caption(
        f":material/database: Kết quả từ `analyses` · "
        f"{stored_analysis['model']} · {stored_analysis['generated_at']}"
    )
else:
    st.info(
        f"Chưa có kết quả {AI_DISPLAY_NAME} cho phiên bản transcript này. "
        "Các mục bên dưới là "
        "trích đoạn tự động từ dữ liệu MongoDB thật, không phải nội dung AI giả lập.",
        icon=":material/info:",
    )

if analyze_requested:
    try:
        with st.status(
            f"{AI_DISPLAY_NAME} đang phân tích…", expanded=True
        ) as analysis_status:
            attempt_progress = st.progress(0, text="Đang chuẩn bị request…")

            def show_key_attempt(attempt: int, total: int, slot: int) -> None:
                attempt_progress.progress(
                    attempt / total,
                    text=(
                        f"Đang thử slot {slot + 1} · lượt {attempt}/{total} · "
                        "mỗi lượt có timeout bảo vệ"
                    ),
                )

            rotation = summarize_with_key_rotation(
                path,
                quiz_questions,
                api_keys,
                st.session_state.gemini_key_cursor,
                on_attempt=show_key_attempt,
            )
            repository.save_analysis(
                path,
                rotation.value,
                model="gemini-2.5-flash",
                quiz_question_count=len(quiz_questions),
            )
            st.session_state.gemini_key_cursor = rotation.next_cursor
            st.session_state.last_key_slot = rotation.used_slot
            analysis_status.update(
                label=(
                    f"Hoàn tất bằng key slot {rotation.used_slot + 1} · "
                    "đã lưu MongoDB"
                ),
                state="complete",
                expanded=False,
            )
        st.rerun()
    except Exception as exc:
        st.error(f"{AI_DISPLAY_NAME} chưa thể xử lý yêu cầu: {exc}")

if view == "Tổng quan":
    main_col, quiz_col = st.columns([1.35, 1], gap="large")
    with main_col:
        with st.container(border=True, key="overview_main"):
            st.caption("BẢN ĐỒ TAPHOAMMO")
            st.markdown(f"## {len(summary)} điều cần nắm trong buổi này")
            st.write(
                "Bắt đầu từ các trọng điểm bên dưới. Mỗi ý đều có đoạn transcript "
                "gốc để bạn kiểm tra lại trước khi chuyển sang ý tiếp theo."
            )
            for index, point in enumerate(summary, 1):
                quiz_mark = " · **quiz**" if point.get("quiz") else ""
                st.markdown(f"**{index:02d}.** {point['title']}{quiz_mark}")
            st.button(
                "Bắt đầu đọc trọng điểm",
                icon=":material/arrow_forward:",
                type="primary",
                on_click=go_to_view,
                args=("Trọng điểm",),
            )

    with quiz_col:
        with st.container(horizontal=True, key="stat_row"):
            st.metric("Trọng điểm", len(summary))
            st.metric("Liên quan quiz", quiz_count)
            st.metric("Đoạn bài giảng", len(segments))
        with st.container(border=True, key="quiz_panel"):
            st.markdown("#### :material/quiz: Nên ưu tiên cho quiz")
            quiz_points = [point for point in summary if point.get("quiz")]
            if not quiz_questions:
                st.info(
                    "Chưa có ngân hàng quiz thật được cấp trong MongoDB, nên hệ thống "
                    "không tự gắn nhãn quiz.",
                    icon=":material/database_off:",
                )
            elif quiz_points:
                for point in quiz_points:
                    st.markdown(f"- **{point['title']}**")
                    if point.get("quiz_reason"):
                        st.caption(point["quiz_reason"])
            else:
                st.caption("Chưa có trọng điểm nào khớp dữ liệu quiz.")

    st.space("small")
    st.markdown("### Cách sử dụng")
    steps = st.columns(3)
    with steps[0].container(border=True):
        st.badge("1", color="blue")
        st.markdown("**Đọc trọng điểm**")
        st.caption("Nắm ý chính theo thứ tự ưu tiên.")
    with steps[1].container(border=True):
        st.badge("2", color="blue")
        st.markdown("**Kiểm chứng nguồn**")
        st.caption("Đối chiếu với transcript nguyên văn.")
    with steps[2].container(border=True):
        st.badge("3", color="blue")
        st.markdown("**Hỏi điều còn vướng**")
        st.caption(f"{AI_DISPLAY_NAME} chỉ trả lời khi có căn cứ.")

elif view == "Trọng điểm":
    outline_col, detail_col = st.columns([.82, 1.65], gap="large")

    with outline_col:
        with st.container(border=True, key="outline"):
            st.markdown("#### Trọng điểm")
            st.caption("Chọn từng ý để đọc. Chỉ một ý được mở mỗi lần.")
            selected_index = st.radio(
                "Danh sách trọng điểm",
                options=list(range(len(summary))),
                format_func=lambda i: f"{i + 1:02d}  {summary[i]['title']}",
                key="point_selector",
                label_visibility="collapsed",
            )

    point = summary[selected_index]
    with detail_col:
        st.progress(
            (selected_index + 1) / len(summary),
            text=f"Trọng điểm {selected_index + 1} / {len(summary)}",
        )
        with st.container(border=True, key="detail_card"):
            with st.container(horizontal=True, vertical_alignment="center"):
                if point.get("quiz"):
                    st.badge("Ưu tiên cho quiz", color="orange", icon=":material/quiz:")
                if point.get("origin") == "transcript-extractive":
                    st.badge(
                        "Trích trực tiếp transcript",
                        color="blue",
                        icon=":material/article:",
                    )
                else:
                    st.badge(
                        f"Tin cậy {point.get('confidence', 'chưa rõ')}",
                        color="green" if point.get("confidence") == "cao" else "gray",
                    )
            st.markdown(f"## {point['title']}")
            st.write(point["summary"])
            if point.get("quiz_reason"):
                st.caption(f":material/lightbulb: {point['quiz_reason']}")

        st.space("small")
        with st.container(border=True, key="source_card"):
            st.markdown("#### Kiểm chứng với transcript gốc")
            citation = st.selectbox(
                "Đoạn nguồn",
                options=point["citations"],
                key=f"source_{cache_key}_{selected_index}",
            )
            if citation in segments:
                source_selection_key = (
                    f"source_selection_{cache_key}_{selected_index}_{citation}"
                )
                selectable_transcript(
                    [{"id": citation, "text": segments[citation].text}],
                    key=source_selection_key,
                    compact=True,
                    height=340,
                    explanations=inline_explanations_for(source_selection_key),
                    pending=inline_pending_for(source_selection_key),
                    focus_segment_id=st.session_state.inline_focus.get(
                        source_selection_key
                    ),
                    on_ask_change=(
                        lambda key=source_selection_key: queue_inline_explanation(key)
                    ),
                    on_followup_change=(
                        lambda key=source_selection_key: queue_inline_followup(key)
                    ),
                )
                st.caption(
                    f":material/verified: Nguồn: {path.title} · "
                    f"[{citation}] · trích nguyên văn"
                )

elif view == "Transcript":
    with st.container(border=True, key="transcript_panel"):
        st.markdown("## :material/article: Transcript buổi học")
        st.caption(
            "Tìm theo khái niệm hoặc mã đoạn. Bôi đen một phần trong cùng một đoạn, "
            f"sau đó chọn “Giải thích bằng {AI_DISPLAY_NAME}”; "
            "câu trả lời sẽ hiện ngay dưới đoạn đó."
        )
        query = st.text_input(
            "Tìm trong transcript",
            placeholder="Ví dụ: deep learning hoặc T04-030",
            icon=":material/search:",
        ).strip().lower()

        all_segments = list(segments.values())
        if query:
            matches = [
                segment
                for segment in all_segments
                if query in segment.id.lower() or query in segment.text.lower()
            ]
        else:
            matches = all_segments

        with st.container(horizontal=True):
            st.badge(f"{len(matches)} kết quả", color="blue")
            st.caption("Hiển thị tối đa 20 đoạn mỗi lượt")

        if matches:
            transcript_selection_key = f"transcript_selection_{cache_key}"
            selectable_transcript(
                [
                    {"id": segment.id, "text": segment.text}
                    for segment in matches[:20]
                ],
                key=transcript_selection_key,
                height=560,
                explanations=inline_explanations_for(transcript_selection_key),
                pending=inline_pending_for(transcript_selection_key),
                focus_segment_id=st.session_state.inline_focus.get(
                    transcript_selection_key
                ),
                on_ask_change=(
                    lambda key=transcript_selection_key: queue_inline_explanation(key)
                ),
                on_followup_change=(
                    lambda key=transcript_selection_key: queue_inline_followup(key)
                ),
            )
        else:
            st.info(
                "Không tìm thấy đoạn phù hợp. Hãy thử một từ khoá ngắn hơn.",
                icon=":material/search_off:",
            )

else:
    with st.container(border=True, key="chat_card"):
        with st.container(horizontal=True, vertical_alignment="center"):
            st.markdown(f"### :material/smart_toy: Hỏi {AI_DISPLAY_NAME}")
            st.space("stretch")
            if api_keys:
                st.badge(
                    f"{AI_DISPLAY_NAME} sẵn sàng",
                    color="green",
                    icon=":material/auto_awesome:",
                )
                include_web_sources = st.toggle(
                    "Bổ sung nguồn web",
                    key="qa_include_web",
                    help=(
                        "Chỉ áp dụng khi câu hỏi đã thuộc bài học. Nguồn web là "
                        "phần đối chiếu bổ sung và luôn có URL thật."
                    ),
                )
            else:
                include_web_sources = False
            if st.session_state.messages and st.button(
                "Xoá", icon=":material/delete_sweep:", key="clear_chat"
            ):
                st.session_state.messages = []
                st.rerun()
        if api_keys:
            st.caption(
                f"Hỏi trực tiếp {AI_DISPLAY_NAME} tại đây; không cần phân tích buổi học trước. "
                f"{AI_DISPLAY_NAME} ưu tiên bài đang mở, từ chối câu ngoài phạm vi "
                "và luôn dẫn tên nguồn cùng trích đoạn khi trả lời."
            )
            if include_web_sources:
                st.caption(
                    ":material/public: Nguồn web đang bật · chỉ bổ sung cho câu hỏi "
                    "đã có căn cứ trong bài, không dùng để trả lời câu hỏi lạc đề."
                )
        else:
            st.caption(
                f"Chưa có API key nên {AI_DISPLAY_NAME} chỉ tìm đoạn transcript liên quan."
            )

        if not st.session_state.messages:
            st.info(
                "Bạn có thể hỏi về một khái niệm, ví dụ hoặc lý do nội dung đó quan trọng.",
                icon=":material/chat_bubble:",
            )
            suggestion = st.pills(
                "Câu hỏi gợi ý",
                [
                    "Tóm tắt buổi học này",
                    f"Giải thích: {summary[0]['title']}",
                    f"Giải thích: {summary[1]['title']}",
                ],
                label_visibility="collapsed",
            )
        else:
            suggestion = None

        if st.session_state.messages:
            with st.container(key="chat_history_scroll"):
                for message in st.session_state.messages:
                    with st.chat_message(
                        message["role"],
                        avatar=":material/smart_toy:"
                        if message["role"] == "assistant"
                        else ":material/person:",
                    ):
                        st.write(message["content"])
                        render_answer_sources(
                            list(message.get("sources") or []),
                            list(message.get("citations") or []),
                        )
                        if message.get("mode") in {"ai", "ai_web"}:
                            web_label = (
                                " · có đối chiếu web"
                                if message.get("mode") == "ai_web"
                                else ""
                            )
                            st.caption(
                                f":material/auto_awesome: {AI_DISPLAY_NAME} · "
                                f"key slot {message['slot'] + 1}{web_label}"
                            )

        typed_question = st.chat_input(
            "Hỏi về nội dung buổi học…",
            key="lesson_chat_input",
            submit_mode="disable",
        )

    prompt = suggestion or (typed_question.strip() if typed_question else None)
    if prompt:
        user_content = str(prompt)
        st.session_state.messages.append({"role": "user", "content": user_content})
        try:
            with st.status(
                f"{AI_DISPLAY_NAME} đang trả lời…", expanded=False
            ) as qa_status:
                def show_qa_attempt(attempt: int, total: int, slot: int) -> None:
                    qa_status.update(
                        label=(
                            f"{AI_DISPLAY_NAME} đang thử key slot {slot + 1} "
                            f"· {attempt}/{total}"
                        )
                    )

                rotation = answer_with_key_rotation(
                    path,
                    str(prompt),
                    api_keys,
                    st.session_state.gemini_key_cursor,
                    on_attempt=show_qa_attempt,
                    include_web=include_web_sources,
                )
                result = rotation.value
                st.session_state.gemini_key_cursor = rotation.next_cursor
                st.session_state.last_key_slot = rotation.used_slot
                qa_status.update(label="Đã trả lời", state="complete")
        except KeyPoolError as exc:
            result = {
                "answer": f"{AI_DISPLAY_NAME} đang tạm thời chưa trả lời được: {exc}",
                "citations": [],
                "sources": [],
                "mode": "error",
            }
            rotation = None
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": result["answer"],
                "citations": result["citations"],
                "sources": result.get("sources", []),
                "mode": result.get("mode"),
                "slot": rotation.used_slot if rotation else None,
            }
        )
        st.rerun()


# Xử lý sau khi component đã được vẽ để trạng thái chờ xuất hiện đúng trong đoạn
# đang đọc. Kết quả được lưu ở state riêng rồi hydrate ngược vào CCv2 ở rerun kế.
pending_inline = st.session_state.get("pending_inline_selection")
if isinstance(pending_inline, dict):
    component_key = str(pending_inline.get("component_key", ""))
    request_kind = str(pending_inline.get("kind", "explanation"))
    selected_text = str(pending_inline.get("text", "")).strip()
    selected_segment_id = str(pending_inline.get("segment_id", "")).strip()
    followup_question = str(pending_inline.get("question", "")).strip()
    explanations = dict(st.session_state.inline_explanations)
    component_threads = dict(explanations.get(component_key, {}))
    segment_thread = list(component_threads.get(selected_segment_id, []))
    try:
        if request_kind == "followup":
            rotation = answer_selection_followup_with_key_rotation(
                path,
                selected_text,
                selected_segment_id,
                followup_question,
                segment_thread,
                api_keys,
                st.session_state.gemini_key_cursor,
            )
        else:
            rotation = explain_selection_with_key_rotation(
                path,
                selected_text,
                selected_segment_id,
                api_keys,
                st.session_state.gemini_key_cursor,
            )
        result = rotation.value
        st.session_state.gemini_key_cursor = rotation.next_cursor
        st.session_state.last_key_slot = rotation.used_slot
    except (KeyPoolError, ValueError) as exc:
        rotation = None
        result = {
            "answer": f"Chưa thể trả lời tại đoạn này: {exc}",
            "citations": [],
            "sources": [],
            "mode": "error",
        }

    segment_thread.append(
        {
            "request_id": pending_inline.get("request_id"),
            "selected_text": selected_text,
            "question": followup_question if request_kind == "followup" else None,
            "segment_id": selected_segment_id,
            "answer": result["answer"],
            "sources": result.get("sources", []),
            "mode": result.get("mode"),
            "slot": rotation.used_slot if rotation else None,
        }
    )
    component_threads[selected_segment_id] = segment_thread
    explanations[component_key] = component_threads
    st.session_state.inline_explanations = explanations
    st.session_state.inline_focus = {
        **st.session_state.inline_focus,
        component_key: selected_segment_id,
    }
    st.session_state.pending_inline_selection = None
    st.rerun()
