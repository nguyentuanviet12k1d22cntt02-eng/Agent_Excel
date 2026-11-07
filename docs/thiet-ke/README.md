# Thiết kế hệ thống (GĐ3) — bản v1

Bộ tài liệu này là **Chương 3 của báo cáo** ("Khảo sát, phân tích yêu cầu và thiết kế hệ thống") và là đầu vào để bắt đầu code từ GĐ4. Trạng thái: **chờ GVHD rà soát** ([biên bản](../quan-ly/bien-ban-ra-soat-thiet-ke.md)). Sau khi chốt sẽ gắn tag `design-v1` trên git.

## Thứ tự đọc

| # | Tài liệu | Task | Mục báo cáo | Nội dung |
|---|---|---|---|---|
| 1 | [dac-ta-yeu-cau.md](dac-ta-yeu-cau.md) | T3.1 | 3.3 | Tác nhân, ca sử dụng, 31 yêu cầu chức năng, 15 yêu cầu phi chức năng có ngưỡng đo |
| 2 | [kien-truc.md](kien-truc.md) | T3.5 | 3.4 | Sơ đồ thành phần, công nghệ, triển khai, các luồng trong Desktop, 2 sơ đồ tuần tự, 7 quyết định kiến trúc |
| 3 | [luoc-do-kich-ban.md](luoc-do-kich-ban.md) | T3.2 | 3.5 | Lược đồ kịch bản JSON v1, 3 tầng kiểm, phiên bản và phát hành |
| 4 | [danh-muc-dieu-kien.md](danh-muc-dieu-kien.md) | T1.6 | 3.2, 3.5 | 25 loại điều kiện kiểm chứng, 8 loại tín hiệu |
| 5 | [luat-goi-y.md](luat-goi-y.md) | T3.4 | 3.6 | Cơ sở lý thuyết, 11 luật tăng/giảm cấp gợi ý, giảm dần trợ giúp theo kỹ năng |
| 6 | [snapshot.md](snapshot.md) | T3.3 | 3.4, 4.4 | Mô hình snapshot workbook dùng chung, chuẩn hóa openpyxl/COM, sự kiện quan sát |
| 7 | [csdl.md](csdl.md) | T3.6 | 3.4 | ERD 15 bảng, ràng buộc, quyền riêng tư |
| 8 | [openapi.yaml](openapi.yaml) | T3.7 | 3.4 | REST API: 31 đường dẫn, 39 thao tác (OpenAPI 3.1) |

**File máy đọc được** (có test trong CI): [`schemas/tutor-script/v1/`](../../schemas/tutor-script/v1/) (lược đồ + 2 ví dụ), [openapi.yaml](openapi.yaml).

## Những gì thiết kế dựa vào

- Đề cương (mục tiêu, phạm vi 11.2, cách tiếp cận 11.3, nội dung chương 3).
- GĐ1: 25 bài của trung tâm, ma trận kỹ năng, 2 kịch bản viết tay.
- GĐ2: thử kỹ thuật trên Excel thật ([báo cáo khả thi](../task/t2-7-bao-cao-spike.md)), 10 quyết định thiết kế.
