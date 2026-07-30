# Reflection — Nguyễn Đức Anh

- **Vai trò:** chủ dự án; thiết kế lát cắt, code prototype, prompt và eval.
- **Phần đã làm:** parser transcript có mã đoạn, bản đồ đọc nhanh, đối chiếu quiz mẫu, điều hướng nguồn, Q&A fail-closed, unit test.
- **AI hỗ trợ:** hỗ trợ scaffold và rà soát; tôi chịu trách nhiệm kiểm tra yêu cầu, chạy test và giải thích code.
- **Bài học từ case fail:** lần test đầu, câu “nấu phở” vẫn bị xem là có căn cứ vì các từ chung trùng transcript. Tôi thêm stopword và ngưỡng overlap, rồi giữ test hồi quy. Bài học: grounding không thể chỉ dựa vào “có vài từ giống nhau”.
- **Cần hoàn tất bằng trải nghiệm thật:** chạy Gemini với key được cấp, chấm golden set, và bổ sung nhận xét sau user validation.

