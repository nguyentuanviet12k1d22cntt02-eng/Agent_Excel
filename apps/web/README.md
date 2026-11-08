# apps/web — Web quản trị (React + Vite + TypeScript)

Dành cho giảng viên và quản trị viên: tải học liệu, yêu cầu AI sinh kịch bản, xem/sửa, duyệt, phát hành,
theo dõi tiến độ học viên. Học viên không dùng Web (dùng ứng dụng Desktop).

- **Yêu cầu:** Node.js 22 LTS (≥ 22.22.2)
- **Gọi Backend qua:** `/api/v1` cùng máy chủ. Khi chạy dev, Vite chuyển tiếp `/api` sang Backend
  (mặc định `http://127.0.0.1:8000`, đổi bằng biến môi trường `TUTOR_BACKEND_URL`). Khi build để triển khai
  mà Web và Backend khác máy chủ thì đặt `VITE_API_BASE_URL`, ví dụ `https://api.trungtam.vn/api/v1`.

## Chạy thử trên máy

```powershell
# Cửa sổ 1: Backend (xem apps/backend/README.md: migrate, create-admin)
.venv\Scripts\python -m tutor_backend serve

# Cửa sổ 2: Web
cd apps\web
npm install          # lần đầu, hoặc khi package.json đổi
npm run dev          # mở http://localhost:5173
```

## Các trang

| Trang                     | Ai dùng              | Việc                                                                                                   |
| ------------------------- | -------------------- | ------------------------------------------------------------------------------------------------------ |
| Bài tập `/exercises`      | Giảng viên           | Tạo bài (file đề, đáp án, sheet, đề bài, giáo trình), sinh kịch bản bằng AI, lịch sử bản, giao cho lớp |
| Trình sửa `/scripts/{id}` | Giảng viên           | Xem, sửa từng bước, kiểm lược đồ ngay, lưới mô phỏng trang tính, gửi duyệt, duyệt, phát hành           |
| Giáo trình `/textbooks`   | Giảng viên           | Tải PDF/DOCX, theo dõi lập chỉ mục, thử tìm đoạn trích                                                 |
| Lớp học `/classes`        | Quản trị, giảng viên | Học viên và nhóm thực nghiệm / đối chứng, bài đã giao                                                  |
| Tài khoản `/users`        | Quản trị             | Thêm tài khoản, nhập CSV                                                                               |

Tài khoản quản trị đầu tiên vẫn tạo bằng dòng lệnh (`python -m tutor_backend create-admin`), các tài khoản sau
tạo trên Web.

## Lệnh

| Lệnh                              | Việc                                                                           |
| --------------------------------- | ------------------------------------------------------------------------------ |
| `npm run dev`                     | Chạy dev, tự tải lại khi sửa code                                              |
| `npm run build`                   | Kiểm kiểu rồi build ra `dist/` (file tĩnh, đặt sau reverse proxy cùng Backend) |
| `npm test`                        | Chạy test (Vitest + Testing Library, Backend giả trong `src/test/fakeApi.ts`)  |
| `npm run lint` · `npm run format` | ESLint · Prettier                                                              |
| `npm run typecheck`               | Kiểm kiểu TypeScript                                                           |
| `npm run gen:api`                 | Sinh lại `src/api/schema.d.ts` từ `docs/thiet-ke/openapi.yaml`                 |
| `npm run check:api`               | Báo lỗi nếu `schema.d.ts` cũ hơn đặc tả (CI chạy)                              |

**Kiểu dữ liệu API không gõ tay** (quy tắc code mục 3): sửa `docs/thiet-ke/openapi.yaml` (và Backend), chạy
`npm run gen:api`, commit cả hai. Tên ngắn cho các kiểu hay dùng ở `src/api/types.ts`. Lược đồ kịch bản đọc
thẳng từ `schemas/tutor-script/v1/` (bí danh `@schemas`).

## Bố cục

```
src/
├─ app/           định tuyến, provider, khung trang, giao diện chung (styles.css)
├─ api/           client gọi Backend (tự gắn và làm mới token), lỗi problem+json, kiểu sinh từ OpenAPI
├─ features/      mỗi tính năng một thư mục: auth/, materials/, script-editor/, publishing/ …
├─ components/    thành phần giao diện dùng chung
├─ lib/           tiện ích dùng chung
└─ test/          Backend giả và hàm dựng ứng dụng cho test
```

Đăng nhập: access token chỉ giữ trong bộ nhớ; refresh token lưu `localStorage` để mở lại trình duyệt không
phải đăng nhập lại. Gặp 401 thì client tự làm mới token một lần rồi gửi lại; hết hạn hẳn thì về trang đăng nhập.
