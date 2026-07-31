# Eval

- `golden-set.csv`: 20 case, gồm 8 thường, 4 nguồn sự thật, 3 mơ hồ, 3 ngoài phạm vi, 2 domain/hiếm.
- Quality bar đã chốt trong `spec.md`: ≥85% tổng, 100% lớp nguồn sự thật, 0 citation bịa.
- Chưa có API key   trong môi trường ngày 2026-07-30, vì vậy chưa tạo `run-01.csv`. Chạy AI thật rồi lưu **đầy đủ cả case fail**, không chỉnh bar sau khi thấy kết quả.

Lệnh kiểm tra phần deterministic:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

