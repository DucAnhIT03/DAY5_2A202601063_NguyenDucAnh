# AI SPEC — Catch-up Assistant · Nhóm Nguyễn Đức Anh

Hướng: **A — VLearn** · Loại: **Tính năng mới** · Trạng thái: **Working · MongoDB thật · Gemini thật**

> Những dữ liệu chỉ người học/nhóm mới có thể cung cấp được đánh dấu `TODO-NGƯỜI-THẬT`. Không thay bằng dữ liệu AI tạo.

## §1. User & Job

- **Job executor:** học viên đã bỏ lỡ một buổi, đang catch up trước buổi/quiz kế tiếp.
- **Workflow:** mở buổi đã lỡ → dò nội dung → chọn phần cần đọc → kiểm chứng transcript → hỏi thêm nếu còn vướng.
- **Core JTBD:** nhanh chóng xác định phần cần đọc trước trong một buổi đã lỡ để không hổng kiến thức ở quiz/buổi kế tiếp.
- **Problem statement (không AI):** học viên trở lại sau một buổi nghỉ phải đọc transcript dài mà không biết phần nào cần ưu tiên; đọc lướt dễ bỏ sót, đọc hết tốn thời gian.
- **Evidence mining kiểm lại được:** script/parser trong `codebase/core.py` đọc đủ 6 transcript, 700 đoạn. Có 55/700 đoạn (7,9%) được nhà cung cấp dữ liệu gắn `[Hoạt động lớp: …]`; 645 đoạn còn lại có nội dung. 103/700 đoạn chứa `[không nghe rõ]`, là tín hiệu không nên tự suy diễn. Cách đếm: parse mã `Txx-NNN`, đếm literal hai nhãn trên.
- **Ví dụ nguồn:** `[T04-015]` quan hệ AI/ML/DL/GenAI; `[T04-025]` giới hạn symbolic AI; `[T04-029]` nợ duy trì expert system; `[T04-030]` deep learning; `[T04-032]` khác biệt feature engineering. Repo nộp chỉ ghi mã, không sao chép data pack.
- **Giới hạn evidence:** số đếm trên chứng minh transcript có phần đệm và phần mơ hồ, chưa chứng minh pain của học viên. `TODO-NGƯỜI-THẬT`: khảo sát ≥20 người hoặc bổ sung mining chatlog đúng pain, log nguyên văn và tỷ lệ ≥50%.

## §2. Impact & quyết định chọn

| Ứng viên | Người gặp | Tần suất | Tốn mỗi lần | Khả thi 1,5 ngày | Quyết định |
|---|---:|---:|---:|---|---|
| Catch-up một buổi đã lỡ | `TODO khảo sát` | Mỗi lần nghỉ | `TODO phút/điểm` | Cao: transcript có mã | **Chọn** |
| Tóm tắt mọi buổi tự động | `TODO` | Mỗi buổi | `TODO` | Thấp, lệch non-goal | Loại |
| Sinh quiz mới | `TODO` | Mỗi buổi | `TODO` | Trung bình, cost-of-error cao | Loại |

Chọn lát cắt một buổi vì demo được end-to-end và giữ được đường kiểm chứng. Không bịa con số impact; bảng phải được nhóm điền từ khảo sát trước CP4.

## §3. Giải pháp tương tự đã nghiên cứu

- **NotebookLM:** học được cách đặt citation cạnh output; né tóm tắt chung không gắn mục tiêu quiz. Khác biệt: ưu tiên bằng quiz cũ của chính khoá.
- **Otter.ai:** học cách điều hướng từ tóm tắt về transcript; né việc tạo cảm giác bản tóm tắt thay thế nguồn.
- Việc dùng thử và quote quan sát cần người thực hiện xác nhận: `TODO-NGƯỜI-THẬT`.

## §4. Thiết kế

- **Lát cắt một câu:** Khi học viên mở một buổi mình đã bỏ lỡ, hệ thống chọn 3–5 điểm có căn cứ và đối chiếu quiz cũ để họ biết phần nào đọc trước, đồng thời luôn cho phép mở đúng đoạn transcript gốc.
- **Non-goals:** không chạy mọi buổi; không thay transcript; không kết luận học viên đã hiểu; không sinh quiz; không trả lời ngoài buổi đang mở.
- **Mức:** Working ở parser, điều hướng citation, guardrail, Gemini summary/Q&A, giải thích phần transcript được bôi đen và persistence MongoDB. Không có fallback/mock trong runtime. Khi chưa có phân tích Gemini, hệ thống chỉ trích xuất nguyên văn từ transcript thật và ghi rõ trạng thái. Data pack chưa cung cấp quiz thật nên hệ thống để trống quiz thay vì dùng câu mẫu.
- **Automation:** **Augment**. Sai trọng tâm có thể gây học sai/mất điểm; user quyết định sau khi xem trích dẫn, sửa rẻ hơn việc tin output không kiểm chứng.

| Nguyên tắc | Vị trí cụ thể |
|---|---|
| G1 — rõ khả năng | Sidebar ghi “chỉ xử lý một buổi chủ động mở” |
| G2 — rõ độ tin | badge phân biệt “Gemini thật · đã lưu MongoDB” và “trích xuất từ transcript thật” |
| G10 — thu hẹp khi nghi ngờ | Q&A từ chối khi không đủ overlap/citation |
| G11 — giải thích vì sao | mỗi nhãn quiz có `quiz_reason` |
| G8 — gạt bỏ dễ | user có thể bỏ bản đồ và mở transcript gốc |
| G9 — sửa dễ | đổi câu hỏi hoặc chọn lại buổi, không khóa flow |

## §5. Kiểu lỗi — 4 lớp chỗ khó + kịch bản

| # | Lớp | Tình huống | Hành vi mong muốn |
|---|---|---|---|
| 1 | ① Nguồn thật | Hỏi nấu phở | Từ chối, không citation |
| 2 | ① Nguồn thật | Model trả mã đoạn không tồn tại | Loại mã; không còn mã thì fail closed |
| 3 | ② Mơ hồ | “Giải thích cái đó” | Xin tên khái niệm |
| 4 | ② Mơ hồ | Transcript có `[không nghe rõ]` | Hạ confidence, dẫn nguồn |
| 5 | ③ Ngoài phạm vi | Tóm tắt cả 6 buổi | Chỉ cho chọn một buổi |
| 6 | ③ Ngoài phạm vi | Đánh giá “tôi hiểu chưa?” | Nêu rõ hệ thống không đánh giá |
| 7 | ④ Domain | Khái niệm quan trọng chỉ xuất hiện một lần | Không dùng tần suất làm tiêu chí duy nhất |
| 8 | ④ Domain | Quiz chỉ khớp từ khoá nhưng khác ý | Chỉ gắn nhãn khi có lý do khớp cụ thể |
| 9 | ④ Domain | Tóm tắt đúng nhưng citation sai | Case fail; không hiển thị như grounded |

## §6. Bốn đường đi của trải nghiệm

- **Happy:** mở Day 1 → đọc 4 điểm Gemini thật từ MongoDB → bấm citation → đọc nguồn.
- **Low-confidence:** buổi chưa có phân tích Gemini → chỉ hiện trích đoạn nguyên văn, confidence thấp và mời người dùng chủ động phân tích.
- **Failure:** hỏi ngoài bài → trả “chưa tìm thấy căn cứ”, không đoán.
- **Correction:** user hỏi lại bằng tên khái niệm hoặc đổi buổi; history giữ trong phiên.
- **Ngoài phạm vi:** UI chỉ chọn một transcript; sidebar nhắc non-goal.
- **Domain hiểm:** mọi điểm buộc có citation hợp lệ; response AI không citation bị chặn.

## §7. Kiểm thử

- **Groundedness:** pass khi mọi citation tồn tại và mọi mệnh đề chính có thể đối chiếu tại citation.
- **Quiz relevance:** pass khi nhãn quiz nêu câu hỏi/khái niệm khớp, không chỉ giống từ.
- **Abstention:** pass khi case ngoài nguồn không trả lời nội dung và không gắn citation.
- **Coverage:** pass khi output có 3–5 điểm, không chứa đoạn hoạt động lớp.
- **Quality bar chốt:** ≥85% tổng case; 100% case nguồn sự thật phải pass; 0 citation bịa.
- Golden set: `eval/golden-set.csv` (20 case, phủ đủ 4 lớp).
- Unit test hiện tại: 19/19 pass. Đã chạy Gemini thật cho `transcript-04-clean.md`, lưu 4 trọng điểm có citation vào `catchup_assistant.analyses`; luồng chat và luồng giải thích phần transcript được chọn đều đã được kiểm tra với Gemini và citation thật. `TODO-NGƯỜI-THẬT`: chấm trọn golden set và ghi kết quả quan sát thật vào `eval/run-01.csv`.

## §8. Phân công & kế hoạch

- Nguyễn Đức Anh: chủ dự án; spec, code, prompt, eval, demo. Nếu là bài nhóm, thay bằng tên thật từng người trước nộp.
- `TODO-NGƯỜI-THẬT`: điền ≥3 willing users có tên và vai; validation ≥5 người ngoài nhóm.
- Ba câu hỏi validation: “Bạn chọn đọc gì trước?” · “Bạn có kiểm chứng nguồn không?” · “Điểm nào làm bạn không tin/không hiểu?”

## §9. Changelog

| Thời điểm | Đổi gì | Vì sao |
|---|---|---|
| 2026-07-30 | Thêm guardrail bỏ stopword và ngưỡng khớp | Test câu “nấu phở” phát hiện false positive |
| 2026-07-30 | Tách nhãn demo và Gemini thật | Không tạo ấn tượng AI đã chạy khi thiếu key |
| 2026-07-31 | Bỏ summary/quiz mẫu; bắt buộc MongoDB; lưu Gemini theo fingerprint | Runtime chỉ dùng dữ liệu thật và không tái sử dụng output sai phiên bản nguồn |
