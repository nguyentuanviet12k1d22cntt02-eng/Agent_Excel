# T2.4 — UI Automation / MSAA: Ribbon, nút lệnh, hộp thoại, vị trí ô, sự kiện in

**Mục tiêu:** tìm được tab và nút trên Ribbon (để overlay chỉ vào), đọc trạng thái nút, phát hiện hộp thoại và nội dung bên trong, lấy tọa độ ô trên màn hình, bắt được thao tác in.

**Chạy:**

```powershell
.venv\Scripts\python spikes\t2-4-uia-ribbon\uia_ribbon.py            # kiểm tra, ~30 giây
.venv\Scripts\python spikes\t2-4-uia-ribbon\uia_ribbon.py --catalog  # xuất danh mục nút → danh-muc-idmso.md
```

Cần `uiautomation==2.0.29` (đã có trong `apps/desktop`). Một cửa sổ Excel riêng hiện lên; không giả lập bàn phím/chuột.

## Kết quả (máy của Việt: Office tiếng Anh 1033, **màn hình 150%** (DPI 144), 07/11/2026)

**1. Tab Ribbon** (tìm mất 350 ms – 3,5 s tùy máy đang bận)
- Tìm được 12 tab Ribbon, mỗi tab có AutomationId riêng (`TabHome`, `TabInsert`, `TabPageLayoutExcel`, `TabFormulas`, `TabData`, `TabView`…). Phải lọc theo cha `Ribbon Tabs`, vì **tab sheet** (`Sheet1`) cũng là `TabItemControl`.
- Phiên Excel mới mở đang chọn tab **Insert**, không phải Home. Chọn tab qua `SelectionItemPattern.Select()` được.
- **Nút chỉ có trong cây UIA khi tab chứa nó đang được chọn**, và khi cửa sổ đủ rộng: cửa sổ hẹp thì Ribbon gộp cả nhóm thành một nút, các nút con biến mất khỏi cây UIA.

**2. Nút lệnh — tìm theo AutomationId** (250–750 ms mỗi nút)

| Nút | AutomationId (= idMso) | Tên hiển thị (Name) | Loại UIA |
|---|---|---|---|
| Comma Style | `CommaStyle` | Comma Style | Button |
| Decrease / Increase Decimal | `DecimalsDecrease` / `DecimalsIncrease` | Decrease Decimal / Increase Decimal | Button |
| Align Right | `AlignRight` | Align Right | Button |
| Bold | `Bold` | Bold | Button |
| AutoSum | `AutoSum` | **Sum** | Button (phần mũi tên: `AutoSumMenu_Dropdown`) |
| Sort & Filter | `SortFilterMenu` | Sort & Filter | MenuItem |

Lần chạy đầu tìm theo **tên** nên không thấy AutoSum, vì tên hiển thị thật là "Sum". Tìm theo AutomationId thì thấy hết. **Danh mục đầy đủ ~220 nút của 6 tab: [danh-muc-idmso.md](danh-muc-idmso.md)**, dùng cho trường vùng mục tiêu giao diện của kịch bản (T3.2).

**3. Trạng thái nút bật/tắt (Bold)**

| Cách đọc | Ô in đậm | Ô không in đậm | Dùng được? |
|---|---|---|---|
| UIA `TogglePattern` | không có | không có | ❌ |
| MSAA `State` | `0x100010` | `0x100000` | ✅ qua bit `0x10` (STATE_SYSTEM_CHECKED) |
| **COM `CommandBars.GetPressedMso("Bold")`** | `True` | `False` | ✅ **đơn giản nhất** (nhưng bị từ chối khi Excel bận, xem T2.2) |

**4. Hộp thoại Format Cells**
- **Mở bằng nút mở rộng nhóm Number** (`FormatCellsNumberDialog`) qua UIA `InvokePattern`, giống người dùng bấm. (Mở bằng COM `Dialogs(...).Show()` thì Excel không ở trạng thái bận như thật, xem T2.2.)
- Tìm theo class `bosa_sdm_XL9` + PID bằng `win32gui`, rồi chuyển sang UIA (`ControlFromHandle`). Tìm thẳng từ gốc cây UIA **không** thấy.
- Đọc được tên hộp thoại, 6 tab và tab đang chọn (`Number`).
- **Mục đang chọn trong danh sách Category: đọc được** (ô A1 định dạng `0.00%`):

| Cách đọc | Kết quả |
|---|---|
| `ListItem.SelectionItemPattern.IsSelected` | `[]` — không dùng được (cách lần trước) |
| **`List.SelectionPattern.GetSelection()`** | `['Percentage']` ✅ |
| **`List.LegacyIAccessible.Value`** | `'Percentage'` ✅ |

- Danh sách mã định dạng trong hộp thoại hiển thị **theo cài đặt vùng vi-VN** (`#.##0,00`), khác mã chuẩn COM trả về với LCID 1033. So sánh định dạng phải dùng COM + LCID 1033, không đọc chữ trong hộp thoại.
- `WM_CLOSE` đóng được hộp thoại.

**5. Tọa độ ô trên màn hình (màn hình chính 150%)**

| Ô | COM `PointsToScreenPixelsX/Y` | UIA `DataItem.BoundingRectangle` | Lệch |
|---|---|---|---|
| A1 | (83, 482, 203, 510) | (82, 482, 202, 511) | ≤ 1 px |
| C5 | (299, 599, 395, 626) | (298, 598, 394, 627) | ≤ 1 px |
| F12 | (587, 800, 683, 830) | (586, 801, 682, 830) | ≤ 1 px |

⚠️ Chỉ đúng khi Excel nằm trên màn hình có DPI bằng DPI hệ thống. Ở màn hình phụ khác DPI, COM lệch hàng trăm pixel. Xem T2.5.

**6. Sự kiện in** (tín hiệu cho điều kiện `printed_to_pdf`, bài b12, b13)

| Thao tác | `Application.WorkbookBeforePrint` |
|---|---|
| In bằng máy in "Microsoft Print to PDF" | ✅ có báo |
| Xuất PDF (`ExportAsFixedFormat`, tương đương File → Export) | ✅ có báo |

## Kết luận

1. **Tìm nút Ribbon theo AutomationId (`idMso`), không theo tên.** Tên đổi theo ngôn ngữ ("Sum" ≠ "AutoSum"). Kịch bản (T3.2) lưu vùng mục tiêu giao diện dạng `{"tab": "TabHome", "control": "CommaStyle"}`, lấy mã từ [danh-muc-idmso.md](danh-muc-idmso.md).
2. Nút ở tab khác tab đang chọn, hoặc nằm trong nhóm bị gộp, thì **không tìm thấy**. Overlay cấp 3 phải: chỉ vào tab trước → học viên chọn tab → mới chỉ vào nút. Nếu vẫn không thấy nút (nhóm bị gộp), chỉ vào nhóm hoặc nhắc phóng to cửa sổ Excel.
3. **Trạng thái nút bật/tắt: COM `CommandBars.GetPressedMso(idMso)`**; khi Excel bận thì dùng MSAA `State` bit `0x10`.
4. **Tọa độ ô: COM `PointsToScreenPixelsX/Y` khi DPI cửa sổ = DPI hệ thống; ngược lại dùng UIA** (T2.5). UIA dùng cho Ribbon và hộp thoại.
5. Tìm bằng UIA mất 0,1–0,7 s mỗi lần (lâu hơn khi máy bận) → **chỉ tìm khi cần chỉ vị trí** (gợi ý cấp 3) và lưu đệm tọa độ.
6. **Hộp thoại: biết đang mở hộp thoại nào, tab nào, mục nào đang chọn** → đủ cho tín hiệu `off_target` và gợi ý kiểu "trong Format Cells, chọn Number".
7. **In ra PDF bắt được bằng sự kiện `WorkbookBeforePrint`** → điều kiện `printed_to_pdf` chấm được, không còn phải xếp loại "chỉ hướng dẫn".
8. **Dọn dẹp:** hộp thoại còn mở thì `Quit()` lỗi và Excel không thoát. Spike/test luôn đóng hộp thoại trước khi `Quit()`. Khi cần đóng tiến trình còn sót, chỉ đóng phiên có cờ `/automation -Embedding`.

## Việc còn lại

- **Office tiếng Việt (LanguageID 1066):** máy này chỉ có giao diện tiếng Anh (thư mục `1036`, `3082` trong Office chỉ là gói hiệu đính). Không tự cài gói ngôn ngữ lên máy người dùng. Theo tài liệu của Microsoft, `idMso` là mã cố định, không dịch. Rủi ro thấp; **chạy `uia_ribbon.py` một lần trên máy ở trung tâm** khi đi khảo sát (T9.3) để xác nhận.
