import streamlit as st

try:
    from codebase.core import (
        ai_available,
        answer_question,
        default_summary,
        segment_map,
        session_files,
        summarize_with_gemini,
    )
except ModuleNotFoundError:
    from core import (
        ai_available,
        answer_question,
        default_summary,
        segment_map,
        session_files,
        summarize_with_gemini,
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
st.session_state.setdefault("gemini_api_key", "")
st.session_state.setdefault("point_selector", 0)
st.session_state.setdefault("active_view", "Lộ trình đọc")


def reset_lesson() -> None:
    st.session_state.messages = []
    st.session_state.point_selector = 0


with st.sidebar:
    st.markdown("## :material/settings: Cài đặt")
    st.text_input(
        "Gemini API key",
        type="password",
        key="gemini_api_key",
        placeholder="AIza…",
        help="Key chỉ được giữ trong phiên trình duyệt.",
    )
    st.caption("Không để lộ API key khi trình chiếu.")
    st.markdown("**Nguyên tắc an toàn**")
    st.caption("Chỉ dùng transcript đang mở · luôn có nguồn · không đủ căn cứ thì từ chối.")

active_key = st.session_state.gemini_api_key.strip() or None

with st.container(horizontal=True, vertical_alignment="center", key="brandbar"):
    st.markdown("### :material/school: VLearn · Catch-up")
    st.space("stretch")
    if ai_available(active_key):
        st.badge("Gemini đã kết nối", color="green", icon=":material/check_circle:")
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

if ai_available(active_key) and cache_key not in st.session_state.ai_generated_sessions:
    try:
        with st.spinner("Đang đọc transcript và đối chiếu quiz…"):
            st.session_state.summary_cache[cache_key] = summarize_with_gemini(
                path, QUIZ_BANK, active_key
            )
        st.session_state.ai_generated_sessions.add(cache_key)
        st.toast("Đã phân tích xong buổi học.", icon=":material/check_circle:")
    except Exception as exc:
        st.warning(f"Chưa thể gọi Gemini. Đang dùng dữ liệu demo. {exc}")

summary = st.session_state.summary_cache[cache_key]
quiz_count = sum(bool(point.get("quiz")) for point in summary)

with st.container(horizontal=True, vertical_alignment="center", key="modebar"):
    view = st.segmented_control(
        "Khu vực",
        ["Lộ trình đọc", "Hỏi trợ lý"],
        key="active_view",
        label_visibility="collapsed",
    )
    st.space("stretch")
    st.caption(f"{len(summary)} trọng điểm · {quiz_count} liên quan quiz · {len(segments)} đoạn transcript")
    if ai_available(active_key) and st.button(
        "Làm mới", icon=":material/refresh:", help="Phân tích lại bằng Gemini"
    ):
        try:
            with st.spinner("Đang phân tích lại…"):
                st.session_state.summary_cache[cache_key] = summarize_with_gemini(
                    path, QUIZ_BANK, active_key
                )
            st.rerun()
        except Exception as exc:
            st.error(f"Không thể gọi Gemini: {exc}")

if view == "Lộ trình đọc":
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
            result = answer_question(path, prompt, active_key)
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": result["answer"],
                "citations": result["citations"],
            }
        )
        st.rerun()
