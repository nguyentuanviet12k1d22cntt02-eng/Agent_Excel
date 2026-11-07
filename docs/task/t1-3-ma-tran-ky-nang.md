# T1.1 – T1.3 — Bộ bài tập mẫu và ma trận kỹ năng

**Cập nhật:** 07/11/2026 · **Nguồn:** thư mục bài học gốc `Cơ bản/` của trung tâm (25 bài: 23 file Excel, 2 file PDF)

## 1. Tình trạng

| Task | Trạng thái | Ghi chú |
|---|---|---|
| T1.1 Thu thập bài | 🔄 | Đã có phần **cơ bản** (bài 03–27). Còn thiếu phần trung cấp (mục 4), chưa có giáo trình riêng cho từng bài, chưa hỏi được trung tâm về quyền công khai và ngôn ngữ Office trên máy phòng thực hành |
| T1.2 Chuẩn hóa | ✅ | 25 bài nằm trong `samples/_local/b<NN>-<mô-tả>/` (không lên git vì repo public). Đã có `dap-an.xlsx` cùng bố cục với đề cho **b09** và **b22** |
| T1.3 Ma trận kỹ năng | ✅ | Mục 3. Đã phủ 7/11 nhóm kỹ năng; 4 nhóm còn thiếu bài |

### Cách tái tạo trên máy khác

```powershell
# 1. Chép thư mục bài học gốc vào gốc repo với tên "Cơ bản" (không lên git)
# 2. Chuẩn hóa vào samples/_local/
.venv\Scripts\python scripts\import_lessons.py --apply
# 3. Tạo đáp án cùng bố cục bằng Excel thật (cần Excel trên máy)
.venv\Scripts\python scripts\build_solutions.py
# 4. Chạy lại bước 2 để cập nhật thong-tin.md
.venv\Scripts\python scripts\import_lessons.py --apply
# Xem nội dung một bài, kể cả đề trong text box
.venv\Scripts\python scripts\dump_workbook.py samples\_local\b09-du-lieu-dang-so\de.xlsx
```

## 2. Phát hiện quan trọng cho thiết kế

| # | Phát hiện | Ảnh hưởng | Xử lý ở |
|---|---|---|---|
| 1 | **Đề bài nằm trong file Excel**, không có file đề riêng. Ở **8/25 bài**, đề nằm trong **text box** (hình vẽ), những bài còn lại nằm trong ô. openpyxl **không đọc** được text box | Bộ trích xuất phải đọc cả ô và text box; nếu không, AI sẽ không thấy đề | T4.2, T5.5. `dump_workbook.py` đã đọc được text box |
| 2 | Chỉ **6/23** file có đáp án, và **đáp án nằm ở vị trí khác** với đề (ví dụ b09: đề ở dòng 10–14, đáp án ở dòng 6–10) | Không so sánh từng ô giữa sheet đề và sheet đáp án được. Cần file đáp án **cùng bố cục** với đề | Web quản trị (T3.1): giảng viên nộp file đáp án cùng bố cục. Nhóm tự tạo cho bài mẫu (`build_solutions.py`) |
| 3 | Đáp án b08–b11 có **checklist "Tiêu chí 1–3"** do giảng viên soạn | Chính là điều kiện kiểm chứng viết bằng lời, AI dùng được làm đầu vào | T1.6, T5.5 |
| 4 | **Máy định dạng vùng Việt Nam** (`vi-VN`: dấu thập phân `,`, dấu nghìn `.`): pywin32 làm Excel **dịch sai mã `NumberFormat`** khi đọc/ghi; địa chỉ ghép vùng `A1:A5,C1:C5` bị lỗi | Bộ giám sát sẽ đọc sai định dạng số trên đa số máy ở Việt Nam | Đã thêm quy tắc 6–7 vào [quy-tac-code.md](../quy-uoc/quy-tac-code.md) mục 2.3; T2.1, T7.2 phải tuân theo |
| 5 | Cùng định dạng `#,##0` hiển thị `1,250` (máy en-US) hoặc `1.250` (máy vi-VN). Đề b09 lại ghi cứng "kết quả mẫu `1,250`" | Gợi ý **không được ghi cứng chuỗi hiển thị**; điều kiện kiểm chứng so **mã định dạng**, không so chữ hiển thị | T1.6, T3.2 |
| 6 | b12, b13 yêu cầu **in ra PDF và lưu vào Desktop**; b15 bài 06 yêu cầu **quan sát thanh trạng thái**; b27 yêu cầu **nhận xét** | Không kiểm chứng được bằng trạng thái workbook | T2.4 xem có bắt được hộp thoại In không; còn lại đánh dấu "chỉ hướng dẫn, không chấm" |
| 7 | Một số đề dẫn "theo **mẫu** bên dưới" (b06, b07, b14) | Mẫu là hình hoặc bảng đặt cạnh đề; AI phải biết đâu là mẫu, đâu là vùng làm bài | T3.2: kịch bản cần khai báo vùng làm bài |
| 8 | Ngày tháng trong đề b09 là **chuỗi văn bản** (`'01/01/2025'`), trong đáp án là ngày thật | Điều kiện về kiểu dữ liệu (số/ngày/văn bản) là một loại kiểm chứng riêng | T1.6 |
| 9 | File ghi tên người biên soạn (Bạch Xuân Hiến) | Là tài liệu có tác giả, cần xin phép trước khi công khai | Giữ trong `samples/_local/` |

## 3. Ma trận bài × nhóm kỹ năng

Cột **Đề ở đâu**: `ô` = đề viết trong ô, `TB` = đề trong text box.
Cột **Kiểm chứng tự động**: ✅ = kiểm được hoàn toàn bằng trạng thái workbook, ◐ = kiểm được một phần, ✗ = không kiểm được.

| Bài | Nội dung | Nhóm kỹ năng | Đề ở đâu | Đáp án | Kiểm chứng tự động |
|---|---|---|---|---|---|
| b03, b04 | Khởi động Excel, thao tác sheet (PDF) | Làm quen | PDF | — | — |
| b05 | Chèn/ẩn/xóa/chỉnh cao dòng | Tổ chức, nhập liệu | TB | — | ✅ |
| b06 | Chèn/ẩn/xóa/chỉnh rộng cột | Tổ chức, nhập liệu | TB | — | ✅ |
| b07 | Gộp ô, xuống dòng trong ô | Tổ chức, nhập liệu | TB | — | ✅ |
| b08 | Chuẩn bị nhập liệu | Tổ chức, nhập liệu | ô | sheet riêng, khác bố cục | ✅ |
| **b09** | **Định dạng số** | **Định dạng dữ liệu** | ô | **`dap-an.xlsx` cùng bố cục** | ✅ |
| b10 | Định dạng ngày tháng | Định dạng dữ liệu | ô | sheet riêng, khác bố cục | ✅ |
| b11 | Định dạng khác | Định dạng dữ liệu | ô | sheet riêng, khác bố cục | ✅ |
| b12 | In: chọn máy in, trang, số bản, xuất PDF | Thiết lập trang in | TB | — | ✗ |
| b13 | Khổ giấy, hướng giấy, đánh số trang, in PDF | Thiết lập trang in | TB | — | ◐ (in PDF thì không) |
| b14 | Tạo bảng tính theo mẫu (báo giá, phiếu, chấm công) | Định dạng, trình bày | TB | — | ◐ (so với mẫu khó) |
| b15 | Lọc theo mã, tên, ngày, số, chứa chuỗi | Lọc dữ liệu | TB | — | ✅ (bài 06: ◐) |
| b16 | Sắp xếp theo tên, ngày, số lượng | Sắp xếp dữ liệu | TB | — | ✅ |
| b17 | Quy tắc phép tính | Công thức | ô | — | ✅ |
| b18 | Sao chép công thức | Công thức | ô | — | ✅ |
| b19 – b21 | Lưu ý, cách gọi, cú pháp hàm | Hàm (nhập môn) | ô | b19, b21 có sheet "Bài mẫu" | ✅ |
| **b22** | **SUM, dòng tổng cộng, sao chép công thức** | **Hàm toán học – thống kê** | ô | **`dap-an.xlsx` (sheet Bài 01)** | ✅ |
| b23 – b25 | COUNT, AVERAGE, MIN/MAX | Hàm toán học – thống kê | ô | — | ✅ |
| b26 | LEFT, RIGHT, MID | Hàm xử lý chuỗi | ô | — | ✅ |
| b27 | LEN, TRIM | Hàm xử lý chuỗi | ô | — | ◐ (phần nhận xét thì không) |

### Độ phủ so với phạm vi đề cương

| Nhóm kỹ năng trong đề cương | Có bài | Ghi chú |
|---|---|---|
| Tổ chức và nhập liệu | ✅ | b05 – b08 |
| Định dạng, trình bày | ✅ | b09 – b11, b14 |
| Thiết lập trang in | ✅ | b12, b13 (phần in PDF không kiểm chứng được) |
| Công thức | ✅ | b17, b18 |
| Hàm toán học – thống kê | ✅ | b22 – b25 |
| Hàm xử lý chuỗi | ✅ | b26, b27 |
| Sắp xếp, lọc | ✅ | b15, b16 |
| **Hàm logic (IF, AND, OR…)** | ❌ | Cần xin phần trung cấp |
| **Hàm ngày giờ** | ❌ | b10 chỉ định dạng ngày, chưa có hàm |
| **Hàm tìm kiếm – tham chiếu (VLOOKUP…)** | ❌ | Cần xin phần trung cấp |
| **Biểu đồ** | ❌ | Không bài nào có biểu đồ |

## 4. Việc còn lại của T1.1 (cần nhóm liên hệ trung tâm)

1. Xin **phần bài trung cấp**: IF, hàm ngày giờ, VLOOKUP/HLOOKUP, biểu đồ.
2. Xin **giáo trình** (PDF/DOCX) cho từng chương, vì RAG (T5.4) cần giáo trình để tra. Hiện chỉ b03, b04 có PDF.
3. Hỏi **quyền công khai** bài tập (repo là public).
4. Hỏi **phiên bản Office và ngôn ngữ giao diện**, **định dạng vùng Windows** trên máy phòng thực hành (liên quan phát hiện số 4).
5. Hỏi xem đáp án các bài còn lại có ở file khác không.

## 5. Hai bài chọn để viết kịch bản tay (T1.4, T1.5)

| Kịch bản | Bài | Sheet | Lý do chọn |
|---|---|---|---|
| [b09-du-lieu-dang-so.md](../kich-ban-tay/b09-du-lieu-dang-so.md) | b09 | `2. Bang_Ke_Ban_Hang` | Có checklist tiêu chí của giảng viên; kiểm chứng định dạng số (bị ảnh hưởng bởi phát hiện số 4, 5) |
| [b22-ham-tinh-tong.md](../kich-ban-tay/b22-ham-tinh-tong.md) | b22 | `Bài 01` | Nhóm kỹ năng khác (hàm + sao chép công thức); kiểm chứng công thức, địa chỉ tương đối, nhiều đáp án đúng |
