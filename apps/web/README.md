# apps/web — Web quản trị (React + Vite + TypeScript)

Dành cho giảng viên: tải học liệu, yêu cầu AI sinh kịch bản, xem/sửa, duyệt, phát hành, theo dõi tiến độ học viên.

- **Được xây dựng ở:** GĐ6 (T6.1 – T6.6). Khung dự án Vite tạo ở T6.1
- **Yêu cầu:** Node.js 22 LTS
- **Bố cục dự kiến** (theo [quy tắc code](../../docs/quy-uoc/quy-tac-code.md#3-typescript--react-appsweb)):

```
src/
├─ app/           định tuyến, provider, layout chung
├─ features/      mỗi tính năng một thư mục: materials/, script-editor/, publishing/, progress/
├─ components/    thành phần giao diện dùng chung
├─ api/           client gọi Backend + kiểu dữ liệu sinh từ OpenAPI
└─ lib/           tiện ích dùng chung
```
