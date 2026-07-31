# Báo cáo Evidence Mining — Phan Văn Hiếu (2A202601227)

> Phụ trách: mining transcript/chatlog, thu thập evidence và đối chiếu mã trích dẫn

## 1. Thống kê transcript

| File | Tổng đoạn | Hoạt động lớp | [không nghe rõ] | Nội dung giảng |
|---|---:|---:|---:|---:|
| transcript-01-clean.md | 89 | 2 | 14 | 87 |
| transcript-02-clean.md | 43 | 6 | 10 | 37 |
| transcript-03-clean.md | 154 | 10 | 11 | 144 |
| transcript-04-clean.md | 98 | 9 | 15 | 89 |
| transcript-05-clean.md | 154 | 17 | 25 | 137 |
| transcript-06-clean.md | 162 | 11 | 28 | 151 |
| **Tổng cộng** | **700** | **55** (7.9%) | **103** (14.7%) | **645** (92.1%) |

## 2. Nhận xét evidence cho spec §1

- Tổng cộng **700 đoạn** có mã trích dẫn `[Txx-NNN]` trên 6 transcript.
- **55/700 đoạn (7.9%)** là `[Hoạt động lớp]` — nên loại khỏi kết quả phân tích AI, không chứa nội dung giảng.
- **103/700 đoạn (14.7%)** chứa `[không nghe rõ]` — cần cẩn trọng, AI không nên suy diễn từ các đoạn này.
- **645/700 đoạn (92.1%)** là nội dung giảng thực sự — đây là nguồn chính để AI trích xuất trọng điểm.

Số liệu trên khớp với mô tả trong `spec.md` §1 và `transcript/README.md`.

## 3. Đối chiếu mã trích dẫn — golden-set.csv

| Case | source_ref | Trạng thái | Tìm thấy trong |
|---|---|---|---|
| GS01 | T04-015 | ✅ TỒN TẠI | transcript-04-clean.md |
| GS02 | T04-025 | ✅ TỒN TẠI | transcript-04-clean.md |
| GS03 | T04-029 | ✅ TỒN TẠI | transcript-04-clean.md |
| GS04 | T04-030 | ✅ TỒN TẠI | transcript-04-clean.md |
| GS05 | T04-032 | ✅ TỒN TẠI | transcript-04-clean.md |
| GS06 | T04-022 | ✅ TỒN TẠI | transcript-04-clean.md |
| GS07 | T04-018 | ✅ TỒN TẠI | transcript-04-clean.md |
| GS08 | T04-031 | ✅ TỒN TẠI | transcript-04-clean.md |
| GS09 | none | N/A (không cần đối chiếu) | - |
| GS10 | none | N/A (không cần đối chiếu) | - |
| GS11 | fake | N/A (không cần đối chiếu) | - |
| GS12 | none | N/A (không cần đối chiếu) | - |
| GS13 | none | N/A (không cần đối chiếu) | - |
| GS14 | T04-021 | ✅ TỒN TẠI | transcript-04-clean.md |
| GS15 | T04-011 | ✅ TỒN TẠI | transcript-04-clean.md |
| GS16 | all | N/A (không cần đối chiếu) | - |
| GS17 | none | N/A (không cần đối chiếu) | - |
| GS18 | none | N/A (không cần đối chiếu) | - |
| GS19 | T04-015 | ✅ TỒN TẠI | transcript-04-clean.md |
| GS20 | T04-025 | ✅ TỒN TẠI | transcript-04-clean.md |

**Kết quả:** 12 tồn tại · 8 N/A · 0 không tìm thấy

## 4. Đối chiếu mã trích dẫn — spec.md

| Citation | Trạng thái | Tìm thấy trong |
|---|---|---|
| T04-015 | ✅ TỒN TẠI | transcript-04-clean.md |
| T04-025 | ✅ TỒN TẠI | transcript-04-clean.md |
| T04-029 | ✅ TỒN TẠI | transcript-04-clean.md |
| T04-030 | ✅ TỒN TẠI | transcript-04-clean.md |
| T04-032 | ✅ TỒN TẠI | transcript-04-clean.md |

**Kết quả:** 5 tồn tại · 0 không tìm thấy

## 5. Ví dụ evidence nguyên văn

Các mã đoạn tiêu biểu được dùng trong spec §1 (chỉ ghi mã, không sao chép data pack):

- `[T04-015]` — Quan hệ AI/ML/DL/GenAI: bức tranh tổng quan các vòng tròn lồng nhau
- `[T04-025]` — Giới hạn symbolic AI: bùng nổ tổ hợp, con người không liệt kê hết luật
- `[T04-029]` — Giới hạn expert system: tri thức nhập bằng tay, nợ kỹ thuật khi cập nhật luật
- `[T04-030]` — Deep learning: mạng neuron nhiều tầng tự học đặc trưng từ dữ liệu
- `[T04-032]` — Khác biệt ML vs DL: ML phải viết đặc trưng, DL tự rút ra từ dữ liệu

Tất cả mã trên đã được kiểm tra tồn tại trong `transcript-04-clean.md`.

## 6. Kết luận

- Toàn bộ mã trích dẫn trong `golden-set.csv` và `spec.md` đều **tồn tại** trong transcript thật.
- Evidence mining xác nhận transcript có cả phần đệm (hoạt động lớp) và phần mơ hồ ([không nghe rõ]) — khớp với mô tả trong spec.
- Kết quả mining này hỗ trợ claim trong spec §1 rằng dữ liệu transcript đủ chất lượng để trích xuất trọng điểm, đồng thời cần xử lý cẩn thận các đoạn không rõ ràng.
