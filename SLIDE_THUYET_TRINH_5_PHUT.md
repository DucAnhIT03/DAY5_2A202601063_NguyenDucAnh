# TAPHOAMMO — INVESTOR PITCH 5 PHÚT

> Deck gồm 8 slide. Nội dung này đồng bộ với
> `THUYET_TRINH_TAPHOAMMO_5_PHUT.html`.

---

# SLIDE 01 — Mỗi bài học đều có thể bắt kịp

## Tầm nhìn

**taphoammo biến transcript thành lộ trình học ưu tiên có thể kiểm chứng.**

Người học quay lại đúng chỗ, đọc phần cần thiết và hỏi tiếp ngay trong ngữ cảnh.

**Grounded learning layer cho nền tảng đào tạo**

Nhóm thực hiện:

**Nguyễn Đức Anh** · Phan Văn Hiếu · Nguyễn Huy Tỏa · Tạ Long Khánh · Vũ Đăng Huy

---

# SLIDE 02 — Tín hiệu nhu cầu

## Nội dung đã có. Điều còn thiếu là một đường quay lại bài học đáng tin cậy.

Mẫu hành vi ẩn danh **n=34**, chọn từ **369 người dùng**:

- **24/34** có ít nhất một yêu cầu tóm tắt hoặc giải thích.
- **34/34** tương tác với một đoạn nội dung được chọn.
- **21/34** có từ hai lượt hỏi trở lên trong cửa sổ dữ liệu.

Trên toàn bộ tập chatlog:

| Bằng chứng | Kết quả |
|---|---:|
| Tin nhắn thật | **2.522** |
| Cặp hỏi–đáp | **1.261** |
| Phản hồi tutor thiếu dẫn nguồn | **46,2%** |

> Nguồn: VLearn Product Analytics — Production, 22–29/07/2026. Mẫu n=34
> được chọn tái lập bằng SHA-256 trên user_id ẩn danh, gồm 98 tin nhắn học
> viên trong 48 hội thoại. Đây là tín hiệu hành vi, không phải khảo sát tự
> khai hay bằng chứng traction thương mại.

---

# SLIDE 03 — Giá trị sản phẩm

## Từ một transcript dài đến ba quyết định học tập rõ ràng

### 01 · Ưu tiên

**Đọc gì trước?**

2–5 trọng điểm đưa người học vào phần có giá trị cao nhất.

### 02 · Kiểm chứng

**Tin vào đâu?**

Mỗi kết luận mở đúng đoạn transcript làm căn cứ.

### 03 · Hiểu sâu

**Hỏi tiếp thế nào?**

Bôi đen một đoạn và đối thoại với AI ngay tại chỗ.

> Không tạo thêm một kho nội dung — tạo đường vào tốt hơn cho nội dung đã có.

---

# SLIDE 04 — Trải nghiệm sản phẩm

## Một màn hình đưa người học từ “bỏ lỡ” đến “bắt kịp”

1. **Chọn bài hoặc nhập nội dung.**
2. **Đọc trọng điểm có dẫn nguồn.**
3. **Hỏi tiếp ngay trong ngữ cảnh.**

Giao diện kết hợp trong một luồng:

- Danh sách bài học.
- Bản đồ 2–5 trọng điểm cần nắm.
- Citation mở đúng đoạn transcript.
- Chat xuất hiện ngay dưới phần bôi đen và tiếp tục được nhiều lượt.

---

# SLIDE 05 — Lợi thế kỹ thuật bước đầu

## Grounded AI biến độ tin cậy thành một phần của trải nghiệm

**Nguyên tắc sản phẩm: mọi kết luận đều có đường về nguồn.**

| Lớp kiểm soát | Giá trị |
|---|---|
| **Bound** | Khóa phân tích vào đúng phiên bản nội dung |
| **Retrieve** | Chỉ lấy context vừa đủ cho câu hỏi |
| **Verify** | Hậu kiểm citation trong transcript đang mở |
| **Fail closed** | Thiếu căn cứ thì từ chối thay vì đoán |

Model có thể thay đổi; lớp kiểm chứng, phiên bản hóa và dữ liệu học tập vẫn
thuộc về taphoammo.

**Lợi thế tích lũy tiếp theo:** feedback thật để đánh giá trọng điểm và chất
lượng trả lời.

---

# SLIDE 06 — Giả thuyết kinh doanh

## B2B2C: bắt đầu từ nơi transcript đã sẵn sàng

### Người mua

Trường học, trung tâm và học viện doanh nghiệp cần hỗ trợ học viên nhất quán
ở quy mô lớn.

### Đơn vị giá trị

Mô hình thuê bao dự kiến tính theo người học hoạt động, khóa học hoặc giấy
phép cấp tổ chức.

### Đường mở rộng

**Pilot 1–2 khóa có transcript → đo hiệu quả → license cấp tổ chức → tích hợp
toàn LMS**

> Đây là giả thuyết mô hình kinh doanh và go-to-market, chưa phải doanh thu
> hay traction thương mại đã đạt được.

---

# SLIDE 07 — Từ prototype đến thị trường

## Đã chứng minh luồng sản phẩm. 12 tháng tới chứng minh giá trị kinh doanh.

### Đã xây

- Prototype end-to-end: nhập nội dung → trọng điểm → citation → hỏi tại chỗ.
- 6 bài demo được giữ nguyên; đầu vào người dùng được lưu riêng.
- **47/47 kiểm thử tự động đạt** tại lần kiểm tra gần nhất.

### Lộ trình dự kiến

| Thời gian | Mục tiêu |
|---|---|
| **0–3 tháng** | Pilot 1–2 khóa; thu feedback thật và chốt bộ chỉ số |
| **3–6 tháng** | Multi-tenant, quyền riêng tư, dashboard đánh giá AI, kết nối LMS |
| **6–12 tháng** | Chuyển pilot thành hợp đồng đầu tiên và mở rộng theo chương trình |

---

# SLIDE 08 — Đề nghị hợp tác và đầu tư

## Cùng biến mọi nội dung học thành một hành trình có thể bắt kịp

- **2 đối tác pilot** có khóa học đã sẵn transcript.
- **Cố vấn EdTech và LMS** về tích hợp, vận hành và go-to-market.
- **Vòng pre-seed** để sản phẩm hóa, đánh giá AI và triển khai pilot.

### Phân bổ nguồn lực dự kiến

| Hạng mục | Tỷ trọng |
|---|---:|
| Sản phẩm | **45%** |
| AI và đánh giá | **30%** |
| Bảo mật và tích hợp LMS | **15%** |
| Vận hành pilot | **10%** |

**Mục tiêu 12 tháng: pilot → đo lường → hợp đồng đầu tiên.**
