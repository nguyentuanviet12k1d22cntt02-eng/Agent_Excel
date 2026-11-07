# T2.5 — Overlay PyQt6

**Mục tiêu:** lớp phủ trong suốt, luôn trên cùng, chuột bấm xuyên qua; vẽ khung đúng quanh vùng ô và nút Ribbon; bám theo khi zoom, cuộn, di chuyển cửa sổ; đúng ở DPI cao.

**Chạy:** `.venv\Scripts\python spikes\t2-5-overlay\overlay.py`
Cần `uiautomation==2.0.29`. Một cửa sổ Excel riêng (dữ liệu tự tạo) hiện ~15 giây; script tự chụp vùng cửa sổ Excel vào `anh/`.

## Cách tính tọa độ

| Vật cần chỉ | Nguồn tọa độ | Ghi chú |
|---|---|---|
| Vùng ô | COM `ActivePane.PointsToScreenPixelsX/Y(Range.Left/Top/…)` | Pixel vật lý, đã tính zoom và cuộn. Khớp UIA ≤ 1 px (T2.4) |
| Nút Ribbon | UIA `BoundingRectangle`, tìm theo AutomationId (`CommaStyle`) | Chỉ có khi tab chứa nút đang được chọn |
| Vẽ bằng Qt | Pixel vật lý ÷ `devicePixelRatio` | Máy này 150% → chia 1,5 |

## Kết quả (máy của Việt, màn hình **150%**, 07/11/2026)

| Trường hợp | Ảnh | Khung vùng C4:D8 | Khung nút Comma Style |
|---|---|---|---|
| Ban đầu | [1-ban-dau.png](anh/1-ban-dau.png) | ✅ ôm sát | ✅ trùng nút |
| Zoom 150% | [2-zoom-150.png](anh/2-zoom-150.png) | ✅ phóng to theo | ✅ |
| Cuộn trang (dòng 3, cột B lên đầu) | [3-cuon-trang.png](anh/3-cuon-trang.png) | ✅ dịch theo | ✅ |
| Di chuyển cửa sổ Excel | [4-di-chuyen-cua-so.png](anh/4-di-chuyen-cua-so.png) | ✅ đi theo | ✅ đi theo |

**Thuộc tính cửa sổ overlay** (đọc bằng `GetWindowLong`): `WS_EX_TRANSPARENT` (chuột xuyên qua) ✅, `WS_EX_LAYERED` ✅, `WS_EX_TOPMOST` ✅, `WS_EX_TOOLWINDOW` (không hiện trên taskbar) ✅. Qt tạo đủ các cờ này từ `WindowTransparentForInput | WindowStaysOnTopHint | Tool`.

## Bài học

1. **Overlay không được giành focus.** Dùng `WA_ShowWithoutActivating`; Excel phải luôn là cửa sổ nhận bàn phím của học viên.
2. **Windows chặn tiến trình nền tự đưa cửa sổ lên trước.** Lần chạy đầu, Excel nằm sau VS Code nên khung vẽ đè lên cửa sổ khác. Spike tạm đặt Excel `HWND_TOPMOST` để chụp ảnh. **Desktop thật thì ngược lại:** chỉ hiện overlay khi Excel đang là cửa sổ trước (kiểm tra `GetForegroundWindow`), ẩn overlay khi học viên chuyển sang ứng dụng khác.
3. **Nhãn che dữ liệu:** nhãn "Vùng C4:D8" đè lên tiêu đề cột. UI thật nên đặt nhãn ngoài vùng bảng hoặc dùng mũi tên từ cửa sổ gia sư.
4. **Phải tính lại tọa độ khi:** zoom, cuộn, di chuyển/đổi kích thước cửa sổ, đổi sheet. Excel không có sự kiện cho zoom/cuộn, nên Desktop kiểm tra định kỳ (khoảng 200 ms) **chỉ khi overlay đang hiện**.
5. **Bảo mật khi chụp màn hình:** lần chạy đầu ảnh đã chụp trúng nội dung màn hình khác (đã xóa). Chỉ chụp khi chắc chắn vùng chụp là cửa sổ Excel đang ở trên cùng.

## Chưa thử

- Màn hình 100% và 125%, **nhiều màn hình có tỉ lệ khác nhau**. Công thức chia `devicePixelRatio` của màn hình chính sẽ sai nếu Excel nằm ở màn hình phụ khác tỉ lệ, cần lấy DPI theo màn hình chứa cửa sổ (`GetDpiForWindow`).
- Bấm chuột thật xuyên qua overlay (mới kiểm tra cờ cửa sổ, chưa bấm thử).
