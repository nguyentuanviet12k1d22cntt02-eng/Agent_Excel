# T2.5 — Overlay PyQt6

**Mục tiêu:** lớp phủ trong suốt, luôn trên cùng, chuột bấm xuyên qua; vẽ khung đúng quanh vùng ô và nút Ribbon; bám theo khi zoom, cuộn, di chuyển cửa sổ; đúng ở mọi tỉ lệ màn hình, kể cả **nhiều màn hình khác tỉ lệ**.

**Chạy:**

```powershell
.venv\Scripts\python spikes\t2-5-overlay\overlay.py                    # tỉ lệ thật của các màn hình
.venv\Scripts\python spikes\t2-5-overlay\overlay.py --qt-scale 0.8333   # mô phỏng tỉ lệ khác (150% x 0,8333 = 125%)
```

Cần `uiautomation==2.0.29`. Một cửa sổ Excel riêng (dữ liệu tự tạo) hiện ~20 giây, có lúc chuyển sang màn hình phụ (nếu máy có màn hình phụ khác tỉ lệ). Script tự chụp vùng cửa sổ Excel vào `anh/`.

## Cách tính tọa độ

| Vật cần chỉ | Nguồn tọa độ | Ghi chú |
|---|---|---|
| Vùng ô, Excel ở màn hình có **DPI = DPI hệ thống** | COM `ActivePane.PointsToScreenPixelsX/Y(Range.Left/Top/…)` | Pixel vật lý, đã tính zoom và cuộn. Khớp UIA ≤ 1 px |
| Vùng ô, Excel ở màn hình **khác DPI hệ thống** | UIA `DataItem.BoundingRectangle` của ô đầu và ô cuối phần vùng đang hiện (`Intersect(vùng, VisibleRange)`) | **COM sai ở trường hợp này**, xem dưới |
| Nút Ribbon | UIA `BoundingRectangle`, tìm theo AutomationId (`CommaStyle`) | Chỉ có khi tab chứa nút đang được chọn |
| Vẽ bằng Qt | `(vật lý − gốc vật lý của màn hình chứa điểm) ÷ devicePixelRatio của màn hình đó` | **Mỗi màn hình một overlay**, mỗi màn hình một tỉ lệ |

DPI hệ thống = DPI của màn hình chính lúc đăng nhập Windows (`GetDpiForSystem`). DPI cửa sổ Excel: `GetDpiForWindow`.

## Kết quả (máy của Việt, 07/11/2026)

Máy có 3 màn hình: **DISPLAY1** chính 1920×1080 **150%**; **DISPLAY2** bên trái 1920×1080 **100%**; **DISPLAY3** bên phải 1366×768 **100%**.

| # | Trường hợp | Màn hình | Ảnh | Khung vùng C4:D8 | Khung nút Comma Style | Chuột tại giữa khung rơi vào |
|---|---|---|---|---|---|---|
| 1 | Ban đầu | 150% | [1-ban-dau.png](anh/1-ban-dau.png) | ✅ lệch UIA 1 px | ✅ | Excel (`EXCEL7`, `NetUIHWND`) |
| 2 | Zoom 150% | 150% | [2-zoom-150.png](anh/2-zoom-150.png) | ✅ 1 px | ✅ | Excel |
| 3 | Cuộn trang | 150% | [3-cuon-trang.png](anh/3-cuon-trang.png) | ✅ 1 px | ✅ | Excel |
| 4 | Di chuyển cửa sổ | 150% | [4-di-chuyen-cua-so.png](anh/4-di-chuyen-cua-so.png) | ✅ 1 px | ✅ | Excel |
| 5 | **Kéo Excel sang màn hình phụ** | **100%** | [5-man-hinh-phu.png](anh/5-man-hinh-phu.png) | ✅ (COM thô lệch **852 px**) | ✅ | Excel |
| 6 | Màn hình phụ + zoom 130% + cuộn | **100%** | [6-man-hinh-phu-zoom-cuon.png](anh/6-man-hinh-phu-zoom-cuon.png) | ✅ (COM thô lệch 828 px) | ✅ | Excel |
| 7 | Mô phỏng **125%** (`--qt-scale 0.8333`), zoom 150% | 150% × 0,8333 | [qt0.8333-2-zoom-150.png](anh/qt0.8333-2-zoom-150.png) | ✅ | ✅ | Excel |
| 8 | Mô phỏng tỉ lệ 0,83 trên màn hình phụ | 100% × 0,8333 | [qt0.8333-5-man-hinh-phu.png](anh/qt0.8333-5-man-hinh-phu.png) | ✅ | ✅ | Excel |

**Thuộc tính cửa sổ overlay** (`GetWindowLong`): `WS_EX_TRANSPARENT` ✅, `WS_EX_LAYERED` ✅, `WS_EX_TOPMOST` ✅, `WS_EX_TOOLWINDOW` ✅. Qt tạo đủ các cờ này từ `WindowTransparentForInput | WindowStaysOnTopHint | Tool`.

**Chuột bấm xuyên qua:** `WindowFromPoint` tại giữa mỗi khung (đúng phép thử Windows dùng để quyết định cửa sổ nào nhận cú bấm) luôn trả về cửa sổ của Excel, không bao giờ là overlay → bấm vào ô hoặc nút đang được khoanh vẫn tới Excel.

### Phát hiện: COM `PointsToScreenPixels` sai ở màn hình khác DPI hệ thống

Đặt Excel lên màn hình 100% trong khi DPI hệ thống là 150% (144):

| | Ô C4 (vật lý) | Ghi chú |
|---|---|---|
| UIA (đúng, khớp ảnh) | (−1705, 417, −1641, 436) | ô rộng 64 px, cao 19 px |
| COM `PointsToScreenPixels` | (−2557, 639, −2461, 654) | rộng 96 px (×1,5) nhưng cao 15 px — **sai không theo một tỉ lệ** |

Đã thử "neo" vào ô góc trên trái (UIA) rồi quy đổi phần còn lại theo tỉ lệ DPI: vẫn lệch 9–11 px theo chiều dọc. **Không sửa được bằng phép nhân → dùng UIA** cho trường hợp này. UIA chỉ có các ô đang hiện, nên khung được cắt theo phần vùng đang hiện; vùng nằm ngoài màn hình thì không vẽ, cũng là hợp lý.

### Về tỉ lệ 125%

Máy không có màn hình đặt 125%. Lần chạy `--qt-scale 0.8333` cho thấy **phép quy đổi của Qt đúng với tỉ lệ bất kỳ** (1,25 và 0,83). Phần tọa độ phía Excel đã đúng ở cả 150% và 100% (kể cả lệch DPI hệ thống). Rủi ro còn lại ở 125% thật là thấp; máy trung tâm sẽ được chạy lại khi khảo sát (T9.3).

## Bài học

1. **Overlay không được giành focus.** Dùng `WA_ShowWithoutActivating`; Excel phải luôn là cửa sổ nhận bàn phím của học viên.
2. **Mỗi màn hình một overlay.** Một cửa sổ Qt trải qua nhiều màn hình khác tỉ lệ sẽ vẽ sai. Overlay đặt `setScreen()` + `setGeometry(screen.geometry())`.
3. **Ghép màn hình Qt với Windows theo kích thước vật lý và tỉ lệ, không theo tên:** Qt có lúc đặt tên màn hình theo model (`HP P19v G4`) thay vì `\\.\DISPLAY3`.
4. **Chọn cách lấy tọa độ ô theo DPI:** `GetDpiForWindow(Excel) == GetDpiForSystem()` → COM (nhanh, có cả ô ngoài màn hình); khác → UIA.
5. **Windows chặn tiến trình nền tự đưa cửa sổ lên trước.** Spike tạm đặt Excel `HWND_TOPMOST` để chụp ảnh. **Desktop thật:** chỉ hiện overlay khi Excel là cửa sổ trước (`GetForegroundWindow`), ẩn khi học viên chuyển ứng dụng.
6. **Khi kéo cửa sổ sang màn hình khác tỉ lệ, Windows tự co giãn kích thước cửa sổ** → phải tính lại tọa độ. Excel không có sự kiện cho zoom/cuộn/di chuyển, nên Desktop kiểm tra định kỳ (~200 ms) **chỉ khi overlay đang hiện**.
7. **Cửa sổ Excel hẹp thì Ribbon gộp nhóm**, nút Comma Style biến mất khỏi cây UIA (lần chạy đầu với cửa sổ 1050 px không tìm thấy nút). Xem T2.4.
8. **Nhãn che dữ liệu:** nhãn "Vùng C4:D8" đè lên tiêu đề cột. UI thật nên đặt nhãn ngoài vùng bảng hoặc dùng mũi tên từ cửa sổ gia sư.
9. **Bảo mật khi chụp màn hình:** chỉ chụp vùng cửa sổ Excel khi nó đang ở trên cùng.
