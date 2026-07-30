# Catch-up Assistant — VLearn

Prototype giúp học viên mở một buổi đã bỏ lỡ và nhận 3–5 điểm cần đọc trước, biết điểm nào liên quan quiz, bấm về đúng đoạn transcript gốc, và hỏi thêm trong phạm vi buổi học.

## Chạy dự án

Yêu cầu Docker Desktop và Python 3.11+. Dữ liệu ứng dụng được lưu thật trong
MongoDB chạy bằng Docker; cổng `27020` chỉ bind vào `127.0.0.1` để không lộ
database ra mạng ngoài.

```powershell
docker compose up -d mongodb
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts\seed_mongodb.py
.\.venv\Scripts\streamlit.exe run codebase\streamlit_app.py
```

Lệnh seed dùng **upsert**, có thể chạy lại an toàn. App đọc trực tiếp các collection
`catchup_assistant.transcripts`, `catchup_assistant.quiz_bank` và
`catchup_assistant.analyses`; badge màu xanh `MongoDB thật · 6 buổi` xác nhận nguồn
dữ liệu đang hoạt động. MongoDB là bắt buộc: nếu mất kết nối, app dừng với hướng dẫn
khởi động database và tuyệt đối không tráo sang dữ liệu fallback.

Có thể đổi kết nối qua biến môi trường (xem `.env.example`):

```powershell
$env:MONGO_URI="mongodb://127.0.0.1:27020"
$env:MONGO_DATABASE="catchup_assistant"
```

Mở `http://localhost:8501`. Trong sidebar, tải lên file `.txt` tại **Nạp key hàng loạt**. Mỗi dòng chứa đúng một Gemini API key; dòng trống và comment bắt đầu bằng `#` được bỏ qua:

```text
# gemini-keys.txt
key-1
key-2
key-3
```

Ứng dụng giới hạn đầu vào 256 KB và không ghi key vào repo/log. Có thể dán trực tiếp hàng loạt vào vùng nhập nhiều dòng bên dưới file uploader; **mỗi dòng là một API key**. Bật **Che key trên màn hình** khi trình chiếu. Pool được mã hóa cục bộ bằng Windows DPAPI trong thư mục `.runtime/` đã gitignore, chỉ tài khoản Windows hiện tại giải mã được; vì vậy tải lại trang hoặc khởi động lại Streamlit không làm mất key. Có nút **Xóa key đã lưu** để xóa ngay bản mã hóa.

Pool sử dụng round-robin sau mỗi request. Việc dán/nạp key **không tự gọi AI**; bấm **Phân tích bằng Gemini** khi muốn chạy. Trong lúc chạy, giao diện hiển thị slot và tiến độ thử key. Nếu một key gặp lỗi quota token/rate-limit (`429`/`RESOURCE_EXHAUSTED`), key lỗi hoặc provider `5xx`, hệ thống tự chạy lại toàn bộ request bằng slot tiếp theo; mỗi request có timeout để không chờ vô hạn. Lời gọi Gemini là non-streaming nên output dở dang không được đưa ra UI; người dùng chỉ thấy kết quả hoàn chỉnh. Lỗi request không hợp lệ (`400`) dừng ngay để không tiêu tốn cả pool. Giao diện và log chỉ hiển thị số slot/key đã che, không hiển thị key đầy đủ.

Kết quả Gemini chỉ được lưu vào `analyses` sau khi có 3–5 trọng điểm và mọi citation
đều tồn tại trong đúng transcript. Bản ghi gắn fingerprint SHA-256 của transcript;
khi nguồn thay đổi, phân tích cũ không được tái sử dụng. Có thể tạo/làm mới phân tích
thật bằng giao diện hoặc CLI:

```powershell
.\.venv\Scripts\python.exe scripts\generate_analysis.py --session transcript-04-clean.md
```

Bạn cũng có thể cấu hình key bằng biến môi trường:

```powershell
$env:GEMINI_API_KEY="..."
.\.venv\Scripts\streamlit.exe run codebase\streamlit_app.py
```

Hoặc cấu hình nhiều key bằng biến môi trường:

```powershell
$env:GEMINI_API_KEYS="key-1,key-2,key-3"
.\.venv\Scripts\streamlit.exe run codebase\streamlit_app.py
```

Không commit key hoặc `.streamlit/secrets.toml`. Trace AI thật được ghi cục bộ tại `codebase/logs/ai-trace.jsonl` và đã gitignore; trước khi nộp chỉ đưa trace tối thiểu không chứa transcript dài hay secret.

Nếu chưa có kết quả Gemini, app chỉ hiển thị bản **trích xuất trực tiếp từ transcript
MongoDB thật** và ghi rõ “chưa phân tích AI”; không có summary hard-code. Data pack
không cung cấp ngân hàng quiz thật nên collection quiz hiện để trống và UI không tự
gắn nhãn quiz. Chỉ nhập quiz khi có nguồn được phép sử dụng.

## Kiểm thử

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## Artifact nộp bài

| Artifact | Vị trí |
|---|---|
| AI Spec | `spec.md` |
| Prototype | `codebase/` |
| Golden set | `eval/golden-set.csv` |
| Feedback log | `validation/feedback-log.md` |
| Reflection | `reflection/NguyenDucAnh.md` |

## Thành viên & phân công

| Thành viên | Mã học viên | Vai trò & phần phụ trách |
|---|---|---|
| **Nguyễn Đức Anh (Trưởng nhóm)** | **2A202601063** | Chịu trách nhiệm chính toàn dự án: điều phối và chốt quyết định sản phẩm; viết AI Spec; thiết kế kiến trúc và prompt; lập trình core AI, guardrail, backend và giao diện Streamlit; tích hợp Gemini; xây golden set và chạy eval; tổng hợp repo, slide và dẫn demo |
| **Phan Văn Hiếu** | **2A202601227** | Hỗ trợ mining transcript/chatlog, thu thập evidence và đối chiếu mã trích dẫn |
| **Nguyễn Huy Tỏa** | **2A202601697** | Hỗ trợ rà soát golden set, chấm kết quả evaluation và ghi nhận case lỗi |
| **Tạ Long Khánh** | **2A202601197** | Hỗ trợ kiểm thử luồng giao diện, góp ý UI/UX và kiểm tra responsive |
| **Vũ Đăng Huy** | **2A202601761** | Hỗ trợ user validation, ghi feedback và chuẩn bị nội dung thuyết trình |

> Trưởng nhóm Nguyễn Đức Anh phụ trách phần lớn khối lượng và toàn bộ hạng mục cốt lõi; các thành viên còn lại hỗ trợ theo đầu việc được giao. Cả 5 thành viên cùng review sản phẩm và tham gia phần trình bày/Q&A.

Các mục cần validation từ người học thật vẫn được đánh dấu `TODO-NGƯỜI-THẬT`;
runtime hiện dùng transcript MongoDB và đã có lời gọi Gemini thật, không có output giả.

## Tài liệu đề bài gốc

Phần dưới đây được giữ nguyên để đối chiếu yêu cầu.

# Mini Hackathon AI — Batch 03

**SPEC → Prototype → Demo.** Đây không phải cuộc thi code — đây là cuộc thi **tư duy sản phẩm AI**.

- Thời lượng: **1,5 ngày** (một ngày build + một buổi demo)
- Nhóm: **4-5 người** · zone tối đa 5 nhóm · thi theo lớp

## Bắt đầu từ đâu?

1. Đọc **`01-de-bai.md`** để chọn hướng và hiểu tiêu chí.
2. Mở **`02-guide.md`** — hướng dẫn từng giai đoạn, đứng ở đâu đọc mục đó.
3. Viết spec theo **`03-template-ai-spec.md`** — deliverable trung tâm của cả sự kiện.
4. Đọc **`04-rubric.md`** ngay từ đầu — biết trước bài được chấm theo tiêu chí nào.

| File / thư mục | Nội dung |
|---|---|
| `01-de-bai.md` | Đề bài 3 hướng · 5 tiêu chí nghiệm thu · ràng buộc chung |
| `02-guide.md` | Hướng dẫn 5 giai đoạn: khám phá → spec → build → đo & validate → demo |
| `03-template-ai-spec.md` | Template AI Spec (nộp 23:59 ngày 1) |
| `04-rubric.md` | Rubric 100 điểm (25 nộp checkpoint + 75 chấm bài) + checklist xác minh 6 mốc |
| `data/` | Dữ liệu thật đã ẩn danh: chatlog VLearn tutor + 6 transcript bài giảng bản sạch — dùng để tìm bằng chứng và xây golden set |
| `tham-khao/` | JTBD Playbook (PDF) + worksheet JTBD đầy đủ — đọc khi muốn đào sâu |

## Lịch — 6 mốc

| Mốc | Khoá 3 | Khoá 4 |
|---|---|---|
| Khai mạc + phát đề | 09:00 ngày 1 | 14:00 ngày 1 |
| CP1 · Chốt Canvas | 10:00 ngày 1 | 15:00 ngày 1 |
| CP2 · Show được thứ bấm được | 12:00 ngày 1 | 17:00 ngày 1 |
| CP3 · AI chạy thật + đo lượt đầu | 16:00 ngày 1 | 10:30 ngày 2 |
| CP4 · Chốt tiến độ — spec nộp hạn cứng **23:59 ngày 1** | 17:30 ngày 1 | 12:00 ngày 2 |
| CP5 · Xác minh + validation + dry run | 09:00 ngày 2 | 14:00 ngày 2 |
| CP6 · Demo | 10:00 ngày 2 | 15:00 ngày 2 |

Mỗi mốc cần show gì và được xác minh thế nào: xem bảng trong `04-rubric.md`.

## Nộp bài

Một repo nhóm, cấu trúc như sau. Spec chốt lúc 23:59 ngày 1; bản hoàn chỉnh trước CP6.

```
repo/
├── README.md          ← thành viên (mã HV + tên) + phân công có tên từng phần
├── spec.md            ← AI Spec theo 03-template-ai-spec.md
├── demo-slides.pdf    ← slide 6 trang theo 02-guide.md §5.1
├── codebase/          ← prototype (ghi rõ phần nào mock)
├── eval/              ← golden set + bảng kết quả các lượt chạy
├── validation/        ← feedback log từ vòng user test
└── reflection/        ← mỗi người 1 file
```

## Chấm điểm

Tổng **100 điểm = 25 điểm nộp checkpoint + 75 điểm chấm bài nộp**. Chi tiết từng ý điểm: `04-rubric.md`.

**25 điểm nộp — mỗi checkpoint 5 điểm (CP1-CP5):** nộp đúng hạn → 5 điểm · nộp muộn → 0 điểm cho mốc đó. Mỗi thành viên nộp riêng, cả nhóm dùng chung một link repo.

**75 điểm chấm — trên artifact trong repo, mỗi con điểm trỏ về một file:**

| Khối | Điểm | Chấm trên file nào |
|---|---|---|
| R1 · Bằng chứng & impact | 15 | `spec.md` §1-§2 + log khảo sát/mining |
| R2 · Lát cắt & thiết kế | 15 | `spec.md` §4 |
| R3 · Chỗ khó & kịch bản rủi ro | 11 | `spec.md` §5-§6 |
| R4 · Kiểm thử | 15 | `spec.md` §7 + `eval/` |
| R5 · Prototype chạy được | 8 | `codebase/` + demo |
| R6 · Validation với user | 8 | `validation/` |
| R7 · Quy trình & repo | 3 | cấu trúc repo |

Ba điều nên biết trước khi làm:

- Điểm dựa trên **chuỗi quyết định và bằng chứng**, không dựa trên mức độ hoành tráng của sản phẩm.
- Kết quả đo **ghi nhận trung thực** — kể cả khi không đạt mục tiêu nhóm tự đặt — vẫn được tính đủ điểm. Số liệu bị chỉnh sửa hoặc che giấu sẽ không được tính.
- Reflection cá nhân chấm riêng theo rubric của khoá. Điểm vòng demo, chấm chéo trong zone và thưởng thêm (nếu có) theo thể lệ công bố lúc khai mạc.

## Luật chung

1. Prototype có 3 mức **Sketch / Mock / Working** — mức nào cũng bắt buộc **≥1 lời gọi AI chạy thật**.
2. **Vibe-coding rule:** dùng AI để build thoải mái, nhưng không giải thích được phần có tên mình thì phần đó 0 điểm (kiểm tra tại CP5).
3. **Quality bar** chốt tại spec.md 23:59 ngày 1 và giữ nguyên sau đó.
4. Chỉ dùng dữ liệu trong `data/` hoặc dữ liệu giả tự sinh — không dùng dữ liệu thật của người thật. Không commit API key.
5. Tuân thủ **quy định bảo mật dữ liệu** bên dưới — đây là điều kiện để được cấp data.

## Bảo mật dữ liệu được cung cấp

Dữ liệu trong `data/` là dữ liệu thật của khoá học (đã ẩn danh), cấp riêng cho hackathon này. Khi nhận data, nhóm cam kết:

1. **Chỉ dùng trong phạm vi hackathon** — cho việc tìm bằng chứng, xây golden set và build prototype. Không dùng cho mục đích khác.
2. **Không chia sẻ ra ngoài khoá học** — không đăng lên mạng xã hội, không gửi cho người ngoài, không đưa vào bất kỳ dataset hay repo công khai nào.
3. **Không commit data pack vào repo nộp bài** — repo nhóm chỉ chứa trích dẫn ngắn để minh hoạ (vài dòng); golden set trích từ data ghi rõ mã đoạn/mã hội thoại thay vì dán nguyên văn dài.
4. **Cẩn trọng khi đưa data vào công cụ ngoài** — chỉ đưa phần tối thiểu cần cho việc đang làm; lưu ý API/công cụ free tier có thể dùng dữ liệu để huấn luyện (xem `02-guide.md` §3.4).
5. **Không cố suy ngược danh tính** từ dữ liệu đã ẩn danh ([học viên], mã U/C/T/M).
6. Sau sự kiện, **xoá các bản sao data pack** khỏi máy cá nhân và các công cụ đã upload nếu ban tổ chức yêu cầu.

Vi phạm được xử lý theo quy định của khoá và có thể ảnh hưởng trực tiếp đến điểm của nhóm.
