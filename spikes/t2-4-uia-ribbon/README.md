# T2.4 — UI Automation / MSAA: Ribbon, nút lệnh, hộp thoại, vị trí ô

**Mục tiêu:** tìm được tab và nút trên Ribbon (để overlay chỉ vào), đọc trạng thái nút, phát hiện hộp thoại, lấy tọa độ ô trên màn hình.

**Chạy:** `.venv\Scripts\python spikes\t2-4-uia-ribbon\uia_ribbon.py`
Cần thư viện `uiautomation==2.0.29` (`.venv\Scripts\python -m pip install uiautomation==2.0.29`). Một cửa sổ Excel riêng hiện lên ~20 giây; không giả lập bàn phím/chuột.

## Kết quả (máy của Việt: Office tiếng Anh 1033, **màn hình 150%** (DPI 144), 07/11/2026)

**1. Tab Ribbon** (tìm mất ~350 ms)
- Tìm được 12 tab Ribbon. Phải lọc theo cha `Ribbon Tabs`, vì các **tab sheet** (`Sheet1`) cũng là `TabItemControl`.
- Phiên Excel mới mở đang chọn tab **Insert**, không phải Home. Chọn tab Home qua `SelectionItemPattern.Select()` được.
- **Nút chỉ có trong cây UIA khi tab chứa nó đang được chọn.**

**2. Nút lệnh trên tab Home** (tìm mỗi nút 80–120 ms)

| Nút (Name) | AutomationId | Tìm thấy |
|---|---|---|
| Comma Style | `CommaStyle` | ✅ |
| Decrease Decimal | `DecimalsDecrease` | ✅ |
| Increase Decimal | `DecimalsIncrease` | ✅ |
| Align Right | `AlignRight` | ✅ |
| Bold | `Bold` | ✅ |
| AutoSum, Sort & Filter | — | ❌ (là nút tách đôi, tên khác; cần tìm theo AutomationId) |

**AutomationId chính là mã `idMso` của Office**, không phụ thuộc ngôn ngữ giao diện. Còn `Name` thì phụ thuộc ngôn ngữ (máy này đang dùng tiếng Anh).

**3. Trạng thái nút bật/tắt (Bold)**

| Cách đọc | Ô in đậm | Ô không in đậm | Dùng được? |
|---|---|---|---|
| UIA `TogglePattern` | không có | không có | ❌ |
| MSAA `State` | `0x100010` | `0x100000` | ✅ qua bit `0x10` (STATE_SYSTEM_CHECKED), không phải bit "pressed" |
| **COM `CommandBars.GetPressedMso("Bold")`** | `True` | `False` | ✅ **đơn giản nhất, không cần UIA** |

**4. Hộp thoại Format Cells**
- Tìm theo class `bosa_sdm_XL9` + PID bằng `win32gui`, rồi chuyển sang UIA (`ControlFromHandle`): ~220 ms. Tìm thẳng từ gốc cây UIA **không** thấy.
- Đọc được: tên hộp thoại (`Format Cells`), các tab và tab đang chọn, danh sách `Category` (12 mục). Chưa đọc được mục đang chọn trong `Category` (`IsSelected` đều sai), cần thử thêm.
- `WM_CLOSE` đóng được hộp thoại.

**5. Tọa độ ô trên màn hình (ở 150%)**

| Ô | COM `Pane.PointsToScreenPixelsX/Y` | UIA `DataItem.BoundingRectangle` | Lệch |
|---|---|---|---|
| A1 | (156, 557, 252, 584) | (156, 556, 252, 585) | ≤ 1 px |
| C5 | (348, 672, 444, 701) | (348, 672, 444, 701) | 0 px |
| F12 | (636, 875, 732, 905) | UIA không có (ô ngoài vùng nhìn thấy) | — |

## Kết luận

1. **Tìm nút Ribbon theo AutomationId (`idMso`), không theo tên**, để chạy được cả với Office tiếng Việt. Kịch bản (T3.2) lưu vùng mục tiêu giao diện dạng `{"tab": "TabHome", "control": "CommaStyle"}`.
2. Nút ở tab khác tab đang chọn thì **không tìm thấy**. Overlay cấp 3 phải **chỉ vào tab trước**, chờ học viên chọn tab, rồi mới chỉ vào nút.
3. **Trạng thái nút bật/tắt: dùng COM `CommandBars.GetPressedMso(idMso)`.** Không cần UIA, không phụ thuộc ngôn ngữ.
4. **Tọa độ ô: dùng COM `PointsToScreenPixelsX/Y`** (khớp UIA trong 1 px ở 150%, nhanh, có cả ô ngoài vùng nhìn thấy). UIA chỉ dùng cho Ribbon và hộp thoại.
5. Tìm bằng UIA mất 100–350 ms mỗi lần → **chỉ tìm khi cần chỉ vị trí** (gợi ý cấp 3) và lưu đệm tọa độ, không tìm theo mỗi sự kiện.
6. **Dọn dẹp:** hộp thoại còn mở thì `Quit()` lỗi và Excel không thoát. Desktop không được tự mở hộp thoại; spike/test thì luôn đóng hộp thoại trước khi `Quit()`. Khi cần đóng tiến trình còn sót, chỉ đóng phiên có cờ `/automation -Embedding`, không đóng Excel của người dùng.

## Việc còn lại

- Chạy lại trên máy có **Office tiếng Việt** (LanguageID 1066) để xác nhận AutomationId giữ nguyên.
- Tìm AutomationId của các nút tách đôi (AutoSum, Sort & Filter) và đọc mục đang chọn trong danh sách Category.
- Thử bắt hộp thoại **In** (T1.6: `printed_to_pdf`).
