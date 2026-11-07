# Danh mục điều kiện kiểm chứng và tín hiệu

**Task:** T1.6 · **Trạng thái:** bản nháp v0. Tổng hợp từ 2 kịch bản tay ([b09](../kich-ban-tay/b09-du-lieu-dang-so.md), [b22](../kich-ban-tay/b22-ham-tinh-tong.md)) và [ma trận 25 bài](../task/t1-3-ma-tran-ky-nang.md). **Chưa đối chiếu** với bộ tiêu chí kiểm tra của GĐ1 (T0.5 chưa xác nhận đã có).
**Dùng cho:** lược đồ kịch bản JSON (T3.2), snapshot workbook (T3.3), bộ kiểm tra `excel_core/checks/` (T4.4)

Tên loại (`check`, `signal`) viết tiếng Anh theo [bảng thuật ngữ](../quy-uoc/dat-ten.md#3-đặt-tên-trong-code-python); mỗi loại điều kiện là một file trong `excel_core/checks/`.

## 1. Nguyên tắc

1. **So theo ý nghĩa, không so chuỗi.** Định dạng số so "bao nhiêu chữ số thập phân, có dấu nghìn không", không so chuỗi `#,##0`. Công thức so "giá trị đúng + có dùng hàm yêu cầu + sao chép nhất quán", không so nguyên văn với đáp án.
2. **Một bài có thể có nhiều đáp án đúng** (b22: `=SUM(F9:F19)` và `=SUM(C20:E20)`). Điều kiện chỉ ràng buộc đúng những gì đề yêu cầu.
3. **Mỗi điều kiện trả về: đạt/không đạt + mã lỗi.** Mã lỗi để chọn *phản hồi riêng cho lỗi hay gặp* (ví dụ `stored_as_text`, `absolute_reference`), không chỉ báo "sai".
4. **Giá trị kỳ vọng lấy từ file đáp án cùng bố cục**, không ghi cứng trong kịch bản, trừ khi đề nói rõ.
5. Điều kiện chạy được trên **cả hai nguồn**: openpyxl (Backend tự kiểm kịch bản, T4.5) và COM (Desktop khi học viên làm). Cột "Nguồn đọc" ghi chỗ nào cần chú ý.

## 2. Loại điều kiện kiểm chứng (`check`)

### 2.1. Giá trị và kiểu dữ liệu

| `type` | Ý nghĩa | Tham số chính | Mã lỗi | Bài dùng | Nguồn đọc |
|---|---|---|---|---|---|
| `value_equals` | Giá trị vùng bằng giá trị kỳ vọng | `range`, `expected_from` (đáp án / ô tham chiếu), `tolerance` | `wrong_value`, `empty` | b09, b22, hầu hết | Cả hai. openpyxl cần giá trị đã tính (file đáp án phải được Excel lưu) |
| `value_type` | Kiểu dữ liệu: số / ngày / văn bản / logic | `range`, `kind` | `stored_as_text` | b09 (số gõ dạng chữ), b10 (ngày) | Cả hai |
| `data_unchanged` | Vùng dữ liệu gốc không bị sửa (điều kiện toàn bài) | `range` | `source_modified` | b09 (bảng thô), b22 (C9:E19) | Cả hai, so với file đề |

### 2.2. Công thức

| `type` | Ý nghĩa | Tham số chính | Mã lỗi | Bài dùng | Nguồn đọc |
|---|---|---|---|---|---|
| `is_formula` | Ô là công thức, không phải số gõ tay | `range` | `hardcoded_value` | b09 (H), b22 | Cả hai |
| `formula_uses_function` | Công thức có dùng hàm yêu cầu | `range`, `functions` (`["SUM"]`), `forbid` (tùy chọn, ví dụ cấm cộng từng ô) | `missing_function`, `used_operator_instead` | b22 – b27 | Cả hai |
| `formula_consistent` | Công thức được sao chép: cùng một công thức R1C1 trong vùng | `range` | `inconsistent_formula`, `absolute_reference` | b18, b22 | COM: `FormulaR1C1`. openpyxl: tự chuyển A1 → R1C1 (cần viết, T4.4) |
| `formula_matches_r1c1` | Công thức đúng mẫu tương đối cho trước (dùng khi chỉ có 1 cách đúng) | `range`, `r1c1` | `wrong_formula` | b09 (H: `=RC[-2]*RC[-1]`) | Như trên |

> **Đã kiểm chứng trên Excel thật:** `formula_consistent` **không** phát hiện lỗi địa chỉ tuyệt đối (`$C$9` sao chép vẫn cho R1C1 đồng nhất). Luôn đi kèm `value_equals`.

### 2.3. Định dạng ô

| `type` | Ý nghĩa | Tham số chính | Mã lỗi | Bài dùng | Nguồn đọc |
|---|---|---|---|---|---|
| `number_format` | Định dạng số theo ý nghĩa | `range`, `category` (number / accounting / percent / date / text), `decimals`, `thousands_separator`, `date_pattern` | `wrong_decimals`, `missing_separator`, `wrong_category` | b09, b10, b11 | **COM phải dùng LCID 1033** ([quy-tac-code](../quy-uoc/quy-tac-code.md) mục 2.3) |
| `alignment` | Căn lề ngang/dọc, xuống dòng | `range`, `horizontal` (chấp nhận `general` cho số khi yêu cầu căn phải), `wrap_text` | `wrong_alignment` | b07, b09 | Cả hai |
| `font` | Đậm, nghiêng, cỡ, kiểu, màu chữ | `range`, các thuộc tính cần kiểm | `wrong_font` | b05 (in đậm tiêu đề), b14 | Cả hai |
| `fill` | Màu nền | `range`, `color` hoặc `any` | `wrong_fill` | b14 | Cả hai. Màu theme cần quy đổi |
| `border` | Viền | `range`, `sides`, `style` | `missing_border` | b14 | Cả hai |
| `merged` | Vùng được gộp | `range` | `not_merged` | b07, b14 | Cả hai |

### 2.4. Cấu trúc trang tính

| `type` | Ý nghĩa | Tham số chính | Mã lỗi | Bài dùng | Nguồn đọc |
|---|---|---|---|---|---|
| `row_col_hidden` | Dòng/cột bị ẩn hoặc hiện | `rows`/`cols`, `hidden` | `wrong_visibility` | b05, b06 | Cả hai |
| `row_col_size` | Chiều cao dòng / độ rộng cột (bằng giá trị hoặc bằng dòng/cột khác) | `rows`/`cols`, `equals` hoặc `autofit` | `wrong_size` | b05, b06 | Cả hai. "Vừa nội dung" cần ngưỡng sai số |
| `layout_matches` | Bảng sau khi chèn/xóa dòng, cột khớp bố cục đáp án | `range`, `key_column` | `wrong_layout` | b05, b06 | Cả hai. Địa chỉ ô **dịch chuyển** sau khi chèn/xóa, nên không so theo địa chỉ cố định |
| `sheet_exists` | Có sheet mới (theo tên hoặc theo nội dung) | `name_pattern` | `missing_sheet` | b14 | Cả hai |

### 2.5. Dữ liệu: lọc, sắp xếp

| `type` | Ý nghĩa | Tham số chính | Mã lỗi | Bài dùng | Nguồn đọc |
|---|---|---|---|---|---|
| `autofilter` | Bộ lọc đang bật đúng cột, đúng tiêu chí | `range`, `column`, `criteria` | `no_filter`, `wrong_criteria` | b15 | COM: `AutoFilter.Filters`. openpyxl: đọc được tiêu chí lưu trong file |
| `visible_rows` | Đúng tập dòng đang hiện sau khi lọc | `range`, `expected_from` | `wrong_rows_visible` | b15 | Cả hai |
| `sorted_by` | Vùng được sắp xếp theo khóa, tăng/giảm | `range`, `key_column`, `order` | `not_sorted`, `wrong_order`, `rows_broken` (sắp xếp một cột làm lệch dòng) | b16 | Cả hai. `rows_broken`: so từng dòng với dữ liệu gốc |

### 2.6. Trang in

| `type` | Ý nghĩa | Tham số chính | Mã lỗi | Bài dùng | Nguồn đọc |
|---|---|---|---|---|---|
| `page_setup` | Hướng giấy, khổ giấy, lề, vừa trang, vùng in | các thuộc tính cần kiểm | `wrong_orientation`, `wrong_paper_size` | b13 | COM: đọc `PageSetup` **chậm** (gọi driver máy in), chỉ đọc khi bước hiện tại cần (T2.3 đo) |
| `header_footer` | Số trang ở đầu/cuối trang, vị trí trái/giữa/phải | `position`, `contains` (`&P`) | `missing_page_number`, `wrong_position` | b13 | Cả hai |

### 2.7. Biểu đồ

| `type` | Ý nghĩa | Tham số chính | Mã lỗi | Bài dùng | Nguồn đọc |
|---|---|---|---|---|---|
| `chart` | Có biểu đồ đúng loại, đúng vùng dữ liệu, có tiêu đề | `chart_types`, `data_range`, `has_title`, `title_contains` | `missing_chart`, `wrong_chart_type`, `wrong_data_range`, `missing_title` | bài trung cấp (chờ T1.1) | Cả hai (T2.3) |

### 2.8. Ngoài workbook

| `type` | Ý nghĩa | Bài | Ghi chú |
|---|---|---|---|
| `printed_to_pdf` | Đã in ra file PDF, đúng trang, đúng số bản | b12, b13 | Không thấy trong trạng thái workbook. **Bắt bằng sự kiện `Application.WorkbookBeforePrint`** (T2.4: có báo khi in ra máy in PDF và khi Xuất PDF) + kiểm file PDF xuất hiện |
| `observation_only` | Bước chỉ để học viên quan sát hoặc nhận xét | b15 bài 06, b27 | Gia sư hiện hướng dẫn, học viên tự bấm "Đã xong" |

## 3. Loại tín hiệu (`signal`)

Tín hiệu là lý do để gia sư **lên tiếng** (hiện gợi ý hoặc phản hồi). Khi không có tín hiệu, gia sư chỉ hiện thẻ yêu cầu của bước hiện tại.

| `signal` | Phát hiện bằng | Phản ứng của gia sư | Ví dụ |
|---|---|---|---|
| `wrong_result` | Vùng mục tiêu thay đổi (`SheetChange`) → chạy điều kiện → không đạt | Phản hồi theo mã lỗi; sai lặp lại thì **tăng cấp gợi ý** | Comma Style còn 2 số lẻ (b09) |
| `repeated_error` | Cùng một mã lỗi xuất hiện ≥ 2 lần trong một bước | Tăng cấp gợi ý ngay | Dùng `$` 2 lần (b22) |
| `idle` | Không có thay đổi ở vùng mục tiêu trong N giây (mặc định 60) khi bước chưa đạt | Gợi ý cấp 1 (định hướng); dừng tiếp thì tăng cấp | |
| `off_target` | Học viên sửa hoặc định dạng **ngoài** vùng mục tiêu; mở hộp thoại không liên quan bước hiện tại | Nhắc nhẹ, chỉ vị trí đúng (cấp 3) | Định dạng cột G khi đang ở bước Số lượng |
| `destructive_change` | Vi phạm điều kiện toàn bài: sửa dữ liệu gốc, gõ đè lên công thức | Phản hồi **ngay**, gợi ý Ctrl+Z | Gõ số đè lên H10 (b09) |
| `help_request` | Học viên bấm nút trợ giúp | Tăng một cấp gợi ý | |
| `step_done` | Mọi điều kiện của bước đạt | Khen ngắn, chuyển bước; bước sau bắt đầu ở cấp thấp hơn nếu bước này làm tốt | |
| `on_track` | Học viên đang làm đúng hướng: chọn đúng vùng, mở đúng hộp thoại | **Không** lên tiếng (tránh làm phiền); ghi nhật ký | Mở Format Cells khi đang chọn F10:F14 |

**Luật tăng/giảm cấp chi tiết** (bao nhiêu lần sai, bao nhiêu giây) để ở T3.4 (`luat-goi-y.md`).

## 4. Cập nhật sau GĐ2

Kết quả làm thử kỹ thuật ([t2-7-bao-cao-spike.md](../task/t2-7-bao-cao-spike.md)):
- `autofilter`, `page_setup`, `header_footer`, `chart`, thuộc tính tùy chỉnh: **đọc được bằng cả COM và openpyxl** (T2.3).
- `sorted_by`: kiểm bằng thứ tự dữ liệu, không dùng `Sort.SortFields` (T2.3).
- `number_format`: COM bắt buộc LCID 1033; định dạng ngày dựng sẵn phải chuẩn hóa (T2.1).
- `alignment` căn phải cho ô số thường **đạt sẵn trên đề** (Excel tự căn phải số) → bị tự kiểm loại là vô nghĩa (T2.6). Chỉ dùng khi đề yêu cầu căn khác mặc định.
- Vùng công thức: luôn kèm `value_equals` (AI không tự thêm, T2.6).
- `printed_to_pdf`: chấm được nhờ sự kiện `WorkbookBeforePrint` (T2.4).
- `off_target` khi mở hộp thoại: biết được hộp thoại nào, tab nào, mục nào đang chọn trong danh sách (T2.4: `SelectionPattern.GetSelection()`).

## 5. Việc còn mở

1. Đối chiếu danh mục này với **bộ tiêu chí kiểm tra và quy tắc phản hồi của GĐ1** khi nhóm xác nhận đã có (T0.5).
2. T2.1, T2.3 đo xem COM đọc được những thuộc tính nào, nhanh không → cập nhật cột "Nguồn đọc".
3. ~~T2.4 xác định `off_target` (hộp thoại) và `printed_to_pdf` làm được tới đâu.~~ Đã xong: cả hai làm được (mục 4).
4. Bổ sung loại điều kiện cho **biểu đồ, hàm logic, tham chiếu** khi có bài trung cấp (T1.1).

## 6. Mã lỗi đã chốt khi cài đặt (T4.4)

Code: `packages/excel_core/src/excel_core/checks/`, mỗi loại một file. Mã lỗi xếp theo **thứ tự ưu tiên**: khi các ô trong vùng sai theo nhiều kiểu, điều kiện trả mã đứng trước (lỗi cụ thể trước, `empty` = "chưa làm" sau cùng); mã còn lại ghi trong `detail`. Test `test_registry.py` bắt buộc mô tả trong lược đồ liệt kê đúng các mã này.

| `type` | Mã lỗi (theo thứ tự ưu tiên) |
|---|---|
| `value_equals` | `stored_as_text`, `wrong_value`, `empty` |
| `value_type` | `stored_as_text`, `wrong_type`, `empty` |
| `data_unchanged` | `formula_overwritten`, `source_modified` |
| `is_formula` | `hardcoded_value`, `empty` |
| `formula_uses_function` | `used_operator_instead`, `missing_function`, `empty` |
| `formula_consistent` | `absolute_reference`, `inconsistent_formula`, `empty` |
| `formula_matches_r1c1` | `hardcoded_value`, `wrong_formula`, `empty` |
| `number_format` | `wrong_category`, `missing_separator`, `unexpected_separator`, `wrong_decimals`, `wrong_date_pattern` |
| `alignment` | `wrong_alignment`, `not_wrapped` |
| `font` | `wrong_font` |
| `fill` | `no_fill`, `wrong_fill` |
| `border` | `missing_border`, `wrong_border_style` |
| `merged` | `not_merged` |
| `row_col_hidden` | `wrong_visibility` |
| `row_col_size` | `wrong_size` |
| `layout_matches` | `wrong_layout` |
| `sheet_exists` | `missing_sheet` |
| `autofilter` | `no_filter`, `wrong_column`, `wrong_criteria` |
| `visible_rows` | `wrong_rows_visible` |
| `sorted_by` | `rows_broken`, `wrong_order`, `not_sorted` |
| `page_setup` | `wrong_orientation`, `wrong_paper_size`, `wrong_margins`, `wrong_fit`, `wrong_centering`, `wrong_print_area` |
| `header_footer` | `wrong_position`, `missing_page_number`, `missing_header_footer` |
| `chart` | `missing_chart`, `wrong_chart_type`, `wrong_data_range`, `missing_title` |
| `printed_to_pdf` | `not_printed` |
| `observation_only` | `not_confirmed` |

Kết quả chấm có 3 trạng thái: `passed`, `failed`, `not_evaluable`. Trạng thái cuối dùng khi điều kiện không chấm được trong ngữ cảnh hiện có: `printed_to_pdf`, `observation_only` khi chấm trên file; thiếu file tham chiếu; tham số sai mà lược đồ không bắt được. Desktop gặp trạng thái này thì không tính bước là sai.

**Các quyết định khi cài đặt:**

| Điều kiện | Quyết định | Lý do |
|---|---|---|
| `value_equals` | Chữ so nguyên văn (chỉ chuẩn hóa Unicode NFC); số có sai số; ngày so được với số seri. Chữ trông như số bằng giá trị kỳ vọng → `stored_as_text` | Bài TRIM/UPPER cần đúng từng ký tự; số gõ dạng chữ là lỗi hay gặp (b09) |
| `alignment` | So **căn lề hiển thị thực tế**: General + số/ngày = right, General + chữ = left, ô trống General không tính là căn gì | Vá lỗi T2.6 (điều kiện căn phải đạt sẵn trên đề); kịch bản ghi `["right"]` là đủ |
| `formula_uses_function` | Phép toán trên từng ô lẻ, kể cả `=SUM(C9+D9+E9)`, → `used_operator_instead`; `=SUM(C9,D9,E9)` đạt | Theo phương án nháp của câu hỏi GVHD b22 |
| `formula_consistent` | Đồng nhất R1C1 mà mọi tham chiếu cố định theo chiều sao chép → `absolute_reference` | Bắt lỗi `$` mà R1C1 không bắt được |
| `formula_matches_r1c1` | Ô bị gõ đè số → `hardcoded_value` (không phải `wrong_formula`) | Khớp phản hồi ngay của b09 bước 4 |
| `number_format` | Kiểm theo thứ tự: loại → dấu nghìn → số lẻ → mẫu ngày. Ô chưa định dạng = General | Còn General thì báo sai loại trước |
| `border` | Đọc rộng 1 ô quanh vùng; cạnh chung giữa hai ô lưu ở ô nào cũng được | Excel lưu viền ở ô bên này hoặc bên kia |
| `fill`, `font` | So màu có ngưỡng 3/255 mỗi kênh | Màu theme quy đổi lệch ±1 |
| `row_col_size` `autofit` | So với kích thước của chính dòng/cột đó trong file đáp án | Không đo được chữ theo phông từ file |
| `sorted_by` | Thứ tự như Excel (số < chữ < đúng/sai < lỗi, ô trống cuối); chữ so theo chữ cái gốc bỏ dấu | Không lệch với thứ tự tiếng Việt của Excel |
| `chart` | `data_range` đạt nếu bằng vùng bao của: giá trị; giá trị + tên chuỗi; giá trị + nhãn trục; hoặc tất cả | Chọn vùng có/không tiêu đề đều ra cùng biểu đồ |
| `data_unchanged` | Ô công thức của đề: so công thức; ô hằng số: so giá trị | Giá trị công thức được phép đổi theo ô học viên nhập |
