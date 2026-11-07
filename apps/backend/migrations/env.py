"""Môi trường chạy migration Alembic. URL CSDL: tham số `sqlalchemy.url` (test, CLI) hoặc Settings."""

from logging.config import fileConfig
from typing import Any

from alembic import context
from sqlalchemy import DateTime, engine_from_config, pool

import tutor_backend.models  # noqa: F401 — nạp đủ bảng vào Base.metadata
from tutor_backend.core.config import get_settings
from tutor_backend.db.base import Base, UTCDateTime

config = context.config
if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _database_url() -> str:
    return config.get_main_option("sqlalchemy.url") or get_settings().database_url


def _render_item(type_: str, obj: Any, autogen_context: Any) -> str | bool:
    # UTCDateTime chỉ đổi cách đọc/ghi trong Python; trong CSDL là DateTime(timezone=True) bình thường
    if type_ == "type" and isinstance(obj, UTCDateTime):
        return "sa.DateTime(timezone=True)"
    if type_ == "type" and isinstance(obj, DateTime):
        return f"sa.DateTime(timezone={obj.timezone})"
    return False


def run_migrations_offline() -> None:
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=True,
        render_item=_render_item,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = config.attributes.get("connection")
    if connectable is None:
        engine = engine_from_config(
            {"sqlalchemy.url": _database_url()}, prefix="sqlalchemy.", poolclass=pool.NullPool
        )
        with engine.connect() as connection:
            _run(connection)
    else:
        _run(connectable)


def _run(connection: Any) -> None:
    # render_as_batch: SQLite không ALTER được nhiều thứ, Alembic dựng lại bảng thay vào đó
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,
        render_item=_render_item,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
