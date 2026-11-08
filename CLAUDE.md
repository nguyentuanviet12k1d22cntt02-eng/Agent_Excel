# Hướng dẫn cho trợ lý AI làm việc trong repo này

Trả lời người dùng bằng tiếng Việt. Repo là **public**.

## Bắt buộc đọc và tuân theo

- Cấu trúc, trách nhiệm thư mục, quy tắc phụ thuộc: `docs/quy-uoc/cau-truc-thu-muc.md`
- Quy tắc code: `docs/quy-uoc/quy-tac-code.md`
- Quy tắc đặt tên và bảng thuật ngữ code: `docs/quy-uoc/dat-ten.md`
- Git, commit, Pull Request: `docs/quy-uoc/lam-viec-nhom.md`
- Kế hoạch và mã task: `docs/quan-ly/ke-hoach-trien-khai.md` (làm task nào thì cập nhật cột TT của task đó)
- Thiết kế hệ thống (GĐ3): `docs/thiet-ke/README.md`; lược đồ kịch bản là hợp đồng giữa các app: `schemas/tutor-script/v1/`

## Điểm hay bị sai

- Không đọc, in hay commit `key.txt`, `.env`, `nckh/`, `Cơ bản/`, `samples/_local/`.
- Desktop không gọi LLM. `packages/excel_core` không import từ `apps/` và không import `win32com` ở mức module.
- Code tiếng Anh; comment, docstring, tài liệu, commit tiếng Việt có dấu. Tên file/thư mục ASCII.
- Commit theo dạng `T2.1: <việc đã làm>`, làm trên nhánh `feature/<mã-task>-<mô-tả>`, không commit thẳng vào `main`.

## Lệnh

```powershell
py -3.14 -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\ruff format .
.venv\Scripts\ruff check .
.venv\Scripts\pytest
# excel_core: so sánh đề/đáp án, kiểm kịch bản 3 tầng
.venv\Scripts\python -m excel_core.diff de.xlsx dap-an.xlsx
.venv\Scripts\python -m excel_core.script kich-ban.json --starter de.xlsx --solution dap-an.xlsx
# Web (apps/web, Node 22): sửa openapi.yaml thì chạy gen:api và commit src/api/schema.d.ts
cd apps\web; npm install; npm run dev; npm test; npm run lint; npm run format; npm run gen:api
```
