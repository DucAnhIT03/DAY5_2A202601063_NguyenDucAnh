from pathlib import Path

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
    page_title="Catch-up Assistant",
    page_icon=":material/school:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Người dùng yêu cầu thiết kế giao diện; CSS chỉ bổ sung micro-polish cho các
# container có key ổn định. Màu/font chính vẫn do config.toml quản lý.
st.html(
    """
    <style>
    .stMainBlockContainer {max-width: 1440px; padding-top: 1.5rem; padding-bottom: 5rem;}
    .st-key-hero {
        background: linear-gradient(135deg, #312E81 0%, #4F46E5 58%, #7C3AED 100%);
        border: 0 !important; border-radius: 22px; padding: 1.55rem 1.8rem;
        box-shadow: 0 18px 44px rgba(79,70,229,.18); margin-bottom: 1.1rem;
    }
    .st-key-hero h1, .st-key-hero p {color: white !important;}
    .st-key-hero p {opacity: .84;}
    [class*="st-key-point_card_"] {
        background: #FFFFFF; border-radius: 16px; padding: .3rem .45rem;
        box-shadow: 0 5px 20px rgba(30,41,59,.045);
        transition: transform .15s ease, box-shadow .15s ease;
    }
    [class*="st-key-point_card_"]:hover {
        transform: translateY(-2px); box-shadow: 0 10px 26px rgba(79,70,229,.10);
    }
    .st-key-source_panel {
        background: #FFFFFF; box-shadow: 0 5px 20px rgba(30,41,59,.045);
    }
    .st-key-chat_shell {
        background: #FFFFFF; border-radius: 18px; padding: .45rem .7rem 1rem;
        box-shadow: 0 5px 20px rgba(30,41,59,.045);
    }
    .st-key-sidebar_brand {padding: .35rem .15rem .9rem;}
    [data-testid="stSidebar"] [data-testid="stButton"] button {width: 100%;}
    @media (max-width: 900px) {
        .stMainBlockContainer {padding-left: 1rem; padding-right: 1rem;}
        .st-key-hero {padding: 1.2rem; border-radius: 16px;}
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

with st.sidebar:
    with st.container(key="sidebar_brand"):
        st.markdown("## :material/school: VLearn")
        st.caption("Catch-up Assistant · Học đúng trọng tâm")
    selected_name = st.selectbox(
        "Chọn buổi bạn đã bỏ lỡ",
        options=[p.name for p in files],
        index=3 if len(files) > 3 else 0,
        format_func=lambda name: labels[name].replace("Transcript bài giảng (bản sạch) — ", ""),
        key="session_selector",
    )
    st.caption(":material/info: Mỗi lần chỉ phân tích một buổi bạn chủ động mở.")
    with st.popover("Kết nối AI", icon=":material/key:"):
        st.text_input(
            "Gemini API key",
            type="password",
            key="gemini_api_key",
            placeholder="AIza…",
            help="Key chỉ tồn tại trong phiên trình duyệt và không được ghi vào repo.",
        )
        st.caption("Lấy key tại Google AI Studio. Không chia sẻ key trong ảnh demo.")
    active_key = st.session_state.gemini_api_key.strip() or None
    if ai_available(active_key):
        st.badge("Gemini đang bật", color="green", icon=":material/bolt:")
    else:
        st.badge("Demo có kiểm soát", color="orange", icon=":material/science:")
        st.caption("Chưa có API key. Nội dung mẫu được gắn nhãn, không giả là AI thật.")
    with st.expander("Catch-up Assistant làm gì?", icon=":material/help:"):
        st.markdown(
            "- Chọn **3–5 điểm nên đọc trước**\n"
            "- Đánh dấu nội dung **liên quan quiz**\n"
            "- Dẫn về **đúng transcript gốc**\n"
            "- Không tự kết luận bạn đã hiểu bài"
        )

path = next(p for p in files if p.name == selected_name)
segments = segment_map(path)
cache_key = path.name
if cache_key not in st.session_state.summary_cache:
    st.session_state.summary_cache[cache_key] = default_summary(path)

# Khi đã kết nối model, lần đầu mở mỗi buổi sẽ tự chạy đúng flow sản phẩm:
# học viên không cần nhập prompt hay bấm nút để nhận bản đồ đọc nhanh.
if (
    ai_available(active_key)
    and cache_key not in st.session_state.ai_generated_sessions
):
    try:
        with st.spinner("AI đang đọc transcript và đối chiếu quiz…"):
            st.session_state.summary_cache[cache_key] = summarize_with_gemini(
                path, QUIZ_BANK, active_key
            )
        st.session_state.ai_generated_sessions.add(cache_key)
    except Exception as exc:
        st.warning(
            f"Chưa thể phân tích bằng Gemini; đang hiển thị bản demo có kiểm soát. Chi tiết: {exc}",
            icon=":material/warning:",
        )

session_title = labels[path.name].replace("Transcript bài giảng (bản sạch) — ", "")
with st.container(key="hero"):
    st.caption("TRỢ LÝ BẮT KỊP BÀI HỌC")
    st.title("Nắm đúng trọng tâm. Không cần đọc lại từ đầu.")
    st.write(f"Đang xem: **{session_title}**")

with st.container(horizontal=True, vertical_alignment="center"):
    st.badge("3–5 điểm cần đọc trước", color="blue")
    st.badge("Có trích dẫn gốc", color="gray")
    if st.button(
        "Phân tích lại bằng AI",
        icon=":material/auto_awesome:",
        type="primary",
        disabled=not ai_available(active_key),
        help="Mở “Kết nối AI” ở sidebar và nhập Gemini API key."
        if not ai_available(active_key)
        else None,
    ):
        try:
            with st.spinner("Đang đọc transcript và đối chiếu quiz…"):
                st.session_state.summary_cache[cache_key] = summarize_with_gemini(
                    path, QUIZ_BANK, active_key
                )
            st.toast("Đã phân tích bằng Gemini.", icon=":material/check_circle:")
        except Exception as exc:
            st.error(f"Không thể gọi AI: {exc}", icon=":material/error:")

summary = st.session_state.summary_cache[cache_key]
quiz_count = sum(bool(point.get("quiz")) for point in summary)
source_count = len({citation for point in summary for citation in point["citations"]})

metrics = st.columns(4)
metrics[0].metric("Trọng điểm", len(summary), help="Số điểm AI gợi ý đọc trước")
metrics[1].metric("Liên quan quiz", quiz_count, help="Điểm có nội dung khớp quiz cũ")
metrics[2].metric("Nguồn gốc", source_count, help="Số đoạn transcript dùng để kiểm chứng")
metrics[3].metric(
    "Chế độ",
    "Gemini" if ai_available(active_key) else "Demo",
    help="AI thật khi đã kết nối Gemini API key",
)

left, right = st.columns([1.35, 1], gap="large")

with left:
    st.subheader("Lộ trình đọc ưu tiên", anchor=False)
    st.caption("Đọc từ trên xuống; mở nguồn bất cứ lúc nào để tự kiểm chứng.")
    for index, point in enumerate(summary, 1):
        with st.container(border=True, key=f"point_card_{index}"):
            with st.container(horizontal=True, vertical_alignment="center"):
                st.badge(f"Bước {index}", color="blue")
                if point.get("quiz"):
                    st.badge("Nên ưu tiên cho quiz", color="orange", icon=":material/quiz:")
                confidence = point.get("confidence", "chưa rõ")
                confidence_color = "green" if confidence == "cao" else "gray"
                st.badge(f"Tin cậy {confidence}", color=confidence_color)
            st.markdown(f"#### {point['title']}")
            st.write(point["summary"])
            if point.get("quiz_reason"):
                st.caption(f"Vì sao ưu tiên: {point['quiz_reason']}")
            with st.container(horizontal=True):
                for citation in point["citations"]:
                    if st.button(
                        f"Xem [{citation}]",
                        icon=":material/arrow_forward:",
                        key=f"cite-{index}-{citation}",
                    ):
                        st.session_state.selected_citation = citation

with right:
    st.subheader("Nguồn để kiểm chứng", anchor=False)
    st.caption("Transcript nguyên văn của đúng đoạn đang được trích dẫn.")
    with st.container(height=520, border=True, key="source_panel"):
        citation = st.session_state.selected_citation
        if citation and citation in segments:
            st.badge(citation, color="blue", icon=":material/bookmark:")
            st.markdown("#### Đoạn giảng gốc")
            st.write(segments[citation].text)
            st.caption(":material/verified: Trích nguyên văn từ dữ liệu buổi học.")
        else:
            st.markdown("### :material/touch_app: Chọn một nguồn")
            st.write(
                "Bấm **Xem [mã đoạn]** dưới một trọng điểm. "
                "Đoạn giảng gốc sẽ hiện ở đây để bạn đối chiếu."
            )
            st.caption("Bạn không cần tin tuyệt đối vào bản tóm tắt của AI.")

st.space("medium")
with st.container(border=True, key="chat_shell"):
    with st.container(horizontal=True, vertical_alignment="center"):
        st.subheader("Hỏi trợ lý về buổi này", anchor=False)
        if st.session_state.messages and st.button(
            "Xoá hội thoại", icon=":material/delete_sweep:", key="clear_chat"
        ):
            st.session_state.messages = []
            st.rerun()
    st.caption(
        ":material/security: Câu trả lời phải có căn cứ trong transcript; "
        "ngoài phạm vi, trợ lý sẽ nói rõ."
    )
    if not st.session_state.messages:
        suggestion = st.pills(
            "Bạn có thể hỏi",
            [
                "Vì sao symbolic AI chạm trần?",
                "Deep learning học đặc trưng thế nào?",
                "Buổi này có nói về cách làm CV không?",
            ],
            label_visibility="collapsed",
        )
    else:
        suggestion = None

    for message in st.session_state.messages:
        with st.chat_message(
            message["role"],
            avatar=":material/smart_toy:" if message["role"] == "assistant" else None,
        ):
            st.write(message["content"])
            if message.get("citations"):
                st.caption("Nguồn: " + ", ".join(f"[{c}]" for c in message["citations"]))

prompt = suggestion or st.chat_input(
    "Ví dụ: Vì sao symbolic AI chạm trần?",
    submit_mode="disable",
)
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Đang kiểm tra căn cứ…"):
            result = answer_question(path, prompt, active_key)
        st.write(result["answer"])
        if result["citations"]:
            st.caption("Nguồn: " + ", ".join(f"[{c}]" for c in result["citations"]))
        if not result["grounded"]:
            st.caption("Hệ thống đã thu hẹp phạm vi thay vì suy đoán.")
    st.session_state.messages.append(
        {"role": "assistant", "content": result["answer"], "citations": result["citations"]}
    )
    st.rerun()
