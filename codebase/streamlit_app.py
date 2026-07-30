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
    initial_sidebar_state="expanded",
)

st.html(
    """
    <style>
    .stApp {background:
        radial-gradient(circle at 92% 0%, rgba(99,102,241,.10), transparent 25rem),
        #F8F9FD;}
    .stMainBlockContainer {max-width: 1380px; padding: 1.25rem 2rem 5rem;}
    .st-key-topbar {padding: .2rem .1rem .8rem;}
    .st-key-topbar h3 {margin: 0; letter-spacing: -.02em;}
    .st-key-hero {
        background: linear-gradient(125deg, #25205F 0%, #4338CA 58%, #6D5CE7 100%);
        border: 0 !important; border-radius: 24px; padding: 1.7rem 2rem 1.45rem;
        box-shadow: 0 20px 50px rgba(55,48,163,.20); margin-bottom: 1.25rem;
        overflow: hidden;
    }
    .st-key-hero h1, .st-key-hero p, .st-key-hero label {color: #FFFFFF !important;}
    .st-key-hero h1 {max-width: 850px; letter-spacing: -.035em; margin-bottom: .35rem;}
    .st-key-hero p {color: #E3E2FF !important; max-width: 850px;}
    .st-key-hero [data-baseweb="select"] > div {
        background: rgba(255,255,255,.98); border-color: rgba(255,255,255,.4);
    }
    .st-key-summary_strip {
        background: #FFFFFF; border: 1px solid #E7E9F2; border-radius: 16px;
        padding: .25rem .8rem; box-shadow: 0 5px 18px rgba(30,41,59,.04);
    }
    [class*="st-key-point_card_"] {
        background: #FFFFFF; border-radius: 17px; padding: .28rem .45rem;
        border: 1px solid #E5E7F0 !important;
        box-shadow: 0 5px 18px rgba(30,41,59,.045);
        transition: transform .16s ease, box-shadow .16s ease, border-color .16s ease;
    }
    [class*="st-key-point_card_"]:hover {
        transform: translateY(-2px); border-color: #C7D2FE !important;
        box-shadow: 0 12px 28px rgba(67,56,202,.10);
    }
    .st-key-source_panel {
        background: linear-gradient(180deg, #FFFFFF 0%, #FBFCFF 100%);
        border: 1px solid #E5E7F0 !important; border-radius: 17px;
        box-shadow: 0 5px 18px rgba(30,41,59,.045);
    }
    .st-key-chat_shell {
        background: #FFFFFF; border: 1px solid #E5E7F0 !important;
        border-radius: 20px; padding: .45rem .85rem 1rem;
        box-shadow: 0 8px 26px rgba(30,41,59,.055);
    }
    .st-key-sidebar_brand {padding: .25rem .1rem .65rem;}
    [data-testid="stSidebar"] {box-shadow: 8px 0 28px rgba(30,41,59,.035);}
    [data-testid="stSidebar"] [data-testid="stButton"] button {width: 100%;}
    [data-testid="stMetric"] {padding: .35rem .2rem;}
    [data-testid="stChatMessage"] {border-radius: 14px; padding: .6rem .8rem;}
    @media (max-width: 900px) {
        .stMainBlockContainer {padding: .8rem 1rem 4rem;}
        .st-key-hero {padding: 1.25rem; border-radius: 18px;}
        .st-key-hero h1 {font-size: 2rem !important;}
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
st.session_state.setdefault("selected_citation", None)
st.session_state.setdefault("gemini_api_key", "")


def reset_session_context() -> None:
    st.session_state.messages = []
    st.session_state.selected_citation = None


with st.sidebar:
    with st.container(key="sidebar_brand"):
        st.markdown("## :material/school: VLearn")
        st.caption("Catch-up Assistant · Học đúng trọng tâm")

    st.markdown("**Trạng thái trợ lý**")
    with st.popover("Kết nối Gemini", icon=":material/key:"):
        st.text_input(
            "Gemini API key",
            type="password",
            key="gemini_api_key",
            placeholder="AIza…",
            help="Key chỉ tồn tại trong phiên trình duyệt và không được ghi vào repo.",
        )
        st.caption("Key chỉ dùng trong phiên này. Không để lộ key khi trình chiếu.")

    active_key = st.session_state.gemini_api_key.strip() or None
    if ai_available(active_key):
        st.success("Gemini đã sẵn sàng", icon=":material/check_circle:")
    else:
        st.warning("Đang dùng dữ liệu demo", icon=":material/science:")
        st.caption("Kết nối Gemini để chạy quyết định AI thật khi demo.")

    with st.expander("Trợ lý làm được gì?", icon=":material/help:"):
        st.markdown(
            "- Chọn **3–5 điểm nên đọc trước**\n"
            "- Đánh dấu nội dung **liên quan quiz**\n"
            "- Dẫn về **đúng transcript gốc**\n"
            "- Từ chối khi **không đủ căn cứ**"
        )
    st.caption("VLearn · Prototype 1.0")

with st.container(horizontal=True, vertical_alignment="center", key="topbar"):
    st.markdown("### :material/auto_stories: Không bỏ lỡ phần quan trọng")
    st.space("stretch")
    if ai_available(active_key):
        st.badge("AI đang hoạt động", color="green", icon=":material/bolt:")
    else:
        st.badge("Demo an toàn", color="orange", icon=":material/shield:")

with st.container(key="hero"):
    st.caption("CATCH-UP ASSISTANT")
    st.title("Bắt kịp một buổi học trong vài phút")
    st.write(
        "Chọn buổi bạn đã lỡ. Trợ lý sẽ chỉ ra phần nên đọc trước, "
        "đánh dấu nội dung liên quan quiz và luôn dẫn về nguồn gốc."
    )
    selected_name = st.selectbox(
        "Bạn đã bỏ lỡ buổi nào?",
        options=[p.name for p in files],
        index=3 if len(files) > 3 else 0,
        format_func=lambda name: labels[name].replace(
            "Transcript bài giảng (bản sạch) — ", ""
        ),
        key="session_selector",
        on_change=reset_session_context,
    )

path = next(p for p in files if p.name == selected_name)
segments = segment_map(path)
cache_key = path.name
if cache_key not in st.session_state.summary_cache:
    st.session_state.summary_cache[cache_key] = default_summary(path)

if ai_available(active_key) and cache_key not in st.session_state.ai_generated_sessions:
    try:
        with st.spinner("AI đang đọc transcript và đối chiếu quiz…"):
            st.session_state.summary_cache[cache_key] = summarize_with_gemini(
                path, QUIZ_BANK, active_key
            )
        st.session_state.ai_generated_sessions.add(cache_key)
        st.toast("Đã tạo lộ trình đọc bằng Gemini.", icon=":material/check_circle:")
    except Exception as exc:
        st.warning(
            f"Chưa thể gọi Gemini; đang dùng dữ liệu demo có kiểm soát. {exc}",
            icon=":material/warning:",
        )

summary = st.session_state.summary_cache[cache_key]
quiz_count = sum(bool(point.get("quiz")) for point in summary)
source_count = len({citation for point in summary for citation in point["citations"]})

with st.container(horizontal=True, vertical_alignment="center", key="summary_strip"):
    st.markdown(f"**:material/route: {len(summary)} trọng điểm**")
    st.markdown(f"**:material/quiz: {quiz_count} điểm nên ưu tiên cho quiz**")
    st.markdown(f"**:material/bookmarks: {source_count} đoạn nguồn**")
    st.space("stretch")
    if st.button(
        "Phân tích lại",
        icon=":material/auto_awesome:",
        type="primary",
        disabled=not ai_available(active_key),
        help="Kết nối Gemini trong sidebar để chạy AI thật."
        if not ai_available(active_key)
        else None,
    ):
        try:
            with st.spinner("Đang phân tích lại nội dung buổi học…"):
                st.session_state.summary_cache[cache_key] = summarize_with_gemini(
                    path, QUIZ_BANK, active_key
                )
            st.toast("Đã cập nhật lộ trình đọc.", icon=":material/check_circle:")
            st.rerun()
        except Exception as exc:
            st.error(f"Không thể gọi Gemini: {exc}", icon=":material/error:")

st.space("small")
left, right = st.columns([1.35, 1], gap="large")

with left:
    st.subheader("Lộ trình đọc ưu tiên", anchor=False)
    st.caption("Bắt đầu từ trên xuống; mỗi ý đều có nguồn để bạn kiểm chứng.")
    for index, point in enumerate(summary, 1):
        with st.container(border=True, key=f"point_card_{index}"):
            with st.container(horizontal=True, vertical_alignment="center"):
                st.badge(f"{index:02d}", color="blue")
                if point.get("quiz"):
                    st.badge(
                        "Ưu tiên cho quiz", color="orange", icon=":material/quiz:"
                    )
                confidence = point.get("confidence", "chưa rõ")
                st.badge(
                    f"Tin cậy {confidence}",
                    color="green" if confidence == "cao" else "gray",
                )
            st.markdown(f"#### {point['title']}")
            st.write(point["summary"])
            if point.get("quiz_reason"):
                st.caption(f":material/lightbulb: {point['quiz_reason']}")
            with st.container(horizontal=True):
                for citation in point["citations"]:
                    if st.button(
                        f"Mở [{citation}]",
                        icon=":material/arrow_outward:",
                        key=f"cite-{index}-{citation}",
                    ):
                        st.session_state.selected_citation = citation

with right:
    st.subheader("Kiểm chứng với bài giảng gốc", anchor=False)
    st.caption("Bạn luôn là người quyết định có tin bản tóm tắt hay không.")
    with st.container(height=540, border=True, key="source_panel"):
        citation = st.session_state.selected_citation
        if citation and citation in segments:
            st.badge(citation, color="blue", icon=":material/bookmark:")
            st.markdown("#### Đoạn transcript gốc")
            st.write(segments[citation].text)
            st.caption(":material/verified: Trích nguyên văn từ buổi học đang mở.")
        else:
            st.markdown("### :material/touch_app: Mở một trích dẫn")
            st.write(
                "Chọn **Mở [mã đoạn]** dưới một trọng điểm. "
                "Đoạn giảng gốc sẽ xuất hiện tại đây để bạn đối chiếu."
            )
            st.info(
                "Bản tóm tắt chỉ là bản đồ định hướng, không thay thế bài giảng gốc.",
                icon=":material/info:",
            )

st.space("medium")
with st.container(border=True, key="chat_shell"):
    with st.container(horizontal=True, vertical_alignment="center"):
        st.subheader("Hỏi thêm về buổi học", anchor=False)
        st.space("stretch")
        if st.session_state.messages and st.button(
            "Bắt đầu lại", icon=":material/replay:", key="clear_chat"
        ):
            st.session_state.messages = []
            st.rerun()
    st.caption(
        ":material/shield: Trợ lý chỉ trả lời từ transcript đang mở. "
        "Nếu không đủ căn cứ, trợ lý sẽ từ chối thay vì đoán."
    )

    if not st.session_state.messages:
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

prompt = suggestion or st.chat_input(
    "Hỏi một điều về buổi học này…", submit_mode="disable"
)
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar=":material/person:"):
        st.write(prompt)
    with st.chat_message("assistant", avatar=":material/smart_toy:"):
        with st.spinner("Đang tìm căn cứ trong transcript…"):
            result = answer_question(path, prompt, active_key)
        st.write(result["answer"])
        if result["citations"]:
            st.caption("Nguồn: " + ", ".join(f"[{c}]" for c in result["citations"]))
        if not result["grounded"]:
            st.caption(":material/shield: Đã thu hẹp phạm vi thay vì suy đoán.")
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": result["answer"],
            "citations": result["citations"],
        }
    )
    st.rerun()
