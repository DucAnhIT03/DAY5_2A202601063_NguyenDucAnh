import streamlit as st

try:
    from codebase.core import (
        answer_with_key_rotation,
        configured_api_keys,
        default_summary,
        masked_key_label,
        segment_map,
        session_files,
        summarize_with_key_rotation,
    )
except ModuleNotFoundError:
    from core import (
        answer_with_key_rotation,
        configured_api_keys,
        default_summary,
        masked_key_label,
        segment_map,
        session_files,
        summarize_with_key_rotation,
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

QUIZ_BANK = [
    "Quan hệ giữa AI, machine learning, deep learning và generative AI là gì?",
    "Vì sao symbolic AI chạm trần?",
    "Deep learning khác feature engineering truyền thống ở điểm nào?",
]

files = session_files()
labels = {
    path.name: path.read_text(encoding="utf-8").splitlines()[0].replace("# ", "")
    for path in files
}

st.session_state.setdefault("messages", [])
st.session_state.setdefault("summary_cache", {})
st.session_state.setdefault("ai_generated_sessions", set())
st.session_state.setdefault("gemini_api_keys_raw", "")
st.session_state.setdefault("gemini_key_cursor", 0)
st.session_state.setdefault("last_key_slot", None)
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


with st.sidebar:
    st.markdown("## :material/settings: Cài đặt")
    st.text_input(
        "Gemini API key pool",
        type="password",
        key="gemini_api_keys_raw",
        placeholder="key-1, key-2, key-3…",
        help="Phân tách nhiều key bằng dấu phẩy, chấm phẩy hoặc khoảng trắng.",
        on_change=reset_key_pool,
    )
    st.caption("Key chỉ nằm trong phiên trình duyệt, không được ghi vào file hoặc log.")

    api_keys = configured_api_keys(st.session_state.gemini_api_keys_raw)
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
    else:
        st.info("Chưa có key · đang chạy demo", icon=":material/science:")
    st.markdown("**Nguyên tắc an toàn**")
    st.caption(
        "Round-robin sau mỗi request · tự chuyển khi hết quota · "
        "chỉ dùng transcript đang mở · không đủ căn cứ thì từ chối."
    )

api_keys = configured_api_keys(st.session_state.gemini_api_keys_raw)

with st.container(horizontal=True, vertical_alignment="center", key="brandbar"):
    st.markdown("### :material/school: VLearn · Catch-up")
    st.space("stretch")
    if api_keys:
        st.badge(
            f"Gemini pool · {len(api_keys)} key",
            color="green",
            icon=":material/check_circle:",
        )
    else:
        st.badge("Dữ liệu demo", color="gray", icon=":material/science:")

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

if api_keys and cache_key not in st.session_state.ai_generated_sessions:
    try:
        with st.spinner("Đang đọc transcript và đối chiếu quiz…"):
            rotation = summarize_with_key_rotation(
                path,
                QUIZ_BANK,
                api_keys,
                st.session_state.gemini_key_cursor,
            )
            st.session_state.summary_cache[cache_key] = rotation.value
            st.session_state.gemini_key_cursor = rotation.next_cursor
            st.session_state.last_key_slot = rotation.used_slot
        st.session_state.ai_generated_sessions.add(cache_key)
        st.toast(
            f"Đã phân tích bằng key slot {rotation.used_slot + 1}.",
            icon=":material/check_circle:",
        )
    except Exception as exc:
        st.warning(f"Chưa thể gọi Gemini. Đang dùng dữ liệu demo. {exc}")

summary = st.session_state.summary_cache[cache_key]
quiz_count = sum(bool(point.get("quiz")) for point in summary)

with st.container(horizontal=True, vertical_alignment="center", key="modebar"):
    view = st.segmented_control(
        "Khu vực",
        ["Tổng quan", "Trọng điểm", "Transcript", "Hỏi trợ lý"],
        key="active_view",
        label_visibility="collapsed",
    )
    st.space("stretch")
    st.caption(f"{len(summary)} trọng điểm · {quiz_count} liên quan quiz · {len(segments)} đoạn transcript")
    if api_keys and st.button(
        "Làm mới", icon=":material/refresh:", help="Phân tích lại bằng Gemini"
    ):
        try:
            with st.spinner("Đang phân tích lại…"):
                rotation = summarize_with_key_rotation(
                    path,
                    QUIZ_BANK,
                    api_keys,
                    st.session_state.gemini_key_cursor,
                )
                st.session_state.summary_cache[cache_key] = rotation.value
                st.session_state.gemini_key_cursor = rotation.next_cursor
                st.session_state.last_key_slot = rotation.used_slot
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
