# Reflection — Phan Văn Hiếu

- **Vai trò:** hỗ trợ mining transcript/chatlog, thu thập evidence và đối chiếu mã trích dẫn.
- **Phần đã làm:**
  - Viết script `scripts/mining_transcript.py` để phân tích tự động 6 file transcript (700 đoạn, mã Txx-NNN): đếm tổng đoạn, đoạn hoạt động lớp, đoạn chứa `[không nghe rõ]`, và đoạn nội dung giảng thực sự.
  - Đối chiếu toàn bộ mã trích dẫn trong `golden-set.csv` (20 case) và `spec.md` (5 citation) với transcript thật — kết quả: 100% tồn tại, không có mã bịa.
  - Thu thập evidence cho spec §1: xác nhận 55/700 đoạn (7,9%) là hoạt động lớp, 103/700 đoạn (14,7%) chứa `[không nghe rõ]`, 645 đoạn còn lại là nội dung giảng.
  - Tạo báo cáo `eval/evidence-mining-report.md` tổng hợp kết quả mining và đối chiếu.
- **AI hỗ trợ:** sử dụng AI để scaffold cấu trúc script mining; tôi chịu trách nhiệm kiểm tra kết quả đối chiếu, xác minh mã đoạn đúng nội dung, và đảm bảo không sao chép data pack vào repo.
- **Bài học:** khi đối chiếu citation, không thể chỉ kiểm tra mã đoạn tồn tại mà phải đọc nội dung đoạn đó để xác nhận ý chính thực sự khớp. Ví dụ, đoạn `[T04-021]` trong golden set (GS14) là đoạn hoạt động kỹ thuật — AI cần nhận diện loại đoạn này để không chọn làm điểm chính. Các đoạn có `[không nghe rõ]` cần được đánh dấu riêng để tránh AI suy diễn sai.
- **Cần hoàn tất bằng trải nghiệm thật:** tham gia chấm golden set cùng nhóm sau khi chạy Gemini thật, bổ sung mining chatlog VLearn (2.522 dòng hội thoại) để tìm thêm evidence về pain point, và hoàn thiện nhận xét sau user validation.
