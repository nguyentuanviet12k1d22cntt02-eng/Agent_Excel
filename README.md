# Gia sư AI hướng dẫn thực hành Excel

Đề tài nghiên cứu khoa học sinh viên năm học 2026–2027, Viện Công nghệ số, Trường Đại học Thủ Dầu Một.
*Xây dựng gia sư AI hướng dẫn thực hành Excel dựa trên thao tác của người học.*

## Hệ thống gồm 3 phần

| Phần | Thư mục | Công nghệ | Vai trò |
|---|---|---|---|
| **Web quản trị** | [`apps/web`](apps/web) | React + TypeScript | Giảng viên tải giáo trình và bài tập. AI sinh kịch bản hướng dẫn; giảng viên xem, sửa, duyệt, phát hành. |
| **Backend** | [`apps/backend`](apps/backend) | FastAPI | Học liệu, RAG giáo trình, tác tử sinh kịch bản, phiên bản kịch bản, tiến độ, nhật ký. |
| **Desktop gia sư** | [`apps/desktop`](apps/desktop) | Python + PyQt6 (Windows) | Theo dõi thao tác trên Excel, kiểm chứng từng bước theo kịch bản, hiện gợi ý khi bắt được tín hiệu. Không gọi AI. |

Thư viện dùng chung: [`packages/excel_core`](packages/excel_core). Lược đồ kịch bản: [`schemas/`](schemas).

## Cấu trúc repo

```
apps/            Ứng dụng: backend/, desktop/, web/
packages/        Thư viện dùng chung: excel_core/
schemas/         JSON Schema của kịch bản hướng dẫn
samples/         Bộ bài tập mẫu đã chuẩn hóa
spikes/          Code làm thử kỹ thuật
scripts/         Công cụ quản lý repo
docs/            Tài liệu (kế hoạch, quy ước, thiết kế, báo cáo)
```

Chi tiết, trách nhiệm từng thư mục và quy tắc phụ thuộc: [docs/quy-uoc/cau-truc-thu-muc.md](docs/quy-uoc/cau-truc-thu-muc.md).

## Yêu cầu môi trường

- Windows 10/11, Microsoft Excel 2016 trở lên (khuyến nghị Microsoft 365)
- **Python 3.14** (xem `.python-version`)
- Node.js 22 LTS (cho `apps/web`)
- Git, VS Code (mở repo sẽ được gợi ý cài các extension cần thiết)

## Bắt đầu

```powershell
git clone https://github.com/nguyentuanviet12k1d22cntt02-eng/Agent_Excel.git
cd Agent_Excel

# Một môi trường Python chung, cài mọi project ở dạng editable
py -3.14 -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt

# Kiểm tra
.venv\Scripts\ruff check .
.venv\Scripts\pytest

# Kiểm tra đóng gói .exe trên máy mình (mã thoát 0 là đạt)
powershell -ExecutionPolicy Bypass -File spikes\t0-3-hello-exe\build.ps1
```

API key đặt trong `apps/backend/.env` theo mẫu [.env.example](.env.example). **Không commit `.env`.**

## Đọc trước khi đóng góp

1. [Quy ước làm việc nhóm](docs/quy-uoc/lam-viec-nhom.md): nhánh, commit, Pull Request, review
2. [Quy tắc code](docs/quy-uoc/quy-tac-code.md)
3. [Quy tắc đặt tên](docs/quy-uoc/dat-ten.md)
4. [Kế hoạch triển khai](docs/quan-ly/ke-hoach-trien-khai.md): chọn task, cập nhật cột TT

Mục lục toàn bộ tài liệu: [docs/README.md](docs/README.md).

## Nhóm thực hiện

Nguyễn Tuấn Việt (trưởng nhóm) · Diệp Đại Lê Hoài · Nguyễn Văn Linh · Nguyễn Ngọc Hòa
GVHD: ThS. Ngô Thị Ngọc Dịu
