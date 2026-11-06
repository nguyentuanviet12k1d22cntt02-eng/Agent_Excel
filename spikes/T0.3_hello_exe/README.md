# T0.3 — Chốt phiên bản Python và thử đóng gói `.exe`

## Mục tiêu

1. Chọn một phiên bản Python chung cho cả nhóm, cài được mọi thư viện dự kiến.
2. Chứng minh PyQt6 + pywin32 + Excel COM chạy được sau khi PyInstaller đóng gói thành `.exe`.

## Cách chạy

Từ gốc repo, sau khi đã tạo `desktop\.venv` (xem [desktop/README.md](../../desktop/README.md)):

```powershell
powershell -ExecutionPolicy Bypass -File spikes\T0.3_hello_exe\build.ps1
```

Script sẽ build `dist\HelloGiaSu.exe`, chạy `HelloGiaSu.exe --selftest` rồi in kết quả. **Mã thoát 0 là đạt.** Muốn xem cửa sổ thì nháy đúp vào file `.exe`.

## Kết quả trên máy của Việt (07/11/2026)

**Cài thử thư viện trên Python 3.14.0:** 23/23 gói cài được, gồm PyQt6, pywin32, comtypes, uiautomation, pyinstaller, fastapi, uvicorn, sqlalchemy, alembic, pydantic-settings, python-multipart, openpyxl, pymupdf, python-docx, psycopg, pgvector, jsonschema, httpx, anthropic, openai, chromadb, pytest, ruff.

**Đóng gói và tự kiểm tra:**

| Hạng mục | Kết quả |
|---|---|
| PyInstaller 6.22.3, `--onefile --windowed` | Build thành công trong khoảng 70 giây |
| Kích thước `HelloGiaSu.exe` | 35,6 MB |
| Chạy ở dạng đóng gói (`frozen`) | Có |
| Python / PyQt / Qt | 3.14.0 / 6.12.0 / 6.12.0 |
| pywin32 | OK |
| Excel COM (mở phiên Excel riêng, đọc phiên bản) | OK: Excel 16.0, build 20326 |
| Ngôn ngữ giao diện Office | 1033 (tiếng Anh). Thông tin này cần cho T2.4 |

## Kết luận

- **Chốt Python 3.14** (ghi trong `.python-version`).
- Đóng gói PyQt6 + pywin32 bằng PyInstaller không cần cấu hình thêm.
- `--onefile` cho file 35,6 MB, khởi động chậm hơn vì phải giải nén. Khi làm bộ cài thật (T7.10) nên thử thêm `--onedir` để so thời gian khởi động.

## Việc còn lại để đóng T0.3

Ba thành viên còn lại chạy `build.ps1` trên máy mình, rồi ghi kết quả vào bảng:

| Thành viên | Windows | Excel (phiên bản, ngôn ngữ) | Mã thoát | Ghi chú |
|---|---|---|---|---|
| Việt | 10 Pro 19045 | 16.0 build 20326, tiếng Anh (1033) | 0 | |
| Hoài | | | | |
| Linh | | | | |
| Hòa | | | | |
