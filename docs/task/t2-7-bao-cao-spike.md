# T2.7 — Báo cáo khả thi kỹ thuật (GĐ2)

**Ngày:** 07/11/2026 (bổ sung cùng ngày: T2.2, T2.4, T2.5 hoàn tất) · **Môi trường thử:** Windows 10 Pro, **định dạng vùng vi-VN**, Microsoft 365 Excel 16.0 build 20326 (giao diện tiếng Anh), **3 màn hình: 150% (chính), 100%, 100%**, Python 3.14, PyQt6 6.12, pywin32 312, uiautomation 2.0.29
**Đây là "bản thử nghiệm bộ giám sát" cam kết trong đề cương (GĐ2).** Chi tiết từng spike ở `spikes/t2-*/README.md`.

## 1. Tóm tắt

**Kết luận: kiến trúc trong đề cương khả thi.** Đọc dữ liệu, bắt sự kiện, chỉ vị trí bằng overlay và sinh kịch bản bằng AI đều đã chạy được trên Excel thật. Không phải thu hẹp phạm vi. **Cả 7 task GĐ2 đã xong**; còn 1 việc xác nhận trên máy trung tâm (Office tiếng Việt), chuyển sang T9.3 (mục 4). Có **10 quyết định thiết kế** (mục 3) rút ra từ các lỗi gặp khi thử.

## 2. Làm được / chưa làm được / cách thay thế

| Hạng mục | Kết quả | Số đo | Ghi chú, cách thay thế |
|---|---|---|---|
| Đọc giá trị, công thức qua COM (T2.1) | ✅ | Cả vùng 1.000 ô: 0,6–1,7 ms. Từng ô: ~0,5 ms/ô | Luôn đọc theo vùng |
| Đọc định dạng ô qua COM (T2.1) | ✅ | `Font.Bold` từng ô: 1,85 ms/ô | Chỉ đọc cho vùng mục tiêu của bước hiện tại |
| COM ↔ openpyxl cho cùng kết quả (T2.1) | ✅ | 222/222 ô khớp giá trị, công thức | Lệch duy nhất: mã định dạng ngày dựng sẵn số 14 → chuẩn hóa trong snapshot |
| Đọc/ghi `NumberFormat` đúng trên máy vi-VN (T1.2, T2.1) | ✅ | | **Bắt buộc dùng LCID 1033**, nếu không sẽ đọc sai |
| Sự kiện `SheetChange` / `SelectionChange` / `SheetActivate` (T2.2) | ✅ | Trễ 7–25 ms | Cần vòng bơm thông điệp trên luồng monitor |
| Phát hiện hộp thoại đang mở (T2.2, T2.4) | ✅ | ~220 ms | class `bosa_sdm_XL9` + PID; UIA đọc tên, tab |
| **Xử lý khi Excel bận (đang sửa ô / mở hộp thoại)** (T2.2) | ✅ | Chạy bền 10 phút, 374 thao tác, 393 lần bận: **0 crash** | Đọc vùng ô vẫn chạy khi bận; lỗi bận có dạng `AttributeError` (phải bắt); `Excel.Ready` không phát hiện được lúc sửa ô → dùng `is_excel_busy()` |
| Bộ lọc, trang in, biểu đồ, mã bài trong thuộc tính tùy chỉnh (T2.3) | ✅ | 2–28 ms; ghi PageSetup 440–560 ms | Cả COM và openpyxl đều đọc được |
| Trạng thái sắp xếp (T2.3) | ✅ theo cách khác | | Không tin `Sort.SortFields`; kiểm bằng thứ tự dữ liệu |
| Tìm tab và nút Ribbon (T2.4) | ✅ | 0,1–0,7 s mỗi lần tìm | Theo AutomationId = `idMso`; nút chỉ có khi tab đang chọn và nhóm không bị gộp. Danh mục ~220 nút: `spikes/t2-4-uia-ribbon/danh-muc-idmso.md` |
| Trạng thái nút bật/tắt (T2.4) | ✅ | | `CommandBars.GetPressedMso` (COM), không cần UIA |
| Mục đang chọn trong danh sách của hộp thoại (T2.4) | ✅ | | `List.SelectionPattern.GetSelection()` hoặc `LegacyIAccessible.Value` (không dùng `ListItem.IsSelected`) |
| Tọa độ ô trên màn hình (T2.4, T2.5) | ✅ | Lệch ≤ 1 px | COM `PointsToScreenPixelsX/Y` khi DPI cửa sổ = DPI hệ thống; **màn hình phụ khác DPI thì COM lệch ~850 px → dùng UIA** |
| Overlay chỉ đúng ô và nút, bám theo zoom/cuộn/di chuyển, nhiều màn hình (T2.5) | ✅ | 8/8 trường hợp có ảnh: 150%, 100% (màn hình phụ), mô phỏng 125% | Mỗi màn hình một overlay; chuột xuyên qua (kiểm bằng `WindowFromPoint`), không giành focus |
| AI sinh kịch bản từ diff (T2.6) | ✅ có điều kiện | 3–13 s/bài; độ phủ diff 100% | Phải có kiểm tra sau sinh, xem mục 3 |
| **AI viết gợi ý đúng sự thật** (T2.6) | ❌ | b09: bịa số, bảo gõ đè công thức | Ngữ cảnh "giữ nguyên" + kiểm tra số/địa chỉ trong gợi ý + giảng viên duyệt |
| In ra PDF (b12, b13) | ✅ | | Sự kiện `WorkbookBeforePrint` báo cả khi in ra máy in PDF lẫn khi Xuất PDF → chấm được |

## 3. Quyết định thiết kế rút ra (đưa vào GĐ3)

| # | Quyết định | Từ | Áp dụng ở |
|---|---|---|---|
| 1 | **Mọi đọc/ghi `NumberFormat` qua COM dùng LCID 1033**; không dùng địa chỉ ghép vùng; `Range.Sort` luôn truyền `Orientation=1` | T1.2, T2.3 | `quy-tac-code.md` mục 2.3 (đã thêm), T7.2 |
| 2 | **Monitor hướng sự kiện**: `SheetChange` cho biết vùng đổi → chỉ đọc lại vùng đó (đọc theo vùng); định dạng chỉ đọc trong vùng mục tiêu | T2.1, T2.2 | T3.3, T7.3 |
| 3 | **Snapshot chuẩn hóa định dạng theo ý nghĩa** (số chữ số thập phân, dấu nghìn, loại); ngày dựng sẵn → "ngày ngắn" | T2.1 | T3.3, T4.1 |
| 4 | **Vùng mục tiêu giao diện lưu bằng `idMso`** (`{"tab": "TabHome", "control": "CommaStyle"}`), không lưu tên hiển thị | T2.4 | T3.2 |
| 5 | **Overlay**: mỗi màn hình một cửa sổ; ô dùng COM `PointsToScreenPixels` khi DPI cửa sổ = DPI hệ thống, ngược lại dùng UIA; Ribbon dùng UIA; chỉ hiện khi Excel là cửa sổ trước; gợi ý cấp 3 chỉ tab trước rồi mới chỉ nút | T2.4, T2.5 | T7.7 |
| 6 | **Mã bài lưu trong thuộc tính tùy chỉnh `tutor_exercise_id`**: openpyxl ghi khi phát hành, COM đọc khi học viên mở file | T2.3 | T5.6, T7.4 |
| 7 | **Diff có ngữ cảnh**: ô đã có công thức/dữ liệu ở file đề được đánh dấu "giữ nguyên"; bỏ qua định dạng Excel tự áp cho ô công thức; kèm tiêu đề cột | T2.6 | T4.3, T5.5 |
| 8 | **Ba lớp kiểm cho kịch bản AI**: (a) tự kiểm điều kiện trên đề/đáp án, (b) luật bắt buộc thêm `value_equals` cho mọi vùng công thức, (c) kiểm số liệu và địa chỉ ô trong chữ gợi ý; sau đó giảng viên duyệt | T2.6 | T4.5, T5.5 |
| 9 | **Monitor chịu được Excel bận**: thử lại có giới hạn, bắt cả `com_error` bận lẫn `AttributeError`; biết trạng thái bận bằng `is_excel_busy()` (không dùng `Excel.Ready`); đang sửa ô thì không chen gợi ý | T2.2 | `quy-tac-code.md` 2.3 mục 2 (đã thêm), T7.3, T7.5 |
| 10 | **`printed_to_pdf` chấm bằng sự kiện `WorkbookBeforePrint`**; `off_target` đọc được hộp thoại, tab, mục đang chọn | T2.4 | `danh-muc-dieu-kien.md` (đã cập nhật), T7.3 |

**Chốt thư viện:** UI Automation dùng `uiautomation==2.0.29` (đã thêm vào `apps/desktop/pyproject.toml`). Không cần MSAA riêng, vì trạng thái nút đọc qua `CommandBars.GetPressedMso`.

## 4. Việc cần người thao tác

Ba việc trước đây ghi "cần người thao tác" đã làm được tự động trên máy này:

| Việc | Đã làm thế nào |
|---|---|
| Excel bận khi đang gõ trong ô / mở hộp thoại | Đưa phiên Excel riêng vào chế độ sửa ô thật (`AttachThreadInput` + `PostMessage`) và mở hộp thoại bằng nút Ribbon (UIA); chạy bền 10 phút (T2.2) |
| Màn hình 100% và nhiều màn hình | Máy có 2 màn hình phụ 100% → chạy thật; Excel kéo sang màn hình phụ (T2.5) |
| Màn hình 125% | Mô phỏng bằng `QT_SCALE_FACTOR` (phép quy đổi của Qt đúng với tỉ lệ bất kỳ) (T2.5) |

**Còn 1 việc, chuyển sang T9.3 (khảo sát máy trung tâm):** chạy `spikes/t2-4-uia-ribbon/uia_ribbon.py` trên máy có **Office tiếng Việt** để xác nhận `idMso` không đổi. Máy này chỉ có giao diện tiếng Anh; không tự cài gói ngôn ngữ lên máy người dùng. Rủi ro thấp vì `idMso` là mã định danh cố định của Office. Nếu máy trung tâm đặt 125% thì chạy luôn `spikes/t2-5-overlay/overlay.py`.

## 5. Rủi ro còn lại

| Rủi ro | Mức | Giảm thiểu |
|---|---|---|
| Excel từ chối lệnh khi học viên đang gõ, monitor bỏ lỡ thay đổi | Thấp (đã kiểm chứng) | Đọc vùng ô vẫn chạy khi bận; thử lại có giới hạn; `SheetChange` báo khi học viên Enter |
| AI bịa nội dung gợi ý | Cao | 3 lớp kiểm ở quyết định 8 + giảng viên duyệt (đã có trong đề cương) |
| Kết quả AI không ổn định giữa các lần chạy | Trung bình | T5.8 đo trên nhiều lần chạy; giảng viên có thể bấm "Sinh lại" |
| Máy trung tâm khác cấu hình (Office tiếng Việt, DPI, nhiều màn hình) | Thấp | DPI và nhiều màn hình đã xử lý (T2.5); Office tiếng Việt xác nhận ở T9.3 |
| Ribbon gộp nhóm khi cửa sổ Excel hẹp, overlay không tìm thấy nút | Trung bình | Chỉ vào nhóm hoặc nhắc phóng to cửa sổ (T7.7) |
