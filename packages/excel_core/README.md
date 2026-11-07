# packages/excel_core — Lõi Excel dùng chung

Thư viện Python dùng chung cho Backend và Desktop.

| Module | Việc | Task |
|---|---|---|
| `snapshot/` | Mô hình dữ liệu chung: giá trị, công thức, định dạng, trang in, bộ lọc, biểu đồ | T3.3, T4.1 |
| `readers/` | Đọc workbook thành snapshot: `openpyxl_reader.py` (file `.xlsx`, Backend), `com_reader.py` (Excel đang chạy, Desktop) | T4.2, T7.2 |
| `diff/` | So sánh file đề với file kết quả mẫu | T4.3 |
| `checks/` | Kiểm tra điều kiện kiểm chứng, mỗi loại một file | T4.4 |
| `script/` | Đọc và kiểm tra kịch bản JSON theo lược đồ trong `schemas/` | T4.5 |

**Quy tắc:** không import gì từ `apps/`; không import `win32com` ở mức module (xem [cấu trúc thư mục](../../docs/quy-uoc/cau-truc-thu-muc.md#3-quy-tắc-phụ-thuộc-giữa-các-phần)). Mọi module có logic phải có test.
