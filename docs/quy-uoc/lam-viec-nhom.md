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
4. Review chéo theo cặp: Việt ↔ Linh, Hoài ↔ Hòa. Thay đổi lược đồ JSON (`schemas/`) cần 1 người bên Backend **và** 1 người bên Desktop duyệt.
5. Merge kiểu **Squash and merge** để lịch sử `main` gọn, mỗi task một commit.

## 4. Cập nhật kế hoạch

Cột **TT** trong [kế hoạch triển khai](../quan-ly/ke-hoach-trien-khai.md):

- Bắt đầu task: đổi ⬜ → 🔄 (commit `docs: bắt đầu T2.1`).
- PR được merge: đổi 🔄 → ✅ **ngay trong PR đó**.
- Task bị chặn hoặc trễ quá 3 ngày: báo trong nhóm chat và ghi lý do vào issue của task.

## 5. Ngôn ngữ, code và đặt tên

| Thành phần | Ngôn ngữ |
|---|---|
| Tên biến, hàm, lớp, file code | Tiếng Anh |
| Comment, docstring, tài liệu, commit, PR | Tiếng Việt có dấu |
| Chữ hiển thị cho người dùng | Tiếng Việt có dấu |

Chi tiết xem [quy tắc code](quy-tac-code.md) và [quy tắc đặt tên](dat-ten.md). CI trên GitHub tự kiểm tra định dạng, lint và test cho mỗi Pull Request; **CI báo đỏ thì không merge**.

Chạy trước khi commit:

```powershell
ruff format .
ruff check . --fix
pytest
```

## 6. Môi trường

- **Python:** đúng phiên bản trong file `.python-version` ở gốc repo. Một môi trường ảo chung `.venv` ở gốc repo (xem [cấu trúc thư mục](cau-truc-thu-muc.md#5-môi-trường-phát-triển)).
- **Node.js:** 22 LTS (cho `apps/web/`).
- Thêm thư viện mới: ghi vào `pyproject.toml` của project đó, kèm số phiên bản (`==`), và nêu lý do trong PR.

## 7. Bí mật và dữ liệu

- **Không bao giờ commit API key, mật khẩu.** Đặt trong file `.env` (đã nằm trong `.gitignore`), mẫu ở `.env.example`.
- Nếu lỡ commit key: báo ngay cho trưởng nhóm và **thu hồi/đổi key** trên trang nhà cung cấp. Xóa commit là chưa đủ vì key đã nằm trong lịch sử git.
- Không commit: môi trường ảo, `build/`, `dist/`, file `.exe`, file tạm `~$*.xlsx`, dữ liệu cá nhân của học viên.
- **Repo là public.** Bài tập mẫu đưa vào `samples/` theo [samples/README.md](../../samples/README.md): chỉ bài được phép công khai, đã xóa thông tin cá nhân. Bài chưa được phép để trong `samples/_local/`.

## 8. Nhịp làm việc

- **Đầu tuần (15 phút):** mỗi người nói task tuần trước đã xong, task tuần này, việc đang bị chặn.
- **Cuối tuần:** trưởng nhóm rà cột TT trong kế hoạch, báo GVHD nếu có giai đoạn có nguy cơ trễ.
