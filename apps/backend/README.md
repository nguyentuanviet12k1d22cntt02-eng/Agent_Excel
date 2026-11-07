# apps/backend — Backend FastAPI

Quản lý người dùng, học liệu, RAG giáo trình, tác tử sinh kịch bản, vòng đời kịch bản, tiến độ và nhật ký.

- **Package:** `tutor_backend` (trong `src/`). Cấu trúc và trách nhiệm từng thư mục: [cấu trúc thư mục](../../docs/quy-uoc/cau-truc-thu-muc.md#appsbackendsrctutor_backend)
- **Thiết kế:** [kiến trúc](../../docs/thiet-ke/kien-truc.md), [CSDL](../../docs/thiet-ke/csdl.md), [API](../../docs/thiet-ke/openapi.yaml)
- **Được xây dựng ở:** GĐ5 (T5.1 – T5.8) trong [kế hoạch](../../docs/quan-ly/ke-hoach-trien-khai.md)
- **Cài môi trường:** dùng chung `.venv` ở gốc repo, xem [README gốc](../../README.md#bắt-đầu)
- **Cấu hình:** sao chép `.env.example` ở gốc repo thành `apps/backend/.env` rồi điền giá trị. Không commit file `.env`.

## Chạy khi phát triển

```powershell
.venv\Scripts\python -m tutor_backend migrate     # tạo/nâng CSDL (mặc định SQLite apps/backend/storage/dev.db)
.venv\Scripts\python -m tutor_backend serve       # http://127.0.0.1:8000/docs
```

CSDL: **PostgreSQL** khi triển khai (`DATABASE_URL=postgresql+psycopg://...`), **SQLite** khi phát triển và test. Model chỉ dùng kiểu có ở cả hai (JSON tự thành JSONB trên PostgreSQL); CI chạy migration và test trên cả SQLite (Windows) và PostgreSQL 16 (Ubuntu).

## Migration

Mỗi thay đổi model đi kèm một migration Alembic trong `migrations/versions/` (tên file ASCII):

```powershell
.venv\Scripts\alembic -c apps\backend\alembic.ini revision --autogenerate -m "them cot x"
```

Rà lại file sinh ra trước khi commit. Test `test_migrations.py` báo đỏ nếu model và migration lệch nhau.

## Lỗi

Mọi lỗi trả về `application/problem+json` dạng `{"code": "...", "message": "...", "errors": [...]}`. `code` ổn định để Web và Desktop hiện thông báo tiếng Việt; service ném `AppError` (`core/errors.py`), router không tự tạo response lỗi.
