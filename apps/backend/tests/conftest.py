"""Dùng chung cho test Backend.

CSDL test: SQLite tạm (mặc định) hoặc PostgreSQL khi đặt `TUTOR_TEST_DATABASE_URL` (job CI PostgreSQL).
Lược đồ luôn tạo bằng migration Alembic thật, không dùng `create_all`, để test cả migration.
"""

import io
import os
import uuid
from collections.abc import Callable, Iterator
from pathlib import Path

import docx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tutor_backend.core.config import Settings
from tutor_backend.core.jobs import InlineJobRunner
from tutor_backend.core.security import TokenType, create_token, hash_password
from tutor_backend.db.base import Base
from tutor_backend.db.migrate import downgrade_database, upgrade_database
from tutor_backend.main import create_app
from tutor_backend.models import User

TEST_DATABASE_URL_ENV = "TUTOR_TEST_DATABASE_URL"
TEST_JWT_SECRET = "khoa-chi-dung-cho-test-khong-dung-that"  # noqa: S105
TEST_PASSWORD = "matkhau-test-123"  # noqa: S105


@pytest.fixture(scope="session")
def database_url(tmp_path_factory: pytest.TempPathFactory) -> str:
    url = os.environ.get(TEST_DATABASE_URL_ENV)
    if url:
        downgrade_database(url)  # CSDL PostgreSQL của CI: bắt đầu sạch
    else:
        url = f"sqlite:///{(tmp_path_factory.mktemp('db') / 'test.db').as_posix()}"
    upgrade_database(url, configure_logger=False)
    return url


@pytest.fixture
def settings(database_url: str, tmp_path: Path) -> Settings:
    return Settings(
        _env_file=None,  # không đọc apps/backend/.env thật (có API key)
        database_url=database_url,
        storage_dir=tmp_path / "storage",
        jwt_secret=TEST_JWT_SECRET,
        llm_api_key=None,
    )


@pytest.fixture
def app(settings: Settings) -> Iterator[FastAPI]:
    application = create_app(settings, job_runner=InlineJobRunner())
    yield application
    # Dọn dữ liệu sau mỗi test, bảng con trước bảng cha
    with application.state.engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(table.delete())
    application.state.engine.dispose()


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db(app: FastAPI) -> Iterator[Session]:
    with app.state.session_factory() as session:
        yield session


@pytest.fixture
def make_user(app: FastAPI) -> Callable[..., User]:
    """Tạo người dùng thẳng trong CSDL (mật khẩu mặc định TEST_PASSWORD)."""

    def _make(
        role: str = "teacher", email: str | None = None, password: str = TEST_PASSWORD, **extra: object
    ) -> User:
        with app.state.session_factory() as session:
            user = User(
                email=email or f"{role}-{uuid.uuid4().hex[:8]}@test.vn",
                full_name=str(extra.pop("full_name", f"Người dùng {role}")),
                role=role,
                password_hash=hash_password(password),
                **extra,
            )
            session.add(user)
            session.commit()
            return user

    return _make


@pytest.fixture
def auth(app: FastAPI) -> Callable[[User], dict[str, str]]:
    """Header Authorization cho một người dùng (không đi qua API đăng nhập)."""

    def _headers(user: User) -> dict[str, str]:
        token = create_token(user.id, user.role, TokenType.ACCESS, app.state.settings)
        return {"Authorization": f"Bearer {token}"}

    return _headers


REPO = Path(__file__).resolve().parents[3]
EXCEL_FIXTURES = REPO / "packages" / "excel_core" / "tests" / "fixtures"  # bài tự soạn b09, b22 (GĐ4)


@pytest.fixture
def exercise_files() -> Callable[[str], dict[str, tuple[str, bytes, str]]]:
    """Phần `files` của request tạo bài tập, lấy file đề/đáp án tự soạn b09 hoặc b22."""

    def _files(name: str = "b09") -> dict[str, tuple[str, bytes, str]]:
        folder = EXCEL_FIXTURES / name
        return {
            "starter_file": ("de.xlsx", (folder / "de.xlsx").read_bytes(), XLSX_MIME),
            "solution_file": ("dap-an.xlsx", (folder / "dap-an.xlsx").read_bytes(), XLSX_MIME),
        }

    return _files


XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


# ----- Giáo trình mẫu cho test RAG (nhóm tự soạn, không phải tài liệu trung tâm) -----

TEXTBOOK_SECTIONS = [
    (1, "Chương 1. Làm quen với Excel", None),
    (2, "Bài 1. Nhập dữ liệu", "Gõ dữ liệu vào ô rồi bấm Enter. Số tự căn phải, chữ tự căn trái."),
    (
        2,
        "Bài 9. Định dạng dữ liệu số",
        "Nút Comma Style thêm dấu phân cách hàng nghìn. Increase Decimal tăng số lẻ.",
    ),
    (1, "Chương 3. Hàm thông dụng", None),
    (
        2,
        "Bài 22. Hàm SUM",
        "Hàm SUM tính tổng các số trong một vùng ô. Cú pháp: =SUM(vùng). Nút AutoSum gõ sẵn hàm SUM.",
    ),
    (
        2,
        "Bài 30. Hàm VLOOKUP",
        "Hàm VLOOKUP dò tìm một giá trị ở cột đầu tiên của bảng dò và trả về giá trị ở cột chỉ định. "
        "Cú pháp: =VLOOKUP(giá_trị_dò, bảng_dò, cột_trả_về, 0). Bảng dò nên dùng địa chỉ tuyệt đối.",
    ),
    (
        2,
        "Bài 31. Hàm IF",
        "Hàm IF kiểm tra một điều kiện, đúng thì trả giá trị thứ nhất, sai thì trả giá trị thứ hai.",
    ),
]


def build_textbook_docx() -> bytes:
    document = docx.Document()
    for level, title, body in TEXTBOOK_SECTIONS:
        document.add_heading(title, level=level)
        if body:
            document.add_paragraph(body)
    # Tiêu đề gõ tay (kiểu Normal) như nhiều giáo trình của trung tâm
    document.add_paragraph("BÀI 25: HÀM MIN, MAX")
    document.add_paragraph("Hàm MIN trả số nhỏ nhất, hàm MAX trả số lớn nhất trong vùng.")
    table = document.add_table(rows=2, cols=2)
    table.cell(0, 0).text, table.cell(0, 1).text = "Hàm", "Công dụng"
    table.cell(1, 0).text, table.cell(1, 1).text = "MAX", "Giá trị lớn nhất"
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def build_text_pdf(lines: list[str]) -> bytes:
    """PDF một trang có chữ (ASCII, phông Helvetica có sẵn), tự tính bảng xref."""
    content = "BT /F1 12 Tf 72 800 Td 16 TL " + " ".join(f"({line}) Tj T*" for line in lines) + " ET"
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R "
        "/Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(content)} >>\nstream\n{content}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n{body}\nendobj\n".encode("latin-1")
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("latin-1")
    out += "".join(f"{offset:010d} 00000 n \n" for offset in offsets).encode("latin-1")
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode(
        "latin-1"
    )
    return bytes(out)


@pytest.fixture
def textbook_docx() -> bytes:
    return build_textbook_docx()


@pytest.fixture
def text_pdf() -> Callable[[list[str]], bytes]:
    return build_text_pdf
