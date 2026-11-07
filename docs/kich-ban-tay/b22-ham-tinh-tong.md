# Kịch bản viết tay — b22: Hàm tính tổng SUM

**Task:** T1.5 · **Trạng thái:** bản nháp, chờ Hòa rà soát và GVHD góp ý
**Bài:** `samples/_local/b22-ham-tinh-tong/` · **Sheet làm bài:** `Bài 01` · **Đáp án:** `dap-an.xlsx` (cùng bố cục, chỉ sheet `Bài 01`)
**Đề trong bài:** ô J9:J11: (1) "Hãy tính Tổng tiền bằng hàm SUM", (2) "Hãy hoàn thành dòng TỔNG CỘNG bằng hàm SUM", (3) "Hãy dùng phương pháp sao chép công thức để thực hiện nhanh"
**Kiến thức liên quan:** b18 (sao chép công thức), b21 (cú pháp hàm)

## 1. Tổng quan

| Vùng | Nội dung | Đáp án mẫu |
|---|---|---|
| F9:F19 | Tổng tiền mỗi ngày = Tiền Bún + Tiền Thịt + Tiền Cá | `=SUM(C9:E9)`, sao chép xuống tới F19 |
| C20:E20 | Tổng cộng từng loại | `=SUM(C9:C19)`, sao chép sang phải |
| F20 | Tổng cộng tất cả | `=SUM(F9:F19)` hoặc `=SUM(C20:E20)`, **cả hai đều đúng** |

**Điểm khác b09:** bài này có **nhiều đáp án đúng**. Kiểm chứng phải dựa vào **giá trị + có dùng hàm SUM + công thức nhất quán khi sao chép**, không so nguyên văn công thức với đáp án.

**Câu hỏi cho GVHD:**
1. `=SUM(C9,D9,E9)` có được chấp nhận không? *(Bản nháp: có, vì vẫn dùng SUM.)*
2. Sheet `Bài 02` (tổng theo ngày, theo loại, các dòng "Tổng tiền" xen giữa): dòng TỔNG CỘNG nên là `=SUM(C12,C16,C20)` hay `=C12+C16+C20`? Chưa làm đáp án cho sheet này, chờ thầy cô xác nhận.

## 2. Quy ước chung

Giống [b09](b09-du-lieu-dang-so.md#2-quy-ước-chung-cho-mọi-bước). **Điều kiện toàn bài:** không sửa dữ liệu C9:E19.

**Kỹ thuật kiểm "có sao chép":** đọc công thức ở dạng **R1C1**. Công thức được sao chép từ một ô thì mọi ô trong vùng có **cùng một công thức R1C1**. Ví dụ F9:F19 đều là `=SUM(RC[-3]:RC[-1])`.

**Lưu ý (đã kiểm chứng trên Excel thật):** R1C1 đồng nhất **không** chứng minh công thức đúng. Khi học viên dùng địa chỉ tuyệt đối `=SUM($C$9:$E$9)` rồi sao chép, R1C1 vẫn đồng nhất (`=SUM(R9C3:R9C5)`), nhưng mọi ô cho cùng một kết quả. Vì vậy luôn kiểm **cả giá trị**. Khi giá trị sai mà R1C1 chứa địa chỉ tuyệt đối (dạng `R9C3`, không có ngoặc vuông), đó là dấu hiệu để đưa ra phản hồi riêng cho lỗi `$`.

## 3. Các bước

### Bước 1 — Tính Tổng tiền ngày đầu tiên bằng hàm SUM

| Mục | Nội dung |
|---|---|
| Thẻ yêu cầu | Tính **Tổng tiền** của ngày đầu tiên (ô F9) bằng **hàm SUM** |
| Vùng mục tiêu | Trang tính: F9 · Tham chiếu: C9:E9 · Giao diện: thẻ Home → **AutoSum (Σ)** hoặc thẻ Formulas |
| Điều kiện kiểm chứng | (a) F9 là **công thức** · (b) công thức **có dùng hàm SUM** · (c) giá trị bằng đáp án (250000) |
| Tín hiệu kích hoạt | F9 thay đổi mà chưa đạt; dừng 60 giây khi F9 còn trống |
| Phản hồi riêng cho lỗi hay gặp | **Đúng kết quả nhưng dùng phép cộng** `=C9+D9+E9`: "Kết quả đúng rồi! Nhưng bài yêu cầu dùng hàm SUM, hãy viết lại bằng SUM." · **Gõ số 250000** (không có công thức): "Ô Tổng tiền cần công thức để tự tính lại khi số liệu thay đổi." · **Vùng thiếu/thừa** (ví dụ `=SUM(C9:D9)` hoặc kéo cả cột Ngày mua B9): "Hãy kiểm tra lại vùng cộng: chỉ gồm Tiền Bún, Tiền Thịt, Tiền Cá." |

| Cấp | Gợi ý |
|---|---|
| 1 | Tổng tiền một ngày = cộng 3 khoản tiền trên cùng dòng. Excel có sẵn hàm để cộng một vùng ô. |
| 2 | Dùng hàm **SUM** với vùng 3 ô tiền. Nút **AutoSum (Σ)** sẽ gõ sẵn hàm này cho bạn. |
| 3 | *(Overlay)* khung ô F9 và vùng C9:E9 → mũi tên tới nút AutoSum. |
| 4 | 1) Chọn ô F9. 2) Gõ `=SUM(` rồi quét chọn C9:E9, gõ `)` và Enter. *(Hoặc chọn F9 → **Home** → **AutoSum** → kiểm tra vùng được chọn là C9:E9 → Enter.)* |

### Bước 2 — Sao chép công thức xuống các ngày còn lại

| Mục | Nội dung |
|---|---|
| Thẻ yêu cầu | Hoàn thành **Tổng tiền** cho tất cả các ngày (F10:F19) bằng cách **sao chép công thức** |
| Vùng mục tiêu | Trang tính: F9:F19 · Thao tác: **Fill Handle** (ô vuông nhỏ góc dưới phải ô F9) |
| Điều kiện kiểm chứng | (a) F9:F19 đều là công thức · (b) **cùng một công thức R1C1**, có SUM · (c) giá trị từng ô bằng đáp án |
| Tín hiệu kích hoạt | Mới điền một phần F10:F19 rồi dừng 45 giây; giá trị sai và R1C1 chứa địa chỉ tuyệt đối (`R9C3`) → lỗi `$` |
| Phản hồi riêng cho lỗi hay gặp | **Mọi ô ra cùng một số** (dùng `$C$9:$E$9`): "Các ngày đang ra cùng một tổng tiền. Công thức đang dùng địa chỉ cố định ($), nên khi sao chép không tự đổi theo dòng." · **Gõ tay từng ô**: chấp nhận nếu đúng, nhưng nhắc: "Lần sau thử kéo Fill Handle để làm nhanh hơn." (yêu cầu 3 của đề) |

| Cấp | Gợi ý |
|---|---|
| 1 | Các ngày khác tính giống hệt ngày đầu, chỉ khác dòng. Không cần gõ lại từng ô. |
| 2 | Dùng **Fill Handle**: kéo góc dưới phải của ô F9 xuống, Excel tự đổi số dòng trong công thức. |
| 3 | *(Overlay)* chấm tròn ở góc dưới phải ô F9 → mũi tên kéo xuống tới F19. |
| 4 | 1) Chọn ô F9. 2) Đưa chuột tới góc dưới phải ô cho tới khi hiện dấu **+** màu đen. 3) Kéo xuống tới F19 (hoặc nhấp đúp vào dấu +). 4) Bấm vào F15, thanh công thức phải là `=SUM(C15:E15)`. |

### Bước 3 — Dòng TỔNG CỘNG

| Mục | Nội dung |
|---|---|
| Thẻ yêu cầu | Hoàn thành dòng **TỔNG CỘNG** (C20:F20) bằng **hàm SUM** |
| Vùng mục tiêu | Trang tính: C20:F20 · Tham chiếu: C9:F19 |
| Điều kiện kiểm chứng | (a) C20:F20 là công thức có SUM · (b) giá trị bằng đáp án (F20 = 1.895.000) · (c) C20:E20 **cùng một công thức R1C1** (sao chép sang phải). F20 được phép khác C20:E20 (`=SUM(C20:E20)` cũng đúng) |
| Tín hiệu kích hoạt | Ô trong C20:F20 thay đổi mà sai; dừng 60 giây |
| Phản hồi riêng cho lỗi hay gặp | **Vùng tính cả dòng tiêu đề** (`=SUM(C8:C19)`): kết quả vẫn đúng vì SUM bỏ qua chữ, nên chấp nhận nhưng nhắc chọn đúng vùng số liệu · **Thiếu dòng cuối** (`=SUM(C9:C18)`): "Tổng đang thiếu ngày cuối cùng." · **Tổng cộng của cột Tổng tiền bị cộng 2 lần** (`=SUM(C20:F20)` ở ô khác): "Ô này đang cộng cả cột Tổng tiền, nên bị tính trùng." |

| Cấp | Gợi ý |
|---|---|
| 1 | Tổng cộng của một cột = cộng tất cả các ngày trong cột đó. |
| 2 | Dùng **SUM** cho cả cột ở ô C20, rồi sao chép công thức sang phải. |
| 3 | *(Overlay)* khung C20 và vùng C9:C19 → mũi tên kéo Fill Handle sang tới F20. |
| 4 | 1) Chọn C20, gõ `=SUM(C9:C19)` rồi Enter (hoặc AutoSum). 2) Chọn lại C20, kéo Fill Handle sang phải tới F20. 3) Bấm vào E20, thanh công thức phải là `=SUM(E9:E19)`. |

## 4. Hoàn thành bài

| Yêu cầu trong đề (J9:J11) | Bước |
|---|---|
| 1. Tính Tổng tiền bằng hàm SUM | 1, 2 |
| 2. Hoàn thành dòng TỔNG CỘNG bằng hàm SUM | 3 |
| 3. Dùng phương pháp sao chép công thức | 2, 3 (kiểm bằng công thức R1C1 đồng nhất) |
