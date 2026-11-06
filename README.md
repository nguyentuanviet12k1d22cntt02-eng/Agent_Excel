# Gia sư AI hướng dẫn thực hành Excel

Đề tài nghiên cứu khoa học sinh viên năm học 2026–2027, Viện Công nghệ số, Trường Đại học Thủ Dầu Một.
*Xây dựng gia sư AI hướng dẫn thực hành Excel dựa trên thao tác của người học.*

## Hệ thống gồm 3 phần

| Phần | Công nghệ | Vai trò |
|---|---|---|
| **Web quản trị** | React | Giảng viên tải giáo trình và bài tập lên. AI sinh kịch bản hướng dẫn, giảng viên xem, sửa, duyệt rồi phát hành. |
| **Backend** | FastAPI | Quản lý học liệu, RAG giáo trình, tác tử sinh kịch bản, phiên bản kịch bản, tiến độ và nhật ký. |
| **Desktop gia sư** | Python + PyQt6 (Windows) | Theo dõi thao tác của học viên trên Excel, kiểm chứng từng bước theo kịch bản đã duyệt, hiện gợi ý khi bắt được tín hiệu. Không gọi AI. |

## Cấu trúc repo

```
backend/         FastAPI: người dùng, học liệu, RAG, sinh kịch bản, tiến độ
web/             React (Vite + TypeScript): Web quản trị
desktop/         PyQt6: bộ giám sát, Teaching Agent, cửa sổ gia sư, overlay
excel_core/      Dùng chung: snapshot workbook, so sánh file, kiểm tra điều kiện
shared/schema/   JSON Schema của kịch bản hướng dẫn
samples/         Bộ bài tập mẫu đã chuẩn hóa
spikes/          Script làm thử kỹ thuật
scripts/         Công cụ quản lý repo (tạo issue…)
docs/            Kế hoạch, quy ước, đặc tả, thiết kế
```

## Yêu cầu môi trường

- Windows 10/11, Microsoft Excel 2016 trở lên (khuyến nghị Microsoft 365)
- **Python 3.14** (xem `.python-version`)
- Node.js 22 LTS (cho `web/`)
- Git

## Bắt đầu

```powershell
git clone <địa-chỉ-repo>
cd Agent_Excel

# Desktop
py -3.14 -m venv desktop\.venv
desktop\.venv\Scripts\python -m pip install -r desktop\requirements.txt -r requirements-dev.txt

# Backend
py -3.14 -m venv backend\.venv
backend\.venv\Scripts\python -m pip install -r backend\requirements.txt -r requirements-dev.txt

# Kiểm tra môi trường: build và chạy app hello (mã thoát 0 là đạt)
powershell -ExecutionPolicy Bypass -File spikes\T0.3_hello_exe\build.ps1
```

API key đặt trong file `.env` theo mẫu [.env.example](.env.example). **Không commit `.env`.**

## Tài liệu

- [Kế hoạch triển khai](docs/KE_HOACH_TRIEN_KHAI.md): các giai đoạn, task, tiến độ
- [Quy ước làm việc](docs/QUY_UOC.md): nhánh, commit, Pull Request, phong cách code
- [T0.4: Chọn LLM](docs/T0.4_chon_LLM.md) · [T0.5: Rà soát đầu ra GĐ1](docs/T0.5_ra_soat_GD1.md)

## Nhóm thực hiện

Nguyễn Tuấn Việt (trưởng nhóm) · Diệp Đại Lê Hoài · Nguyễn Văn Linh · Nguyễn Ngọc Hòa
GVHD: ThS. Ngô Thị Ngọc Dịu
