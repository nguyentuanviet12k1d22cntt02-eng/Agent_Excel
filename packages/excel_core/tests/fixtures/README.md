# File Excel dùng cho test `excel_core`

Bài **do nhóm tự soạn, số liệu giả**, được phép công khai. Bố cục (tên sheet, địa chỉ ô) theo 2 kịch bản viết tay [b09](../../../../docs/kich-ban-tay/b09-du-lieu-dang-so.md) và [b22](../../../../docs/kich-ban-tay/b22-ham-tinh-tong.md), để chạy được kịch bản mẫu trong `schemas/tutor-script/v1/examples/` trên CI. Bài gốc của trung tâm nằm trong `samples/_local/`, không lên git.

| Thư mục | Sheet làm bài | Nội dung |
|---|---|---|
| `b09/` | `2. Bang_Ke_Ban_Hang` | Bảng chính B9:I14 (cột H có công thức `=F*G`), bảng số liệu thô B17:I22. Đáp án: Số lượng Comma Style 0 số lẻ, Đơn giá và Thành tiền `#,##0.00`, Tỉ lệ `0.000`, căn phải |
| `b22/` | `Bài 01` | Tiền Bún/Thịt/Cá C9:E19. Đáp án: `=SUM(C9:E9)` sao chép xuống F9:F19, dòng TỔNG CỘNG C20:F20 |

Dựng lại (cần Windows có Excel, vì file đáp án phải được Excel tính và lưu để có giá trị của công thức):

```powershell
.venv\Scripts\python packages\excel_core\tests\fixtures\build_fixtures.py
```
