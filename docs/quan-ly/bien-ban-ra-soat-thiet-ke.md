# Biên bản rà soát thiết kế v1 (T3.8)

**Thời gian:** …/…/2026 · **Hình thức:** họp trực tiếp / trực tuyến
**Thành phần:** GVHD ThS. Ngô Thị Ngọc Dịu; nhóm: Nguyễn Tuấn Việt (trưởng nhóm), Nguyễn Văn Linh, Diệp Đại Lê Hoài, Nguyễn Ngọc Hòa
**Tài liệu rà soát:** [docs/thiet-ke/](../thiet-ke/README.md) (8 tài liệu), lược đồ [schemas/tutor-script/v1/](../../schemas/tutor-script/v1/)

> Gửi GVHD trước buổi họp ít nhất 2 ngày. Trong buổi họp đi lần lượt mục 1 (câu hỏi cần quyết định), rồi mục 2 (góp ý chung). Ghi quyết định vào cột "Kết luận".

## 1. Câu hỏi cần GVHD quyết định

| # | Câu hỏi | Phương án nhóm đề xuất | Tài liệu | Kết luận |
|---|---|---|---|---|
| Q1 | b09: cột Thành tiền có phải bước bắt buộc (hướng dẫn trong bài không nhắc, nhưng tiêu chí 2 có)? | Có, là bước 4 | [kịch bản b09](../kich-ban-tay/b09-du-lieu-dang-so.md) | |
| Q2 | b09: Đơn giá dùng `0.00` (không dấu nghìn) có được chấp nhận? | Có, đề chỉ yêu cầu 2 chữ số thập phân | như trên | |
| Q3 | b22: `=SUM(C9,D9,E9)` có được chấp nhận? | Có, vẫn dùng SUM | [kịch bản b22](../kich-ban-tay/b22-ham-tinh-tong.md) | |
| Q4 | b22 sheet Bài 02: dòng TỔNG CỘNG dùng `=SUM(C12,C16,C20)` hay `=C12+C16+C20`? | Chờ thầy cô | như trên | |
| Q5 | Các ngưỡng của luật gợi ý (dừng 60 s thì nhắc, sai 2 lần thì tăng cấp, giãn cách 20 s) có hợp lý với học viên trung tâm? | Dùng làm giá trị ban đầu, chỉnh sau thử nghiệm nhỏ (T9.1) | [luat-goi-y.md](../thiet-ke/luat-goi-y.md) mục 3 | |
| Q6 | Cấp 4 (hướng dẫn chi tiết) chỉ hiện khi học viên xin hoặc đồng ý, không tự hiện. Đồng ý? | Đồng ý (không làm thay) | luat-goi-y.md mục 1, R9 | |
| Q7 | Có cho học viên tắt chế độ gia sư tự lên tiếng không? | Không, trong đợt thực nghiệm dùng một chế độ thống nhất | luat-goi-y.md mục 9 | |
| Q8 | Nhóm đối chứng dùng Desktop ở chế độ chỉ ghi nhật ký (không gợi ý), hay không dùng Desktop? | Dùng chế độ chỉ ghi nhật ký, để đo thời gian, số lỗi cùng một cách | [dac-ta-yeu-cau.md](../thiet-ke/dac-ta-yeu-cau.md) FR-D15 | |
| Q9 | Các ngưỡng phi chức năng: kiểm chứng ≤ 300 ms, nhận diện đúng ≥ 95%, báo sai ≤ 5%, SUS ≥ 68 có phù hợp để đưa vào báo cáo? | Như đề xuất | dac-ta-yeu-cau.md mục 4 | |
| Q10 | RAG bắt đầu bằng tìm toàn văn, thêm embedding sau khi chọn nhà cung cấp. Có cần embedding ngay cho tính "AI" của đề tài? | Bắt đầu toàn văn; so sánh hai cách ở T5.8 làm kết quả nghiên cứu | [kien-truc.md](../thiet-ke/kien-truc.md) A7 | |
| Q11 | Bộ tiêu chí kiểm tra và quy tắc phản hồi của GĐ1 khảo sát (mục tiêu cụ thể 1 của đề cương) đã có chưa, để đối chiếu với danh mục điều kiện? | Nếu chưa, dùng danh mục điều kiện + 2 kịch bản tay làm bản đầu | [danh-muc-dieu-kien.md](../thiet-ke/danh-muc-dieu-kien.md) | |

## 2. Góp ý chung

| # | Tài liệu / mục | Góp ý | Người xử lý | Hạn | Đã xử lý |
|---|---|---|---|---|---|
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |

## 3. Kết luận

- [ ] Chốt thiết kế v1, gắn tag `design-v1` (trưởng nhóm thực hiện sau khi xử lý xong mục 2).
- [ ] Cần sửa và rà soát lại vào ngày: …/…/2026

**Xác nhận của GVHD:** ……………………
