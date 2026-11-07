"""Bảng `script_versions`: mỗi revision kịch bản là một dòng, không sửa đè (csdl.md mục 2.3)."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from tutor_backend.db.base import Base, CreatedAtMixin, uuid_pk
from tutor_backend.models.enums import ScriptOrigin, ScriptStatus, enum_check

_PUBLISHED = text("status = 'published'")


class ScriptVersion(CreatedAtMixin, Base):
    __tablename__ = "script_versions"
    __table_args__ = (
        UniqueConstraint("exercise_id", "revision"),
        # Mỗi bài tối đa một bản đang phát hành: chỉ mục duy nhất có điều kiện (PostgreSQL và SQLite đều có)
        Index(
            "uq_script_versions_one_published",
            "exercise_id",
            unique=True,
            postgresql_where=_PUBLISHED,
            sqlite_where=_PUBLISHED,
        ),
        enum_check("status", ScriptStatus),
        enum_check("origin", ScriptOrigin),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    exercise_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("exercises.id", ondelete="CASCADE"))
    revision: Mapped[int]
    schema_version: Mapped[str] = mapped_column(String(8), default="1")
    status: Mapped[str] = mapped_column(String(20), default=ScriptStatus.DRAFT)
    origin: Mapped[str] = mapped_column(String(12))
    content: Mapped[dict[str, Any]]
    self_check_report: Mapped[dict[str, Any] | None]
    parent_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("script_versions.id", ondelete="SET NULL")
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("generation_jobs.id", ondelete="SET NULL"))
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    review_note: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime | None]
    published_at: Mapped[datetime | None]
    published_file_path: Mapped[str | None] = mapped_column(String(500))  # file đề đã nhúng mã bài
