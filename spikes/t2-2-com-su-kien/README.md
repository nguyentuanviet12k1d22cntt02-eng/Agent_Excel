# T2.2 — Sự kiện COM và khi Excel đang bận

**Mục tiêu:** bắt `SheetChange`, `SelectionChange`, `SheetActivate`; xử lý khi Excel từ chối lệnh COM vì người học đang gõ trong ô hoặc đang mở hộp thoại.

**Chạy:**

```powershell
# Tự kiểm tra trên phiên Excel riêng (một cửa sổ Excel sẽ hiện vài giây)
.venv\Scripts\python spikes\t2-2-com-su-kien\events_busy.py

# Kiểm tra thật: mở Excel, mở một file bất kỳ, rồi chạy lệnh dưới và thao tác tự do trong 2 phút
# (gõ trong ô mà CHƯA bấm Enter, mở Format Cells, đổi sheet…)
.venv\Scripts\python spikes\t2-2-com-su-kien\events_busy.py --attach 120
```

## Kết quả tự động (máy của Việt, 07/11/2026)

| Kiểm tra | Kết quả |
|---|---|
| `SheetChange` khi ghi giá trị | ✅ nhận được, trễ **~7 ms** |
| `SheetChange` khi ghi công thức | ✅ nhận được, trễ **~14 ms** |
| `SheetSelectionChange` khi chọn vùng | ✅ nhận được, có địa chỉ vùng (`$E$5:$F$6`) |
| `SheetActivate` khi thêm/đổi sheet | ✅ nhận được |
| Phát hiện hộp thoại Format Cells đang mở | ✅ tìm thấy cửa sổ class `bosa_sdm_XL9`, tiêu đề `Format Cells`, đúng tiến trình Excel |
| Đóng hộp thoại không cần bàn phím | ✅ `WM_CLOSE` đóng được |
| **Excel từ chối lệnh khi bận** | ⚠️ **Chưa tái hiện được tự động** (xem dưới) |

**Vì sao chưa tái hiện được trạng thái bận:**

1. Hộp thoại mở bằng `Dialogs(...).Show()` **từ chính script** không làm Excel từ chối lệnh của script (đọc A1 vẫn được, 0 lần bị từ chối).
2. Gửi phím F2 bằng `PostMessage` vào cửa sổ lưới `EXCEL7` không đưa Excel vào chế độ sửa ô (`Excel.Ready` vẫn `True`).
3. Không dùng cách giả lập bàn phím toàn hệ thống, vì có thể gõ nhầm vào ứng dụng khác đang mở trên máy.

→ Hàm `read_with_retry` (thử lại khi gặp mã `0x80010001 RPC_E_CALL_REJECTED` hoặc `0x8001010A RPC_E_SERVERCALL_RETRYLATER`) **đã viết nhưng chưa được kiểm chứng với lỗi thật**.

## Việc còn lại để đóng T2.2 (cần người thao tác)

Linh chạy `--attach 120`, trong lúc đó: (1) gõ dở trong một ô, chờ 5 giây rồi mới Enter; (2) mở Format Cells và để mở 5 giây; (3) đổi sheet. Ghi lại số lần bị từ chối và mã lỗi in ra:

| Thao tác | Bị từ chối? | Mã lỗi | Ghi chú |
|---|---|---|---|
| Gõ dở trong ô | | | |
| Mở Format Cells | | | |
| Đổi sheet | | | |

## Kết luận (tạm thời)

1. **Dùng sự kiện là chính, không đọc định kỳ cả trang.** `SheetChange` cho biết chính xác vùng vừa đổi, trễ dưới 15 ms, nên chỉ cần đọc lại đúng vùng đó (kết hợp với T2.1: đọc theo vùng).
2. Sự kiện cần **bơm thông điệp** (`pythoncom.PumpWaitingMessages`) trên luồng đã đăng ký sự kiện. Luồng `monitor/` của Desktop phải có vòng lặp này (đúng quy tắc "COM chạy trên luồng riêng").
3. Phát hiện hộp thoại bằng **class cửa sổ `bosa_sdm_XL9` + PID của Excel**: rẻ hơn UI Automation, dùng được cho tín hiệu `off_target`. Tiêu đề hộp thoại phụ thuộc ngôn ngữ Office, nên phân biệt từng hộp thoại cụ thể cần thêm UIA (T2.4).
4. Sau `Quit()`, tiến trình Excel còn sống vài giây rồi mới thoát. Không coi đây là lỗi rò tiến trình.
