"""Migration Alembic tạo đủ bảng theo ERD và khớp với model (T5.1)."""

from pathlib import Path

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect

import tutor_backend.models  # noqa: F401 — nạp đủ bảng
from tutor_backend.db.base import Base
from tutor_backend.db.migrate import downgrade_database, upgrade_database

ERD_TABLES = {
    "users",
    "classes",
    "class_members",
    "class_exercises",
    "textbooks",
    "textbook_chunks",
    "exercise_textbooks",
    "exercises",
    "generation_jobs",
    "script_versions",
    "practice_sessions",
    "step_progress",
    "event_logs",
    "skill_states",
    "survey_responses",
}


def test_migration_creates_every_erd_table(database_url: str):
    engine = create_engine(database_url)
    try:
        tables = set(inspect(engine).get_table_names()) - {"alembic_version"}
    finally:
        engine.dispose()
    assert tables == ERD_TABLES


def test_migration_matches_models(database_url: str):
    # Sửa model mà quên tạo migration thì test này đỏ
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            context = MigrationContext.configure(connection, opts={"compare_type": True})
            assert compare_metadata(context, Base.metadata) == []
    finally:
        engine.dispose()


def test_downgrade_then_upgrade_again(tmp_path: Path):
    url = f"sqlite:///{(tmp_path / 'roundtrip.db').as_posix()}"
    upgrade_database(url, configure_logger=False)
    downgrade_database(url)
    engine = create_engine(url)
    try:
        assert set(inspect(engine).get_table_names()) <= {"alembic_version"}
    finally:
        engine.dispose()
    upgrade_database(url, configure_logger=False)


def test_only_one_published_version_per_exercise_is_enforced(database_url: str):
    # Chỉ mục duy nhất có điều kiện (csdl.md 2.3) phải có trong CSDL thật, không chỉ trong model
    engine = create_engine(database_url)
    try:
        indexes = {ix["name"]: ix for ix in inspect(engine).get_indexes("script_versions")}
    finally:
        engine.dispose()
    assert indexes["uq_script_versions_one_published"]["unique"]
