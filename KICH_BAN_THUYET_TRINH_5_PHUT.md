# KỊCH BẢN THUYẾT TRÌNH DỰ ÁN TAPHOAMMO — 5 PHÚT

> Kịch bản dành cho một người trình bày, ưu tiên trưởng nhóm Nguyễn Đức Anh. Phần trong dấu `[ ]` là thao tác hoặc ghi chú, không đọc thành lời.

## 1. Thông tin nhóm

| Thành viên | Mã học viên | Vai trò chính |
|---|---|---|
| Nguyễn Đức Anh — Trưởng nhóm | 2A202601063 | Kiến trúc, core AI, prompt, backend, giao diện, eval và demo |
| Phan Văn Hiếu | 2A202601227 | Phân tích transcript, evidence và citation |
| Nguyễn Huy Tỏa | 2A202601697 | Golden set, evaluation và rà soát ca lỗi |
| Tạ Long Khánh | 2A202601197 | Kiểm thử giao diện và UI/UX |
| Vũ Đăng Huy | 2A202601761 | User validation và nội dung thuyết trình |

## 2. Chuẩn bị trước khi trình bày

- Mở sẵn ứng dụng tại `http://localhost:8501`.
- Bật MongoDB và kiểm tra badge **MongoDB thật · 6 buổi**.
- Chuẩn bị sẵn một bài đã có analysis để không phải chờ Gemini.
- Mở sẵn một trọng điểm có citation.
- Chuẩn bị câu hỏi ngoài phạm vi: **“Buổi này hướng dẫn nấu phở như thế nào?”**
- Không mở hoặc đọc API key trên màn hình.
- Luyện một lần với đồng hồ; mục tiêu kết thúc trong khoảng 4 phút 45 giây đến 5 phút.

---

## 3. Lời thoại chính

### 0:00–0:25 — Chào hỏi và giới thiệu

**Lời nói:**

> Em xin chào thầy cô và các bạn. Nhóm em gồm năm thành viên: Nguyễn Đức Anh là trưởng nhóm, cùng Phan Văn Hiếu, Nguyễn Huy Tỏa, Tạ Long Khánh và Vũ Đăng Huy. Hôm nay nhóm em xin trình bày **taphoammo — trợ lý giúp học viên bắt kịp một buổi học đã bỏ lỡ**.

### 0:25–0:55 — Vấn đề

**Lời nói:**

> Khi nghỉ một buổi, học viên phải đọc transcript dài nhưng không biết phần nào cần ưu tiên. Sáu transcript nhóm khảo sát có 700 đoạn, gồm nhiều hoạt động lớp và hơn một trăm đoạn có tín hiệu “không nghe rõ”. Đọc hết thì tốn thời gian, còn đọc lướt dễ bỏ sót kiến thức. Bản tóm tắt AI tự do cũng chưa an toàn vì người học không biết thông tin đến từ đâu.

### 0:55–1:30 — Giải pháp của nhóm

**Lời nói:**

> Vì vậy, nhóm không làm công cụ tóm tắt chung. taphoammo xử lý **một buổi mỗi lần**, chọn từ hai đến năm trọng điểm và gắn mã nguồn để kiểm chứng. Nếu có quiz cũ, hệ thống mới đối chiếu; không có quiz thì không tự đoán nội dung sẽ thi. Người học vẫn là người quyết định cuối cùng.

### 1:30–2:10 — Luồng hoạt động

**Lời nói:**

> Luồng sử dụng có bốn bước. Học viên chọn bài demo hoặc nhập transcript bằng TXT, Markdown hay JSON. Hệ thống kiểm tra, chia thành các đoạn có mã và lưu vào MongoDB trong Docker. Khi người dùng bấm phân tích, transcript và quiz được gửi qua Gemini. Backend kiểm tra số lượng, nội dung trùng và citation trước khi lưu kết quả theo fingerprint.

> Nếu transcript hoặc quiz thay đổi, fingerprint thay đổi nên kết quả AI cũ không được dùng lại. Sáu bài demo vẫn được giữ nguyên, còn bài mới mang nhãn **Bạn thêm**.

### 2:10–2:55 — Cách AI chọn trọng điểm và trả lời đúng trọng tâm

**Lời nói:**

> Để chọn trọng điểm, prompt ưu tiên khái niệm, quan hệ nguyên nhân–kết quả, quy trình và ví dụ; đồng thời loại chào hỏi, hành chính, hoạt động lớp và ý lặp. Gemini phải trả JSON theo schema cố định với độ ngẫu nhiên thấp. Trọng điểm không có mã nguồn hợp lệ sẽ không được lưu.

> Khi học viên hỏi, retrieval chuẩn hóa tiếng Việt có dấu hoặc không dấu, loại từ dừng và xếp hạng các đoạn liên quan. Chỉ tối đa bốn đoạn tốt nhất được gửi cho Gemini. AI phải kết luận ngay câu đầu, trả lời ngắn và có citation. Không có căn cứ thì hệ thống từ chối thay vì suy đoán.

### 2:55–4:05 — Demo trực tiếp

**Thao tác 1 — Tổng quan, khoảng 15 giây**

`[Chỉ vào badge MongoDB, danh sách bài và số trọng điểm.]`

**Lời nói:**

> Dữ liệu runtime đang được đọc từ MongoDB. Giao diện phân biệt bài Demo và bài Bạn thêm. Tổng quan cho biết số trọng điểm, nội dung liên quan quiz và số đoạn nguồn.

**Thao tác 2 — Mở trọng điểm và nguồn, khoảng 20 giây**

`[Mở tab Trọng điểm, chọn một ý và chỉ vào đoạn nguồn.]`

**Lời nói:**

> Mỗi trọng điểm có giải thích, mức tin cậy và citation. Học viên mở được nguyên văn đúng đoạn nguồn, nên bản tóm tắt không thay thế transcript.

**Thao tác 3 — Hỏi ngoài phạm vi, khoảng 20 giây**

`[Mở Hỏi taphoammo AI, nhập “Buổi này hướng dẫn nấu phở như thế nào?”.]`

**Lời nói:**

> Câu hỏi này không có trong bài nên trợ lý từ chối và không gắn citation giả.

**Thao tác 4 — Bôi đen và hỏi tiếp, khoảng 15 giây**

`[Nếu đã chuẩn bị sẵn kết quả, mở phần bôi đen có mini-chat. Không chờ request mới nếu mạng chậm.]`

**Lời nói:**

> Người dùng có thể bôi đen để hỏi ngay tại đoạn. Backend xác minh phần chọn thuộc đúng nguồn. Câu trả lời xuất hiện tại chỗ, có thể hỏi tiếp trong cùng ngữ cảnh và lịch sử dài sẽ cuộn riêng.

### 4:05–4:35 — Độ tin cậy và kỹ thuật vận hành

**Lời nói:**

> Hệ thống nhận nhiều Gemini API key, mỗi dòng một key. Pool chạy round-robin và tự chuyển slot khi hết quota. Key được mã hóa bằng Windows DPAPI, không lưu trong Git và chỉ hiện dạng đã che. Request dùng non-streaming nên người dùng không nhận câu trả lời dở dang.

> Cả 32 unit test đều đạt. Golden set có 20 ca gồm câu đúng nguồn, câu mơ hồ, câu ngoài phạm vi và citation giả.

### 4:35–5:00 — Giá trị và kết luận

**Lời nói:**

> taphoammo kết hợp xử lý dữ liệu, retrieval, structured output, hậu kiểm citation và MongoDB versioning, chứ không chỉ dựa vào một prompt. Sản phẩm giúp học viên biết **đọc gì trước và kiểm chứng ở đâu**.

> Thông điệp của nhóm là: **không dùng AI để thay thế nguồn học, mà dùng AI để dẫn người học đến đúng phần của nguồn học nhanh hơn**. Nhóm em xin cảm ơn thầy cô và các bạn.

---

## 4. Câu chuyển khi demo gặp sự cố

Nếu Gemini phản hồi chậm:

> Do lời gọi AI phụ thuộc kết nối mạng, em xin dùng kết quả đã được hệ thống lưu theo fingerprint trong MongoDB. Cơ chế lưu này cũng là cách sản phẩm tránh gọi lại AI không cần thiết.

Nếu một API key hết quota:

> Đây chính là tình huống pool key xử lý. Hệ thống sẽ thử slot tiếp theo và chỉ hiển thị kết quả khi request hoàn tất.

Nếu MongoDB mất kết nối:

> Hệ thống chủ động dừng thay vì tráo sang dữ liệu giả. Đây là lựa chọn fail-closed để trạng thái demo luôn phản ánh đúng nguồn dữ liệu.

Nếu không đủ thời gian:

> Em xin bỏ qua thao tác hỏi mới và mở kết quả đã chuẩn bị sẵn để tập trung vào citation và cơ chế kiểm chứng nguồn.

---

## 5. Các câu hỏi phản biện có thể gặp

### Vì sao không dùng ChatGPT hoặc Gemini trực tiếp?

Vì model chat thông thường chưa bảo đảm chỉ dùng đúng transcript, chưa có retrieval riêng theo bài, chưa hậu kiểm mã nguồn và chưa lưu kết quả theo fingerprint. Giá trị của taphoammo nằm ở toàn bộ pipeline kiểm soát trước và sau AI.

### Hệ thống có bảo đảm AI không bao giờ bịa không?

Không nên khẳng định tuyệt đối. Prototype giảm rủi ro bằng context hẹp, temperature thấp, JSON Schema, `supported`, citation hợp lệ và cơ chế từ chối. Hiện hệ thống mới kiểm tra mã đoạn tồn tại; semantic verifier độc lập là hướng phát triển tiếp theo.

### Tại sao dùng retrieval từ khóa thay vì vector database?

Phạm vi prototype nhỏ nên lexical retrieval dễ giải thích, chạy nhanh và kiểm thử deterministic. Hướng phát triển là hybrid search kết hợp lexical và embedding để xử lý từ đồng nghĩa hoặc cách diễn đạt khác.

### Nếu transcript thay đổi thì sao?

Mỗi bài có fingerprint SHA-256. Analysis chỉ được đọc lại khi tên bài và fingerprint cùng khớp. Với bài người dùng, fingerprint còn bao gồm quiz đã chuẩn hóa.

### “Dữ liệu thật” trong dự án nghĩa là gì?

Runtime đọc và ghi thật trong MongoDB Docker, không dùng fallback trong bộ nhớ. Sáu bài demo là data pack đã ẩn danh; bài người dùng nhập được lưu riêng. Nhóm không gọi dữ liệu demo là dữ liệu cá nhân thật của người dùng.

### Hạn chế lớn nhất hiện tại là gì?

Retrieval vẫn chủ yếu là lexical, chưa có đăng nhập/phân quyền, DPAPI phụ thuộc Windows và hậu kiểm citation chưa chứng minh ngữ nghĩa từng mệnh đề. Đây là các hạng mục ưu tiên nếu chuyển prototype thành sản phẩm production.

---

## 6. Câu chốt cần nhớ

> **taphoammo không thay thế transcript; taphoammo giúp học viên tìm đúng phần cần đọc, hiểu đúng phần đang vướng và luôn quay lại được nguồn gốc.**
