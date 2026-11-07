# T2.2 — Sự kiện COM và khi Excel đang bận

**Mục tiêu:** bắt `SheetChange`, `SelectionChange`, `SheetActivate`; xử lý khi Excel từ chối lệnh COM vì người học đang gõ trong ô hoặc đang mở hộp thoại; chạy 10 phút thao tác liên tục không crash.

**Chạy:**

```powershell
# Tự kiểm tra trên phiên Excel riêng (một cửa sổ Excel hiện lên vài giây, đặt ở màn hình phụ nếu có)
.venv\Scripts\python spikes\t2-2-com-su-kien\events_busy.py

# Chạy bền 10 phút trên phiên Excel riêng: "người học giả lập" thao tác liên tục, monitor theo dõi
.venv\Scripts\python spikes\t2-2-com-su-kien\events_busy.py --soak 600

# Gắn vào Excel ĐANG MỞ của bạn trong 120 giây (để tự thao tác bằng tay nếu muốn)
.venv\Scripts\python spikes\t2-2-com-su-kien\events_busy.py --attach 120
```

## Cách đưa Excel vào trạng thái bận thật (không dùng bàn phím toàn hệ thống)

| Cách | Kết quả |
|---|---|
| Mở hộp thoại bằng COM `Dialogs(...).Show()` | ❌ Excel **không** bận với lệnh COM khác (không giống thực tế) |
| `PostMessage` phím F2 vào cửa sổ lưới `EXCEL7` | ❌ Excel bỏ qua |
| Double-click / bấm thanh công thức bằng `PostMessage`, UIA `SetFocus` thanh công thức | ❌ không vào chế độ sửa ô |
| **`AttachThreadInput` vào luồng Excel + `SetFocus(EXCEL7)` + `PostMessage` F2, ký tự** | ✅ **vào chế độ sửa ô thật** (Enter thì ô nhận giá trị mới, Esc thì bỏ) |
| **UIA `Invoke` nút mở rộng nhóm Number (`FormatCellsNumberDialog`)** | ✅ **mở Format Cells như người dùng bấm**, Excel bận thật |

Cả hai cách đều chỉ gửi vào cửa sổ của phiên Excel riêng do script mở, không ảnh hưởng ứng dụng khác.

## Kết quả (máy của Việt, Microsoft 365, 07/11/2026)

**1. Sự kiện**

| Kiểm tra | Kết quả |
|---|---|
| `SheetChange` khi ghi giá trị / công thức | ✅ trễ **7–25 ms** |
| `SheetSelectionChange` khi chọn vùng | ✅ có địa chỉ vùng (`$E$5:$F$6`) |
| `SheetActivate` khi thêm/đổi sheet | ✅ |

**2. Lệnh COM nào chạy được khi Excel bận**

| Lệnh | Bình thường | **Đang sửa ô** (F2, chưa Enter) | **Đang mở Format Cells** |
|---|---|---|---|
| `Excel.Ready` | `True` | **`True`** (không phát hiện được!) | `False` |
| `is_excel_busy()` (mới) | `False` | ✅ `True` | ✅ `True` |
| Đọc vùng `Range("A1:B2").Value` | ✅ | ✅ (trả giá trị **trước** khi gõ) | ✅ |
| Đọc `ActiveCell.Address` | ✅ | ✅ | ✅ |
| Đọc `ActiveSheet.Name` (gọi trễ) | ✅ | ❌ **`AttributeError`** | ❌ **`AttributeError`** |
| Ghi `Range("B1").Value = 5` | ✅ | ❌ `0x80020009` | ❌ `0x80020009` |
| `CommandBars.GetPressedMso("Bold")` | ✅ | ❌ `AttributeError` | ❌ `AttributeError` |

**Vì sao là `AttributeError` chứ không phải mã lỗi COM:** khi Excel bận, nó từ chối cả bước tra tên `IDispatch.GetIDsOfNames` bằng `0x80010001` (`RPC_E_CALL_REJECTED`). pywin32 (gọi trễ) nuốt lỗi đó rồi ném `AttributeError`, như thể thuộc tính không tồn tại. Gọi thẳng `_oleobj_.GetIDsOfNames(...)` thì thấy đúng mã `0x80010001`. Dùng ràng buộc sớm (`gencache.EnsureDispatch`) chỉ đỡ được một phần: các đối tượng trả về kiểu chung (`ActiveSheet`) và thư viện Office (`CommandBars`) vẫn gọi trễ.

→ Phiên bản `read_with_retry` cũ chỉ bắt `com_error` nên **sẽ làm monitor crash ngay khi học viên mở hộp thoại**. Đã sửa: `busy_code()` coi cả `AttributeError` là "bận".

**3. Chạy bền 10 phút** (`--soak 600`): luồng monitor chạy riêng (giống `monitor/` của Desktop: bơm thông điệp, nhận sự kiện, đọc lại vùng thay đổi, kiểm tra bận mỗi 0,2 s); "người học giả lập" làm ngẫu nhiên 374 thao tác:

| Thao tác giả lập | Số lần |
|---|---|
| Ghi ô | 119 |
| Sửa ô dở dang 1–4 s rồi Enter (70%) hoặc Esc | 115 |
| Chọn vùng | 54 |
| Mở Format Cells 1–4 s rồi đóng | 46 |
| Thêm / đổi sheet | 40 |

| Kết quả ở monitor | |
|---|---|
| **Crash / lỗi không bắt được** | **0** ✅ |
| Sự kiện nhận được | `SheetChange` 151, `SelectionChange` 91, `SheetActivate` 27 |
| Đọc lại vùng sau `SheetChange` | 151/151 thành công |
| Lần kiểm tra trạng thái | 2.553, trong đó **393 lần phát hiện Excel bận** |
| Lỗi "bận" gặp và đã xử lý | 392 lần, đều là `AttributeError (GetIDsOfNames bị từ chối)` |

104 thao tác của phía giả lập bị Excel từ chối, do Excel còn bận từ thao tác trước (ví dụ hộp thoại mở trễ hơn lúc script đóng). Đây là lỗi phía script giả lập, không ảnh hưởng monitor. Sau khi chạy bền, `Quit()` xong tiến trình Excel vẫn treo ẩn; đã đóng bằng `Stop-Process` (chỉ phiên có cờ `/automation -Embedding`).

## Kết luận

1. **Dùng sự kiện là chính, không đọc định kỳ cả trang.** `SheetChange` cho biết chính xác vùng vừa đổi, trễ dưới 25 ms → chỉ đọc lại đúng vùng đó (kết hợp T2.1: đọc theo vùng).
2. **Đọc vùng ô vẫn chạy khi Excel bận** → monitor gần như không bị chặn. Phần đang gõ dở chưa có trong ô; khi học viên Enter, `SheetChange` sẽ báo.
3. **Hàm thử lại phải bắt cả `AttributeError`** (quy tắc code 2.3 mục 2 đã cập nhật).
4. **Phát hiện "đang bận" bằng `is_excel_busy()`**: gọi `CommandBars._oleobj_.GetIDsOfNames(...)`, bị từ chối nghĩa là đang sửa ô hoặc mở hộp thoại. **Không dùng `Excel.Ready`.** Dùng cho tín hiệu: học viên đang gõ dở thì không chen gợi ý; đang mở hộp thoại thì kết hợp T2.4 để biết hộp thoại nào.
5. Sự kiện cần **bơm thông điệp** (`pythoncom.PumpWaitingMessages`) trên luồng đã đăng ký sự kiện (đúng quy tắc "COM chạy trên luồng riêng").
6. Desktop **không ghi** vào workbook (ghi bị từ chối khi bận, và quy tắc 2.3 mục 3 cấm ghi).
7. Phát hiện hộp thoại bằng **class `bosa_sdm_XL9` + PID**: rẻ hơn UIA; phân biệt hộp thoại nào thì dùng UIA (T2.4).
