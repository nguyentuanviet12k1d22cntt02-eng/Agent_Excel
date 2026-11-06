# Quy ước làm việc của nhóm

Áp dụng cho cả 4 thành viên. Có thay đổi thì sửa file này qua Pull Request.

## 1. Nhánh (branch)

| Nhánh | Dùng cho |
|---|---|
| `main` | Luôn chạy được. **Không** commit thẳng, chỉ nhận code qua Pull Request. |
| `feature/<mã-task>-<mô-tả>` | Làm một task trong kế hoạch. Ví dụ: `feature/T2.1-com-doc-du-lieu` |
| `fix/<mô-tả>` | Sửa lỗi không gắn với task nào. Ví dụ: `fix/overlay-lech-dpi-150` |

- Mô tả viết thường, không dấu, nối bằng dấu `-`.
- Mỗi nhánh chỉ làm **một** task. Làm xong và merge thì xóa nhánh.
- Trước khi mở Pull Request, cập nhật nhánh từ `main`: `git pull origin main`.

## 2. Commit

Định dạng: `<mã-task>: <việc đã làm>`, viết tiếng Việt có dấu, ngắn gọn.

```
T2.1: đọc giá trị và công thức qua Excel COM
T2.1: đo thời gian đọc 1.000 ô
fix: overlay lệch vị trí khi DPI 150%
docs: cập nhật trạng thái GĐ2
```

- Mỗi commit là một thay đổi có ý nghĩa, không gộp nhiều việc không liên quan.
- Không commit code đang lỗi cú pháp hoặc không chạy được lên nhánh sẽ mở Pull Request.

## 3. Pull Request (PR) và review

1. Mở PR từ nhánh task vào `main`. Tiêu đề: `[T2.1] Đọc dữ liệu qua Excel COM`.
2. Mô tả PR gồm: **đã làm gì**, **cách kiểm tra** (lệnh chạy, file mẫu dùng để thử), **ảnh chụp** nếu có giao diện.
3. Cần **ít nhất 1 người duyệt**. Người duyệt phải tải nhánh về và chạy thử, không chỉ đọc code.
4. Review chéo theo cặp: Việt ↔ Linh, Hoài ↔ Hòa. Thay đổi lược đồ JSON (`shared/schema/`) cần 1 người bên Backend **và** 1 người bên Desktop duyệt.
5. Merge kiểu **Squash and merge** để lịch sử `main` gọn, mỗi task một commit.

## 4. Cập nhật kế hoạch

Cột **TT** trong [KE_HOACH_TRIEN_KHAI.md](KE_HOACH_TRIEN_KHAI.md):

- Bắt đầu task: đổi ⬜ → 🔄 (commit `docs: bắt đầu T2.1`).
- PR được merge: đổi 🔄 → ✅ **ngay trong PR đó**.
- Task bị chặn hoặc trễ quá 3 ngày: báo trong nhóm chat và ghi lý do vào issue của task.

## 5. Ngôn ngữ và phong cách code

| Thành phần | Quy ước |
|---|---|
| Tên biến, hàm, lớp, file code | Tiếng Anh: `read_range_values()`, `TeachingAgent` |
| Comment, docstring, tài liệu, commit, PR | Tiếng Việt có dấu |
| Chữ hiển thị cho người dùng | Tiếng Việt có dấu |
| Python | Định dạng và kiểm tra bằng `ruff` (cấu hình ở `ruff.toml`), có type hint cho hàm public |
| JavaScript/TypeScript | Prettier + ESLint (thiết lập ở T6.1) |

Chạy trước khi commit Python:

```powershell
ruff format .
ruff check . --fix
```

## 6. Môi trường

- **Python:** đúng phiên bản trong file `.python-version` ở gốc repo. Mỗi phần một môi trường ảo: `backend\.venv`, `desktop\.venv`.
- **Node.js:** 22 LTS (cho `web/`).
- Thêm thư viện mới: ghi vào `requirements.txt` của phần đó, kèm số phiên bản (`==`), và nêu lý do trong PR.

## 7. Bí mật và dữ liệu

- **Không bao giờ commit API key, mật khẩu.** Đặt trong file `.env` (đã nằm trong `.gitignore`), mẫu ở `.env.example`.
- Nếu lỡ commit key: báo ngay cho trưởng nhóm và **thu hồi/đổi key** trên trang nhà cung cấp. Xóa commit là chưa đủ vì key đã nằm trong lịch sử git.
- Không commit: môi trường ảo, `build/`, `dist/`, file `.exe`, file tạm `~$*.xlsx`, dữ liệu cá nhân của học viên.
- Bài tập mẫu đưa vào `samples/` theo quy ước trong [samples/README.md](../samples/README.md), đã xóa thông tin cá nhân.

## 8. Nhịp làm việc

- **Đầu tuần (15 phút):** mỗi người nói task tuần trước đã xong, task tuần này, việc đang bị chặn.
- **Cuối tuần:** trưởng nhóm rà cột TT trong kế hoạch, báo GVHD nếu có giai đoạn có nguy cơ trễ.
