# backend — FastAPI

Quản lý người dùng, học liệu, RAG giáo trình, tác tử sinh kịch bản, vòng đời kịch bản, tiến độ và nhật ký.

**Được xây dựng ở:** GĐ5 (T5.1 – T5.8) trong [kế hoạch](../docs/KE_HOACH_TRIEN_KHAI.md).

## Cài môi trường

```powershell
py -3.14 -m venv backend\.venv
backend\.venv\Scripts\python -m pip install -r backend\requirements.txt -r requirements-dev.txt
```

API key và cấu hình đặt trong `backend/.env` (sao chép từ `.env.example` ở gốc repo). Không commit file `.env`.
