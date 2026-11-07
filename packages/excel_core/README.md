# packages/excel_core — Lõi Excel dùng chung

Thư viện Python dùng chung cho Backend và Desktop.

| Module | Việc | Task |
|---|---|---|
| `address.py` | Địa chỉ A1: chữ cột, vùng liền kề, duyệt ô | T4.1 |
| `snapshot/` | Mô hình dữ liệu chung (`model.py`), yêu cầu đọc (`request.py`), phân tích mã định dạng số (`number_format.py`), chuyển JSON (`serialize.py`) | T3.3, T4.1 |
| `formula.py` | Phân tích công thức: A1 → R1C1, tên hàm, phép tính | T4.2 |
| `readers/` | Đọc workbook thành snapshot: `openpyxl_reader.py` (file `.xlsx`, Backend; màu theme ở `colors.py`, bộ lọc/trang in/biểu đồ ở `openpyxl_objects.py`), `com_reader.py` (Excel đang chạy, Desktop) | T4.2, T7.2 |
| `diff/` | So sánh file đề với file kết quả mẫu, gom ô cùng loại thay đổi thành vùng. Xem nhanh: `python -m excel_core.diff de.xlsx dap-an.xlsx` | T4.3 |
| `checks/` | Kiểm tra điều kiện kiểm chứng, mỗi loại một file | T4.4 |
| `script/` | Đọc và kiểm tra kịch bản JSON theo lược đồ trong `schemas/` | T4.5 |

**Quy tắc:** không import gì từ `apps/`; không import `win32com` ở mức module (xem [cấu trúc thư mục](../../docs/quy-uoc/cau-truc-thu-muc.md#3-quy-tắc-phụ-thuộc-giữa-các-phần)). Mọi module có logic phải có test.

## Test

```powershell
.venv\Scripts\pytest packages/excel_core
```

File Excel cho test: [tests/fixtures/](tests/fixtures/README.md) (bài nhóm tự soạn). Chạy thêm trên bài của trung tâm trong `samples/_local/` (không lên git, chỉ chạy trên máy có thư mục này):

```powershell
$env:EXCEL_CORE_LOCAL_SAMPLES = "1"
.venv\Scripts\pytest packages/excel_core
```
