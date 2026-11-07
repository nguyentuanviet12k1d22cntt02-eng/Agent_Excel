"""Chạy migration Alembic từ code (CLI `python -m tutor_backend migrate`, test)."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy.engine import make_url

from tutor_backend.core.config import BACKEND_DIR

ALEMBIC_INI = BACKEND_DIR / "alembic.ini"


def alembic_config(database_url: str, *, configure_logger: bool = True) -> Config:
    if not ALEMBIC_INI.is_file():
        raise FileNotFoundError(f"Không thấy {ALEMBIC_INI}: chạy Backend từ thư mục repo (apps/backend)")
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    config.attributes["configure_logger"] = configure_logger
    return config


def _ensure_sqlite_dir(database_url: str) -> None:
    url = make_url(database_url)
    if url.get_backend_name() == "sqlite" and url.database and url.database != ":memory:":
        Path(url.database).parent.mkdir(parents=True, exist_ok=True)


def upgrade_database(database_url: str, revision: str = "head", *, configure_logger: bool = True) -> None:
    _ensure_sqlite_dir(database_url)
    command.upgrade(alembic_config(database_url, configure_logger=configure_logger), revision)


def downgrade_database(database_url: str, revision: str = "base") -> None:
    command.downgrade(alembic_config(database_url, configure_logger=False), revision)


def migrations_dir() -> Path:
    return BACKEND_DIR / "migrations"
