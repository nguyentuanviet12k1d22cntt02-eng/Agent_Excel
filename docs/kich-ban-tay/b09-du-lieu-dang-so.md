# Kịch bản viết tay — b09: Định dạng dữ liệu số

**Task:** T1.4 · **Trạng thái:** bản nháp, chờ Hoài rà soát và GVHD góp ý
**Bài:** `samples/_local/b09-du-lieu-dang-so/` · **Sheet làm bài:** `2. Bang_Ke_Ban_Hang` · **Đáp án:** `dap-an.xlsx` (cùng bố cục)
**Nguồn hướng dẫn trong bài (thay giáo trình):** sheet `1. Thuc_Hanh_Tung_Buoc` (ô B5, B13) và hướng dẫn B5:B7 của sheet đề; checklist "Tiêu chí 1–3" ở sheet `3. Dap_An_Mau`

## 1. Tổng quan

**Học viên cần làm:** chép số liệu thô ở bảng dưới (dòng 18–22) lên bảng chính (dòng 10–14), rồi định dạng 4 cột số theo yêu cầu.

| Vùng | Nội dung | Yêu cầu |
|---|---|---|
| F10:F14 | Số lượng | Số nguyên, có dấu phân cách hàng nghìn |
| G10:G14 | Đơn giá (USD) | Đúng 2 chữ số thập phân |
| H10:H14 | Thành tiền (đã có công thức `=F*G`) | Giữ nguyên công thức; hiển thị 2 chữ số thập phân (Tiêu chí 2) |
| I10:I14 | Tỉ lệ giảm giá | Đúng 3 chữ số thập phân |
| F10:I14 | Cả 4 cột | Căn phải |

**Câu hỏi cho GVHD:**
1. Hướng dẫn B5:B7 không nhắc cột Thành tiền, nhưng Tiêu chí 2 lại yêu cầu Thành tiền có 2 chữ số thập phân. Có tính H10:H14 là một bước bắt buộc không? *(Bản nháp: có, là bước 4.)*
2. Đơn giá dùng `0.00` (không có dấu nghìn) có được chấp nhận không, hay bắt buộc `#,##0.00` như đáp án? *(Bản nháp: chấp nhận cả hai, vì đề chỉ yêu cầu "đúng 2 chữ số thập phân".)*

## 2. Quy ước chung cho mọi bước

- **Thẻ yêu cầu** (luôn hiện, không có cách làm): một câu nói *phải đạt gì*, đặt gần vùng mục tiêu.
- **Gợi ý 4 cấp** (chỉ hiện khi bắt được tín hiệu): `1 định hướng` → `2 gợi ý công cụ` → `3 chỉ vị trí` (overlay) → `4 hướng dẫn chi tiết`.
- **Điều kiện kiểm chứng định dạng so mã định dạng theo ý nghĩa** (số chữ số thập phân, có dấu nghìn hay không), **không so chữ hiển thị**. Lý do: cùng một định dạng, máy vi-VN hiện `1.250`, máy en-US hiện `1,250`.
- **Gợi ý không ghi cứng chữ hiển thị** như `1,250`. Dùng cách nói "có dấu phân cách hàng nghìn".
- **Điều kiện toàn bài** (kiểm ở mọi bước): không sửa bảng số liệu thô B17:I22, không xóa công thức ở H10:H14.

## 3. Các bước

### Bước 1 — Nhập Số lượng

| Mục | Nội dung |
|---|---|
| Thẻ yêu cầu | Nhập số lượng của 5 mặt hàng vào cột **Số lượng** (F10:F14), lấy từ bảng số liệu thô bên dưới |
| Vùng mục tiêu | Trang tính: F10:F14 · Tham chiếu: F18:F22 |
| Điều kiện kiểm chứng | (a) F10:F14 có giá trị bằng F18:F22 · (b) giá trị là **số**, không phải văn bản |
| Tín hiệu kích hoạt | Ô trong F10:F14 thay đổi mà sai giá trị; nhập số dạng văn bản; dừng 60 giây không có thay đổi ở F10:F14 |
| Phản hồi riêng cho lỗi hay gặp | **Số dạng văn bản** (căn trái, có tam giác xanh): "Số bạn nhập đang được Excel hiểu là chữ. Hãy xóa dấu nháy `'` hoặc khoảng trắng ở đầu rồi gõ lại." · **Dán kèm định dạng** (nền xám từ bảng thô): nhắc nhẹ, không tính là sai: "Bạn đã dán kèm màu nền của bảng thô. Có thể dùng *Paste Values* để chỉ dán giá trị." |

| Cấp | Gợi ý |
|---|---|
| 1 | Số lượng của từng mặt hàng có sẵn ở bảng số liệu thô phía dưới. Bạn chỉ cần đưa chúng lên đúng dòng. |
| 2 | Có thể gõ lại từng số, hoặc sao chép (Ctrl+C) cột Số lượng thô rồi dán (Ctrl+V) vào cột Số lượng của bảng chính. |
| 3 | *(Overlay)* khung vùng F18:F22 (nguồn) và F10:F14 (đích). |
| 4 | 1) Chọn F18:F22 → Ctrl+C. 2) Chọn ô F10 → Ctrl+V. 3) Kiểm tra 5 số đã nằm đúng dòng của từng mặt hàng. |

### Bước 2 — Định dạng Số lượng: số nguyên, có dấu phân cách hàng nghìn

| Mục | Nội dung |
|---|---|
| Thẻ yêu cầu | Cột **Số lượng** hiển thị số nguyên, có dấu phân cách hàng nghìn |
| Vùng mục tiêu | Trang tính: F10:F14 · Giao diện: thẻ Home → nhóm Number → nút **Comma Style**, nút **Decrease Decimal** |
| Điều kiện kiểm chứng | Mã định dạng của F10:F14: **0 chữ số thập phân** và **có dấu phân cách hàng nghìn**. Chấp nhận `#,##0`, `#,##0;-#,##0`, định dạng Comma/Accounting 0 số lẻ (`_(* #,##0_);…`) |
| Tín hiệu kích hoạt | Định dạng F10:F14 đổi mà chưa đạt; mở hộp thoại Format Cells khi đang chọn sai vùng; dừng 60 giây |
| Phản hồi riêng cho lỗi hay gặp | **Bấm Comma Style xong còn 2 số lẻ** (lỗi rất hay gặp vì Comma Style mặc định có 2 chữ số thập phân): "Đã có dấu phân cách hàng nghìn rồi, nhưng số lượng không cần phần thập phân." · **Có số lẻ nhưng thiếu dấu nghìn**: "Còn thiếu dấu phân cách hàng nghìn." |
| Trích hướng dẫn trong bài | "Quét chọn cột ➔ Chọn thẻ Home ➔ Tại nhóm Number ➔ Tích vào dấu , (Comma Style)" (sheet 1, ô B5) |

| Cấp | Gợi ý |
|---|---|
| 1 | Cách số được hiển thị (dấu phân cách, số chữ số thập phân) được điều chỉnh ở nhóm lệnh **Number**. |
| 2 | Nút **Comma Style** (dấu phẩy) thêm dấu phân cách hàng nghìn. Sau đó dùng **Decrease Decimal** để bỏ phần thập phân. |
| 3 | *(Overlay)* khung F10:F14 → mũi tên tới nút Comma Style → mũi tên tới nút Decrease Decimal. |
| 4 | 1) Chọn F10:F14. 2) Thẻ **Home** → nhóm **Number** → bấm **Comma Style**. 3) Bấm **Decrease Decimal** 2 lần cho tới khi không còn số lẻ. *Cách khác:* chuột phải → **Format Cells** → **Number** → Decimal places = 0 → tích **Use 1000 Separator**. |

### Bước 3 — Nhập và định dạng Đơn giá: 2 chữ số thập phân

| Mục | Nội dung |
|---|---|
| Thẻ yêu cầu | Nhập **Đơn giá** từ bảng thô vào G10:G14 và hiển thị đúng 2 chữ số thập phân |
| Vùng mục tiêu | Trang tính: G10:G14 · Tham chiếu: G18:G22 · Giao diện: nút **Increase Decimal** / **Decrease Decimal** |
| Điều kiện kiểm chứng | (a) giá trị bằng G18:G22, là số · (b) mã định dạng có **đúng 2 chữ số thập phân** (`0.00`, `#,##0.00`, Comma 2 số lẻ đều đạt) |
| Tín hiệu kích hoạt | Như bước 1–2 |
| Phản hồi riêng cho lỗi hay gặp | **Hiển thị đúng 2 số lẻ nhưng do độ rộng cột chứ không do định dạng** (định dạng General): "Số đang hiện đủ 2 số lẻ chỉ vì giá trị gốc có 2 số lẻ. Hãy đặt định dạng để mọi số luôn hiện 2 số lẻ, kể cả số tròn như 320." |
| Trích hướng dẫn trong bài | "Dùng 2 nút Increase/Decrease Decimal trên thẻ Home ➔ Tại nhóm Number" (sheet 1, ô B13) |

| Cấp | Gợi ý |
|---|---|
| 1 | Đơn giá 320 cũng phải hiện thành 320 kèm 2 chữ số 0 ở phần thập phân. Đó là việc của định dạng, không phải của giá trị. |
| 2 | Dùng **Increase Decimal** để tăng số chữ số thập phân hiển thị. |
| 3 | *(Overlay)* khung G10:G14 → mũi tên tới nút Increase Decimal. |
| 4 | 1) Sao chép G18:G22 sang G10:G14. 2) Chọn G10:G14. 3) **Home** → **Number** → bấm **Increase Decimal** cho tới khi mọi ô có đúng 2 số lẻ (hoặc Format Cells → Number → Decimal places = 2). |

### Bước 4 — Định dạng Thành tiền: 2 chữ số thập phân, giữ nguyên công thức

| Mục | Nội dung |
|---|---|
| Thẻ yêu cầu | Cột **Thành tiền** hiển thị đúng 2 chữ số thập phân. Không sửa công thức có sẵn |
| Vùng mục tiêu | Trang tính: H10:H14 |
| Điều kiện kiểm chứng | (a) H10:H14 **vẫn là công thức** `=F*G` của cùng dòng (so sánh dạng R1C1: `=RC[-2]*RC[-1]`) · (b) giá trị bằng đáp án (sai số ≤ 0,005) · (c) mã định dạng có đúng 2 chữ số thập phân |
| Tín hiệu kích hoạt | Công thức ở H bị thay bằng số gõ tay → phản hồi **ngay**, không chờ |
| Phản hồi riêng cho lỗi hay gặp | **Gõ đè số lên công thức**: "Ô Thành tiền cần giữ công thức để tự tính lại khi Số lượng hoặc Đơn giá thay đổi. Hãy bấm Ctrl+Z để khôi phục." |

| Cấp | Gợi ý |
|---|---|
| 1 | Thành tiền cũng là tiền USD như Đơn giá, nên cần cùng kiểu hiển thị. |
| 2 | Cách làm giống Đơn giá: **Increase/Decrease Decimal**. Chỉ đổi định dạng, không gõ vào ô. |
| 3 | *(Overlay)* khung H10:H14. |
| 4 | 1) Chọn H10:H14. 2) **Home** → **Number** → chỉnh **Decrease/Increase Decimal** tới đúng 2 số lẻ. 3) Bấm vào H10, kiểm tra thanh công thức vẫn là `=F10*G10`. |

### Bước 5 — Nhập và định dạng Tỉ lệ giảm giá: 3 chữ số thập phân

| Mục | Nội dung |
|---|---|
| Thẻ yêu cầu | Nhập **Tỉ lệ giảm giá** vào I10:I14 và hiển thị đúng 3 chữ số thập phân |
| Vùng mục tiêu | Trang tính: I10:I14 · Tham chiếu: I18:I22 |
| Điều kiện kiểm chứng | (a) giá trị bằng I18:I22, là số · (b) mã định dạng có **đúng 3 chữ số thập phân**, **không phải** dạng phần trăm |
| Tín hiệu kích hoạt | Như bước 1–2 |
| Phản hồi riêng cho lỗi hay gặp | **Dùng Percent Style** (hiện 1%): "Bài yêu cầu hiển thị dạng số thập phân (3 số lẻ), không phải phần trăm." · **Ô có giá trị 0 hiện "0"** thay vì 0 kèm 3 số lẻ: nhắc định dạng cả ô có giá trị 0 |

| Cấp | Gợi ý |
|---|---|
| 1 | Tỉ lệ 0.01 cần hiện với đủ 3 chữ số sau dấu thập phân, kể cả dòng có tỉ lệ bằng 0. |
| 2 | **Increase Decimal** cho tới khi đủ 3 số lẻ. Không dùng nút phần trăm (%). |
| 3 | *(Overlay)* khung I10:I14 → mũi tên tới nút Increase Decimal. |
| 4 | 1) Sao chép I18:I22 sang I10:I14. 2) Chọn I10:I14 → Format Cells → Number → Decimal places = 3. |

### Bước 6 — Căn phải các cột số

| Mục | Nội dung |
|---|---|
| Thẻ yêu cầu | Các cột Số lượng, Đơn giá, Thành tiền, Tỉ lệ giảm giá được căn phải |
| Vùng mục tiêu | Trang tính: F10:I14 · Giao diện: thẻ Home → nhóm Alignment → **Align Right** |
| Điều kiện kiểm chứng | Căn lề ngang của F10:I14 là **Right**, hoặc **General** (Excel tự căn phải số). Không đạt nếu Left hoặc Center |
| Tín hiệu kích hoạt | Căn lề vùng F10:I14 thành Left/Center |
| Ghi chú | Thường tự đạt nếu bước 1–5 nhập số đúng (không phải văn bản). Gia sư chỉ nhắc khi học viên chủ động căn trái/giữa |

| Cấp | Gợi ý |
|---|---|
| 1 | Số liệu nên căn phải để các hàng đơn vị thẳng cột, dễ so sánh. |
| 2 | Nhóm **Alignment** trên thẻ Home có nút căn phải. |
| 3 | *(Overlay)* khung F10:I14 → mũi tên tới nút Align Right. |
| 4 | Chọn F10:I14 → **Home** → **Alignment** → **Align Right**. |

## 4. Hoàn thành bài

Khi cả 6 bước đạt, gia sư đối chiếu với checklist của giảng viên:

| Tiêu chí của giảng viên (sheet `3. Dap_An_Mau`) | Bước tương ứng |
|---|---|
| 1. Số lượng hiển thị số nguyên, có dấu phân cách hàng nghìn, căn phải | 1, 2, 6 |
| 2. Đơn giá và Thành tiền hiển thị đúng 2 chữ số thập phân, căn phải | 3, 4, 6 |
| 3. Tỉ lệ giảm giá hiển thị đúng 3 chữ số thập phân, căn phải | 5, 6 |

Phần luyện tập ở sheet `1. Thuc_Hanh_Tung_Buoc` (E7:E10, E15:E18) **không** đưa vào kịch bản này. Đề xuất: làm thành kịch bản riêng dạng "khởi động", có cùng loại điều kiện kiểm chứng.
