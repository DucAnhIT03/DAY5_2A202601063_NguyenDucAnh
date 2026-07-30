import streamlit as st

try:
    from codebase.core import (
        answer_with_key_rotation,
        configured_api_keys,
        default_summary,
        local_transcripts,
        masked_key_label,
        parse_api_keys,
        segment_map,
        summarize_with_key_rotation,
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
except ModuleNotFoundError:
    from core import (
        answer_with_key_rotation,
        configured_api_keys,
        default_summary,
        local_transcripts,
        masked_key_label,
        parse_api_keys,
        segment_map,
        summarize_with_key_rotation,
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


st.set_page_config(
    page_title="Catch-up Assistant · VLearn",
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

FALLBACK_QUIZ_BANK = [
    "Quan hệ giữa AI, machine learning, deep learning và generative AI là gì?",
    "Vì sao symbolic AI chạm trần?",
    "Deep learning khác feature engineering truyền thống ở điểm nào?",
]


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
    quiz_questions = list(mongo_snapshot.quiz_questions) or FALLBACK_QUIZ_BANK
    data_source = "mongodb"
except MongoUnavailable as exc:
    mongo_snapshot = None
    mongo_error = str(exc)
    files = local_transcripts()
    quiz_questions = FALLBACK_QUIZ_BANK
    data_source = "local-fallback"

if not files:
    st.error("Không có transcript nào để hiển thị.", icon=":material/database_off:")
    st.stop()

labels = {transcript.name: transcript.title for transcript in files}

try:
    persisted_api_keys = load_key_pool()
    initial_vault_error = None
except KeyVaultError as exc:
    persisted_api_keys = []
    initial_vault_error = str(exc)

st.session_state.setdefault("messages", [])
st.session_state.setdefault("summary_cache", {})
st.session_state.setdefault("ai_generated_sessions", set())
st.session_state.setdefault("gemini_api_keys_raw", "\n".join(persisted_api_keys))
st.session_state.setdefault("gemini_key_cursor", 0)
st.session_state.setdefault("last_key_slot", None)
st.session_state.setdefault("key_vault_saved_count", len(persisted_api_keys))
st.session_state.setdefault("key_vault_error", initial_vault_error)
st.session_state.setdefault("point_selector", 0)
st.session_state.setdefault("active_view", "Tổng quan")


def reset_lesson() -> None:
    st.session_state.messages = []
    st.session_state.point_selector = 0
    st.session_state.active_view = "Tổng quan"


def go_to_view(view_name: str) -> None:
    st.session_state.active_view = view_name


def reset_key_pool() -> None:
    st.session_state.gemini_key_cursor = 0
    st.session_state.last_key_slot = None
    st.session_state.ai_generated_sessions = set()


def persist_manual_key_pool() -> None:
    reset_key_pool()
    keys = parse_api_keys(st.session_state.get("gemini_api_keys_raw", ""))
    try:
        if keys:
            save_key_pool(keys)
        else:
            clear_key_pool()
        st.session_state.key_vault_saved_count = len(keys)
        st.session_state.key_vault_error = None
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


with st.sidebar:
    st.markdown("## :material/settings: Cài đặt")
    st.markdown("**Nguồn dữ liệu**")
    if data_source == "mongodb":
        st.success("MongoDB đang kết nối", icon=":material/database:")
        st.caption(
            f"`{mongo_snapshot.database}.{mongo_snapshot.collection}` · "
            f"{len(files)} buổi · {mongo_snapshot.segment_count} đoạn"
        )
    else:
        st.error("MongoDB chưa sẵn sàng", icon=":material/database_off:")
        st.caption("Ứng dụng đang dùng file cục bộ dự phòng để không gián đoạn demo.")
    st.divider()
    st.markdown("**Nạp key hàng loạt**")
    uploaded_key_file = st.file_uploader(
        "File Gemini key (.txt)",
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
        help="Nhấn Enter để xuống dòng. Mỗi dòng tạo một slot trong pool.",
        on_change=persist_manual_key_pool,
    )
    st.caption(
        "Mỗi dòng đúng một key · tự bỏ dòng trống, comment bắt đầu bằng # và key trùng."
    )

    combined_key_input = "\n".join(
        part
        for part in (uploaded_key_text, st.session_state.gemini_api_keys_raw)
        if part
    )
    api_keys = configured_api_keys(combined_key_input)
    manual_api_keys = parse_api_keys(st.session_state.gemini_api_keys_raw)
    keys_to_persist = api_keys if uploaded_key_text else manual_api_keys
    if keys_to_persist:
        try:
            save_key_pool(keys_to_persist)
            st.session_state.key_vault_saved_count = len(keys_to_persist)
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
        st.info("Chưa có key · đang chạy demo", icon=":material/science:")
    if st.session_state.key_vault_error:
        st.warning(st.session_state.key_vault_error, icon=":material/lock_open:")
    st.markdown("**Nguyên tắc an toàn**")
    st.caption(
        "Round-robin sau mỗi request · tự chuyển khi hết quota · "
        "chỉ dùng transcript đang mở · không đủ căn cứ thì từ chối."
    )

api_keys = configured_api_keys(combined_key_input)

with st.container(horizontal=True, vertical_alignment="center", key="brandbar"):
    st.markdown("### :material/school: VLearn · Catch-up")
    st.space("stretch")
    if data_source == "mongodb":
        st.badge(
            f"MongoDB · {len(files)} buổi",
            color="blue",
            icon=":material/database:",
        )
    else:
        st.badge("Dữ liệu dự phòng", color="orange", icon=":material/database_off:")
    if api_keys:
        st.badge(
            f"Gemini pool · {len(api_keys)} key",
            color="green",
            icon=":material/check_circle:",
        )
    else:
        st.badge("AI demo · chưa có key", color="gray", icon=":material/science:")

if mongo_error:
    st.warning(
        f"{mongo_error} Ứng dụng đang dùng file cục bộ dự phòng.",
        icon=":material/database_off:",
    )

with st.container(border=True, key="lesson_header"):
    st.caption("TRỢ LÝ BẮT KỊP BÀI HỌC")
    st.title("Hôm nay bạn muốn bắt kịp buổi nào?")
    st.write("Chọn một buổi. Trợ lý sẽ chỉ giữ lại phần cần đọc trước và dẫn về đúng nguồn.")
    selected_name = st.selectbox(
        "Buổi học đã bỏ lỡ",
        options=[p.name for p in files],
        index=3 if len(files) > 3 else 0,
        format_func=lambda name: labels[name].replace(
            "Transcript bài giảng (bản sạch) — ", ""
        ),
        key="session_selector",
        on_change=reset_lesson,
    )

path = next(p for p in files if p.name == selected_name)
segments = segment_map(path)
cache_key = path.name
if cache_key not in st.session_state.summary_cache:
    st.session_state.summary_cache[cache_key] = default_summary(path)

summary = st.session_state.summary_cache[cache_key]
quiz_count = sum(bool(point.get("quiz")) for point in summary)

analyze_requested = False
with st.container(horizontal=True, vertical_alignment="center", key="modebar"):
    view = st.segmented_control(
        "Khu vực",
        ["Tổng quan", "Trọng điểm", "Transcript", "Hỏi trợ lý"],
        key="active_view",
        label_visibility="collapsed",
    )
    st.space("stretch")
    st.caption(f"{len(summary)} trọng điểm · {quiz_count} liên quan quiz · {len(segments)} đoạn transcript")
    if api_keys:
        already_analyzed = cache_key in st.session_state.ai_generated_sessions
        analyze_requested = st.button(
            "Phân tích lại" if already_analyzed else "Phân tích bằng Gemini",
            icon=":material/refresh:" if already_analyzed else ":material/auto_awesome:",
            help="Chỉ bắt đầu gọi Gemini khi bạn bấm nút này.",
            type="secondary" if already_analyzed else "primary",
        )

if analyze_requested:
    try:
        with st.status("Đang phân tích bằng Gemini…", expanded=True) as analysis_status:
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
            st.session_state.summary_cache[cache_key] = rotation.value
            st.session_state.gemini_key_cursor = rotation.next_cursor
            st.session_state.last_key_slot = rotation.used_slot
            st.session_state.ai_generated_sessions.add(cache_key)
            analysis_status.update(
                label=f"Hoàn tất bằng key slot {rotation.used_slot + 1}",
                state="complete",
                expanded=False,
            )
        st.rerun()
    except Exception as exc:
        st.error(f"Không thể gọi Gemini: {exc}")

if view == "Tổng quan":
    main_col, quiz_col = st.columns([1.35, 1], gap="large")
    with main_col:
        with st.container(border=True, key="overview_main"):
            st.caption("BẢN ĐỒ CATCH-UP")
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
            if quiz_points:
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
        st.caption("Trợ lý chỉ trả lời khi có căn cứ.")

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
                st.write(segments[citation].text)
                st.caption(f":material/verified: Nguồn [{citation}] · trích nguyên văn")

elif view == "Transcript":
    with st.container(border=True, key="transcript_panel"):
        st.markdown("## :material/article: Transcript buổi học")
        st.caption(
            "Tìm theo khái niệm hoặc mã đoạn. Kết quả luôn giữ nguyên văn từ bài giảng."
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

        with st.container(height=520, border=True):
            for segment in matches[:20]:
                st.markdown(f"#### [{segment.id}]")
                st.write(segment.text)
                st.space("small")
            if not matches:
                st.info(
                    "Không tìm thấy đoạn phù hợp. Hãy thử một từ khoá ngắn hơn.",
                    icon=":material/search_off:",
                )

else:
    with st.container(border=True, key="chat_card"):
        with st.container(horizontal=True, vertical_alignment="center"):
            st.markdown("### :material/smart_toy: Hỏi về buổi học này")
            st.space("stretch")
            if st.session_state.messages and st.button(
                "Xoá", icon=":material/delete_sweep:", key="clear_chat"
            ):
                st.session_state.messages = []
                st.rerun()
        st.caption("Trợ lý chỉ dùng transcript đang mở; không đủ căn cứ sẽ nói rõ.")

        if not st.session_state.messages:
            st.info(
                "Bạn có thể hỏi về một khái niệm, ví dụ hoặc lý do nội dung đó quan trọng.",
                icon=":material/chat_bubble:",
            )
            suggestion = st.pills(
                "Câu hỏi gợi ý",
                [
                    "Vì sao symbolic AI chạm trần?",
                    "Deep learning học đặc trưng thế nào?",
                    "Buổi này có hướng dẫn làm CV không?",
                ],
                label_visibility="collapsed",
            )
        else:
            suggestion = None

        for message in st.session_state.messages:
            with st.chat_message(
                message["role"],
                avatar=":material/smart_toy:"
                if message["role"] == "assistant"
                else ":material/person:",
            ):
                st.write(message["content"])
                if message.get("citations"):
                    st.caption("Nguồn: " + ", ".join(f"[{c}]" for c in message["citations"]))

        with st.form("question_form", border=False):
            with st.container(horizontal=True, vertical_alignment="bottom"):
                typed_question = st.text_input(
                    "Câu hỏi",
                    placeholder="Nhập điều bạn còn vướng…",
                    label_visibility="collapsed",
                )
                submitted = st.form_submit_button(
                    "Gửi", icon=":material/arrow_upward:", type="primary"
                )

    prompt = suggestion or (typed_question if submitted and typed_question.strip() else None)
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.spinner("Đang tìm căn cứ trong transcript…"):
            rotation = answer_with_key_rotation(
                path,
                prompt,
                api_keys,
                st.session_state.gemini_key_cursor,
            )
            result = rotation.value
            st.session_state.gemini_key_cursor = rotation.next_cursor
            st.session_state.last_key_slot = rotation.used_slot
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": result["answer"],
                "citations": result["citations"],
            }
        )
        st.rerun()
