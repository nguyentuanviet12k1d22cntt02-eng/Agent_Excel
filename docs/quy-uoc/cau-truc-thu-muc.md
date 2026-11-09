# Cấu trúc thư mục

Repo tổ chức theo kiểu **monorepo**: mỗi ứng dụng nằm trong `apps/`, mỗi thư viện dùng chung nằm trong `packages/`. Muốn mở rộng (ví dụ thêm gia sư Word) chỉ cần thêm một thư mục vào `apps/` hoặc `packages/`, không phải sửa cấu trúc cũ.

## 1. Tổng thể

```
Agent_Excel/
├─ apps/                       Ứng dụng chạy được
│  ├─ backend/                 FastAPI (Python)
│  ├─ desktop/                 Gia sư trên Windows (Python + PyQt6)
│  └─ web/                     Web quản trị (React + TypeScript)
├─ packages/                   Thư viện dùng chung giữa các ứng dụng
│  └─ excel_core/              Snapshot workbook, diff, kiểm tra điều kiện
├─ schemas/                    JSON Schema: "hợp đồng" dữ liệu giữa các ứng dụng
├─ samples/                    Bộ bài tập mẫu đã chuẩn hóa
├─ spikes/                     Code làm thử kỹ thuật, không dùng cho sản phẩm
├─ scripts/                    Công cụ quản lý repo
├─ docs/                       Tài liệu (tiếng Việt)
├─ .github/                    CI, mẫu Pull Request
├─ .vscode/                    Cấu hình VS Code dùng chung
├─ requirements-dev.txt        Cài toàn bộ môi trường Python bằng 1 lệnh
├─ pytest.ini · ruff.toml      Cấu hình test và kiểm tra code dùng chung
└─ .python-version             Phiên bản Python của nhóm (3.14)
```

Không đưa lên git: `.venv/`, `nckh/` (đề cương có thông tin cá nhân), `Cơ bản/` (tài liệu gốc của trung tâm), `key.txt`, `.env`, `samples/_local/`.

## 2. Một project Python (`apps/backend`, `apps/desktop`, `packages/excel_core`)

Mọi project Python dùng **bố cục `src/`** và cùng một khuôn:

```
apps/desktop/
├─ pyproject.toml              Tên, phiên bản, thư viện phụ thuộc
├─ README.md                   Project làm gì, chạy thế nào
├─ src/
│  └─ tutor_desktop/           Package Python (tên = tên import)
│     ├─ __init__.py
│     └─ <module con>/
└─ tests/                      Test của project, cấu trúc giống src/
```

Lý do dùng `src/`: test luôn chạy trên package **đã cài**, nên tránh lỗi "máy mình chạy được nhưng đóng gói thì hỏng".

### `apps/backend/src/tutor_backend/`

| Thư mục | Trách nhiệm | Được gọi tới |
|---|---|---|
| `api/v1/` | Router REST. Chỉ nhận request, kiểm tra dữ liệu vào, gọi `services`, trả response | `services`, `schemas` |
| `schemas/` | Pydantic model cho dữ liệu vào/ra API | — |
| `services/` | Nghiệp vụ: học liệu, sinh kịch bản, phát hành, tiến độ | `db`, `models`, `ai`, `excel_core` |
| `ai/` | RAG giáo trình, tác tử sinh kịch bản; prompt trong `ai/prompts/` | `excel_core` |
| `models/` | Model ORM SQLAlchemy, mỗi bảng một file | — |
| `db/` | Kết nối CSDL, session | `models` |
| `core/` | Cấu hình, bảo mật, ghi log | — |
| `../../migrations/` | Migration Alembic | — |

### `apps/desktop/src/tutor_desktop/`

| Thư mục | Trách nhiệm | Được gọi tới |
|---|---|---|
| `monitor/` | Đọc Excel qua COM, Win32 API, MSAA, UI Automation → phát **sự kiện quan sát** | `excel_core` |
| `agent/` | Teaching Agent: bước hiện tại, kiểm chứng, tín hiệu, cấp gợi ý | `excel_core`, `storage` |
| `ui/` | Cửa sổ gia sư, overlay, mascot (PyQt6); ảnh, icon trong `ui/resources/` | — (nhận dữ liệu qua signal) |
| `api_client/` | Gọi API Backend | — |
| `storage/` | Lưu kịch bản đã tải, hàng đợi nhật ký | — |
| `__main__.py` | Điểm khởi động: lắp ráp các phần lại với nhau | tất cả |
| `../../packaging/` | File `.spec`, icon, script đóng gói `.exe` | — |

### `packages/excel_core/src/excel_core/`

| Thư mục | Trách nhiệm |
|---|---|
| `snapshot/` | Kiểu dữ liệu snapshot workbook |
| `readers/` | Đọc workbook thành snapshot: `openpyxl_reader.py`, `com_reader.py`; chữ trong hình vẽ: `shapes.py` |
| `diff/` | So sánh file đề và file mẫu |
| `checks/` | Kiểm tra điều kiện: **mỗi loại điều kiện một file** |
| `script/` | Đọc và kiểm tra kịch bản JSON theo lược đồ trong `schemas/` |
| `procedure.py` | Làm lần lượt thao tác cấu trúc (ẩn/hiện, chèn, xóa, kích thước) trên snapshot: trạng thái mong đợi sau từng bước của kịch bản theo quy trình |

## 3. Quy tắc phụ thuộc giữa các phần

```
apps/web  ──HTTP──▶  apps/backend  ──import──▶  packages/excel_core  ◀──import──  apps/desktop
                          │                                                         │
                          └──────────────── HTTP (REST API) ◀───────────────────────┘
```

1. **`packages/` không bao giờ import từ `apps/`.** Thư viện dùng chung không được biết ai đang dùng nó.
2. **Các app không import lẫn nhau.** Backend và Desktop chỉ nói chuyện qua REST API, Web cũng vậy.
3. **Code chạy được ở cả hai phía thì đặt trong `packages/excel_core`**, không sao chép.
4. **`excel_core` không import `win32com` ở mức module.** Riêng `readers/com_reader.py` import trong hàm, để Backend (có thể chạy trên Linux) vẫn import được `excel_core`.
5. **Desktop không gọi LLM.** Mọi việc cần AI đều nằm ở `apps/backend/src/tutor_backend/ai/`.
6. **Trong Desktop, `ui/` không gọi COM.** Chỉ `monitor/` được nói chuyện với Excel; `ui/` nhận dữ liệu qua signal của Qt.
7. **Trong Backend, đi một chiều** `api → services → (db, ai, excel_core)`. `api/` không truy vấn CSDL trực tiếp.

## 4. Thêm mới thì đặt ở đâu

| Muốn thêm | Đặt ở | Ví dụ |
|---|---|---|
| Loại điều kiện kiểm chứng mới | `packages/excel_core/src/excel_core/checks/<ten>.py` + test cùng tên | `checks/number_format.py`, `tests/checks/test_number_format.py` |
| Nhóm API mới | `apps/backend/src/tutor_backend/api/v1/<tai_nguyen>.py` + `services/<tai_nguyen>_service.py` | `api/v1/exercises.py`, `services/exercise_service.py` |
| Bảng CSDL mới | `models/<ten_bang>.py` + migration Alembic | `models/script_version.py` |
| Nguồn quan sát mới cho Desktop | `apps/desktop/src/tutor_desktop/monitor/<nguon>.py` | `monitor/uia_ribbon.py` |
| Thành phần giao diện mới | `apps/desktop/src/tutor_desktop/ui/<ten>.py` | `ui/hint_panel.py` |
| Phiên bản lược đồ kịch bản mới | `schemas/tutor-script/v2/` | |
| Ứng dụng mới (ví dụ gia sư Word) | `apps/<ten>/` + `packages/<ten>_core/` nếu cần lõi riêng | `apps/word-desktop/` |
| Spike mới | `spikes/<ma-task>-<mo-ta>/` có `README.md` ghi kết luận | `spikes/t2-4-uia-ribbon/` |
| Tài liệu | `docs/<nhom>/` theo bảng ở [docs/README.md](../README.md) | |

## 5. Môi trường phát triển

Một môi trường ảo Python duy nhất ở gốc repo, cài tất cả project ở dạng editable:

```powershell
py -3.14 -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
```

Sau đó `pytest` chạy test của mọi project, còn `ruff check .` kiểm tra toàn repo. Khi đóng gói Desktop, PyInstaller chỉ lấy những module mà Desktop thực sự import, nên dùng chung môi trường không làm file `.exe` to thêm.
