"""Bảng `script_versions`: mỗi revision kịch bản là một dòng, không sửa đè (csdl.md mục 2.3)."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tutor_backend.db.base import Base, CreatedAtMixin, uuid_pk
from tutor_backend.models.enums import ScriptOrigin, ScriptStatus, enum_check

if TYPE_CHECKING:
    from tutor_backend.models.user import User

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

    # Tên người tạo, người duyệt để Web hiện lịch sử (FR-W10); giảng viên không xem được danh sách tài khoản
    creator: Mapped[User | None] = relationship(foreign_keys=[created_by], lazy="selectin", viewonly=True)
    reviewer: Mapped[User | None] = relationship(foreign_keys=[reviewed_by], lazy="selectin", viewonly=True)

    @property
    def created_by_name(self) -> str | None:
        return self.creator.full_name if self.creator else None

    @property
    def reviewed_by_name(self) -> str | None:
        return self.reviewer.full_name if self.reviewer else None
