"""Dùng chung cho test Backend.

CSDL test: SQLite tạm (mặc định) hoặc PostgreSQL khi đặt `TUTOR_TEST_DATABASE_URL` (job CI PostgreSQL).
Lược đồ luôn tạo bằng migration Alembic thật, không dùng `create_all`, để test cả migration.
"""

import os
import uuid
from collections.abc import Callable, Iterator
from pathlib import Path

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
