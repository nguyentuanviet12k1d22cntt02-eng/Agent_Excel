"""Dùng chung cho test Backend.

CSDL test: SQLite tạm (mặc định) hoặc PostgreSQL khi đặt `TUTOR_TEST_DATABASE_URL` (job CI PostgreSQL).
Lược đồ luôn tạo bằng migration Alembic thật, không dùng `create_all`, để test cả migration.
"""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tutor_backend.core.config import Settings
from tutor_backend.core.jobs import InlineJobRunner
from tutor_backend.db.base import Base
from tutor_backend.db.migrate import downgrade_database, upgrade_database
from tutor_backend.main import create_app

TEST_DATABASE_URL_ENV = "TUTOR_TEST_DATABASE_URL"
TEST_JWT_SECRET = "khoa-chi-dung-cho-test-khong-dung-that"  # noqa: S105


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
