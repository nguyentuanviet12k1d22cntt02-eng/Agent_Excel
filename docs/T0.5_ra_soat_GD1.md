# T0.5 — Rà soát đầu ra Giai đoạn 1 (tháng 10/2026)

**Ngày rà soát:** 07/11/2026 · **Người lập:** nhóm (bản nháp do trưởng nhóm chuẩn bị, cần cả nhóm xác nhận cột "Trạng thái")

## 1. Đầu ra GĐ1 đã cam kết trong đề cương

| # | Đầu ra | Trạng thái | Ghi chú / việc cần làm |
|---|---|---|---|
| 1 | Báo cáo tổng quan tình hình nghiên cứu | ❓ nhóm xác nhận | Dùng lại mục 10 của đề cương làm khung; bổ sung 2 tài liệu còn thiếu ở mục 3 |
| 2 | Phiếu khảo sát học viên (trực tuyến) | ❓ | |
| 3 | Câu hỏi phỏng vấn bán cấu trúc cho giảng viên | ❓ | |
| 4 | Báo cáo kết quả khảo sát (lỗi thao tác phổ biến, khó khăn khi phân tích đề, chọn công cụ) | ❓ | Có thể bổ sung bằng phân tích bài làm thực tế của học viên |
| 5 | **Bộ tiêu chí kiểm tra và quy tắc phản hồi** | ❓ | **Quan trọng nhất**: là đầu vào của T1.6 và T3.2. Nếu chưa có thì phải xong trước 22/11 |

Phần còn thiếu ghi lịch bổ sung vào bảng dưới, rồi tạo issue riêng:

| Việc bổ sung | Người làm | Hạn |
|---|---|---|
| | | |

## 2. Tài liệu hiện có trong máy

| Tài liệu | Nội dung | Dùng cho |
|---|---|---|
| `nckh/Nguyễn Tuấn Việt_...docx` | Đề cương đề tài | Mọi giai đoạn |
| `nckh/nckh.pdf` | Bài báo tham khảo [2]: Aguirre Reid và cộng sự, *Improving feedback from automated reviews of student spreadsheets* | Tổng quan; tham khảo 7 cấp phản hồi của họ khi thiết kế 4 cấp gợi ý (T3.4) |
| `Cơ bản/` (25 file) | Bài học và bài tập Excel phần cơ bản của trung tâm | Đầu vào T1.1 – T1.3 (xem mục 4) |

## 3. Lỗi cần sửa trong đề cương / báo cáo tổng quan

1. **Thiếu tài liệu tham khảo.** Mục 10 nhắc "Barowy và cộng sự, Hofer và Wotawa" nhưng danh mục không có. Đề xuất bổ sung (lấy từ danh mục tham khảo của bài báo [2], **cần kiểm tra lại DOI trước khi dùng**):
   - D. W. Barowy, D. Gochev, and E. D. Berger, "CheckCell: Data debugging for spreadsheets," in *Proc. ACM Int. Conf. Object Oriented Programming Systems Languages & Applications (OOPSLA)*, 2014, pp. 507–523, doi: 10.1145/2660193.2660207.
   - B. Hofer and F. Wotawa, "Why does my spreadsheet compute wrong values?," in *Proc. IEEE 25th Int. Symp. Software Reliability Engineering (ISSRE)*, 2014, pp. 112–121, doi: 10.1109/ISSRE.2014.23.
2. **Thứ tự đánh số IEEE.** Số thứ tự phải theo thứ tự trích dẫn lần đầu. Hiện tại [10] xuất hiện ở mục 9 (Tính cấp thiết), trước [6]–[9]. Khi bổ sung 2 tài liệu trên, đánh số lại toàn bộ.

## 4. Kiểm kê sơ bộ thư mục `Cơ bản/`

| Bài | Chủ đề | Nhóm kỹ năng (theo phạm vi đề cương) | Có đáp án mẫu trong file? |
|---|---|---|---|
| 03, 04 | Khởi động Excel, thao tác với sheet (PDF) | Làm quen | — (tài liệu lý thuyết) |
| 05 – 07 | Thao tác với dòng, cột, địa chỉ ô | Tổ chức và nhập liệu | Không |
| 08 – 11 | Chuẩn bị nhập liệu, dữ liệu số, ngày tháng, định dạng khác | Nhập liệu, định dạng | **Có** — sheet `Dap_An_Mau` |
| 12, 13 | Trang in, hướng giấy, khổ giấy, đánh số trang | Thiết lập trang in | Không |
| 14 | Tạo bảng tính (báo giá, phiếu nhập kho, phiếu thu, chấm công) | Định dạng, trình bày | Không |
| 15 | Lọc dữ liệu | Lọc | Không |
| 16 | Sắp xếp dữ liệu | Sắp xếp | Không |
| 17, 18 | Quy tắc phép tính, sao chép công thức | Công thức | Không |
| 19 – 21 | Lưu ý, cách gọi hàm, cú pháp hàm | Hàm (nhập môn) | Bài 19, 21 **có** sheet `Bài mẫu` |
| 22 – 25 | SUM, COUNT, AVERAGE, MAX/MIN | Hàm toán học – thống kê | Không |
| 26, 27 | LEFT/RIGHT/MID, LEN/TRIM | Hàm xử lý chuỗi | Không |

### Phát hiện ảnh hưởng đến thiết kế

1. **Phần lớn bài không có đáp án mẫu.** Chỉ 6/23 file Excel có sheet đáp án. Kế hoạch đang giả định giảng viên cung cấp *file đề* + *file kết quả mẫu* tách riêng. Cần hỏi trung tâm: đáp án các bài còn lại có ở file khác không? Nếu không, nhóm phải tự làm đáp án (và nhờ giảng viên duyệt) cho các bài chọn làm mẫu.
2. **Đề và đáp án có thể nằm chung một file**, ở các sheet khác nhau (`Thuc_Hanh_Tung_Buoc`, `Dap_An_Mau`). Khi thiết kế upload trên Web quản trị (T3.1) và bộ so sánh (T4.3), cần hỗ trợ cả trường hợp "chọn sheet đề và sheet đáp án trong cùng một file".
3. **Còn thiếu nhóm kỹ năng** so với phạm vi đề cương: hàm logic (IF…), hàm ngày giờ, hàm tìm kiếm – tham chiếu (VLOOKUP…), biểu đồ. Cần xin thêm phần bài học trung cấp ở trung tâm (T1.1).
4. Một số file có sheet `GPT cache` (1 ô), có thể do add-in. Khi chuẩn hóa vào `samples/` (T1.2) thì bỏ sheet này.
