"""Kết nối CSDL và phiên làm việc. Router nhận `Session` qua `Depends(get_db)`."""

from collections.abc import Iterator

from fastapi import Request
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from tutor_backend.core.config import Settings


def _enable_sqlite_foreign_keys(dbapi_connection: object, _: object) -> None:
    # SQLite tắt kiểm khóa ngoại theo mặc định: bật để ON DELETE CASCADE chạy giống PostgreSQL
    cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def create_db_engine(settings: Settings) -> Engine:
    if settings.is_sqlite:
        settings.storage_dir.mkdir(parents=True, exist_ok=True)
        engine = create_engine(
            settings.database_url,
            echo=settings.database_echo,
            connect_args={"check_same_thread": False},  # tiến trình nền dùng luồng khác
        )
        event.listen(engine, "connect", _enable_sqlite_foreign_keys)
        return engine
    return create_engine(settings.database_url, echo=settings.database_echo, pool_pre_ping=True)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(engine, expire_on_commit=False)


def get_db(request: Request) -> Iterator[Session]:
    """Một phiên CSDL cho mỗi request; service tự commit khi xong việc."""
    with request.app.state.session_factory() as session:
        yield session
