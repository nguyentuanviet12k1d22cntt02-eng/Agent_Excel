# apps/desktop — Gia sư trên Windows (Python + PyQt6)

Bộ giám sát Excel (COM, Win32 API, UI Automation), Teaching Agent chạy theo kịch bản đã duyệt, cửa sổ gia sư, mascot, overlay hướng dẫn. Desktop **không gọi AI**.

- **Package:** `tutor_desktop` (trong `src/`). Cấu trúc và trách nhiệm từng thư mục: [cấu trúc thư mục](../../docs/quy-uoc/cau-truc-thu-muc.md#appsdesktopsrctutor_desktop)
- **Được xây dựng ở:** GĐ7 (T7.1 – T7.10). Đóng gói `.exe` trong `packaging/` (T7.10)
- **Cài môi trường:** dùng chung `.venv` ở gốc repo, xem [README gốc](../../README.md#bắt-đầu)

## Chế độ chạy thử cho giảng viên (đã có)

Thử kịch bản AI sinh ngay trên Excel trước khi duyệt:

```powershell
# Backend phải đang chạy (.venv\Scripts\python -m tutor_backend serve)
.venv\Scripts\python -m tutor_desktop                  # đăng nhập, chọn bài và bản kịch bản
.venv\Scripts\python -m tutor_desktop --version <id>   # chạy thẳng một bản (trình sửa trên Web có nút chép lệnh)
```

1. Đăng nhập bằng tài khoản giảng viên (nhớ địa chỉ máy chủ và email).
2. App tải **bản sao mới** của file đề gốc, mở trong Excel đang chạy (chưa có Excel thì mở Excel), hiện cửa sổ gia sư bên phải màn hình.
3. Làm bài như học viên. Cửa sổ gia sư:
   - hiện thẻ yêu cầu của bước, **tự chuyển bước** khi làm đúng;
   - hiện **phản hồi theo mã lỗi** khi làm sai (sau khi đã sửa trang tính);
   - **nhắc ngay** khi sửa dữ liệu gốc hoặc gõ đè công thức có sẵn (điều kiện toàn bài);
   - **Xin gợi ý** từng cấp; ở cấp 3 khoanh vùng ô (cam) và nút Ribbon trên Excel, nút chưa hiện thì chỉ vào thẻ chứa nút;
   - bước có **chuỗi thao tác** (kịch bản theo quy trình): dẫn từng chỗ một — khoanh tiêu đề cột cần chọn, chọn
     đúng rồi mới chỉ nút Format, mở menu rồi mới chỉ mục Hide & Unhide, Unhide Columns…; bỏ chọn hay đóng menu
     thì quay lại chỗ đó; bấm nhầm lệnh (ẩn nhầm cột…) thì báo chỗ sai, nhắc Ctrl+Z; hoàn tác về trước một
     bước đã qua thì lùi về bước đó;
   - đánh dấu "Khoanh vùng của bước" để luôn thấy vùng học viên làm (xanh) và dữ liệu nguồn (xanh lá, nét đứt);
   - "Xem chi tiết điều kiện kiểm" để xem điều kiện nào chưa đạt, mã lỗi, ô nào.

App chỉ đọc Excel (không ghi vào file, không đóng Excel). Định dạng ô không phát sự kiện nên app đọc lại mỗi 1,5 giây khi Excel không bận; khung chỉ dẫn cập nhật mỗi 0,3 giây và chỉ hiện khi Excel (hoặc cửa sổ gia sư) ở trước.

**Chưa có (làm tiếp ở GĐ7):** chế độ học viên tự nhận bài theo mã nhúng trong file (T7.4), gợi ý tự đưa theo tín hiệu và luật thích ứng (T7.5), mascot (T7.8), nhật ký và đồng bộ tiến độ (T7.9), đóng gói `.exe` (T7.10).

## Bố cục

| Thư mục | Đã có |
|---|---|
| `api_client/client.py` | Đăng nhập, tự làm mới token, gói chạy thử, tải file đề gốc |
| `monitor/excel_link.py` | Mở file trong Excel, đọc snapshot (`excel_core.readers.com_reader`), thử lại khi Excel bận, tọa độ ô (COM hoặc UIA tùy DPI) và nút Ribbon (UIA, `idMso`) |
| `monitor/watcher.py` | Luồng giám sát (QThread, COM STA): sự kiện SheetChange/in, đọc định kỳ, tính khung chỉ dẫn; giao diện nhận qua signal |
| `agent/preview_session.py` | Phiên chạy thử: bước hiện tại, chấm bằng `excel_core.checks`, tự chuyển bước, gợi ý từng cấp, phản hồi theo mã lỗi, báo lệch quy trình và lùi bước |
| `agent/guide.py` | Chuỗi thao tác của bước: vùng chọn phủ đúng cột/dòng chưa, đang dẫn ở chỗ nào |
| `ui/` | Đăng nhập, chọn kịch bản, cửa sổ gia sư, overlay mỗi màn hình một cửa sổ |

## Test

```powershell
.venv\Scripts\pytest apps/desktop                                  # không cần Excel (cửa sổ chạy offscreen)
$env:EXCEL_TESTS = "1"; .venv\Scripts\pytest apps/desktop -m excel  # cần Excel: phiên riêng, ẩn, tự đóng
```
