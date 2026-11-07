"""Bảng `generation_jobs`: mỗi lần bấm "Sinh kịch bản" (dữ liệu cho đánh giá kỹ thuật, đề cương 5.2)."""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from tutor_backend.db.base import Base, CreatedAtMixin, uuid_pk
from tutor_backend.models.enums import JobStatus, enum_check


class GenerationJob(CreatedAtMixin, Base):
    __tablename__ = "generation_jobs"
    __table_args__ = (enum_check("status", JobStatus),)

    id: Mapped[uuid.UUID] = uuid_pk()
    exercise_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("exercises.id", ondelete="CASCADE"), index=True)
    requested_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(String(16), default=JobStatus.QUEUED)
    stage: Mapped[str | None] = mapped_column(String(16))  # diff | rag | llm | self_check
    model: Mapped[str] = mapped_column(String(80))
    instructions: Mapped[str | None] = mapped_column(Text)  # lưu ý thêm của giảng viên
    attempts: Mapped[int] = mapped_column(default=0)
    prompt_tokens: Mapped[int] = mapped_column(default=0)
    completion_tokens: Mapped[int] = mapped_column(default=0)
    duration_ms: Mapped[int] = mapped_column(default=0)
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None]
    finished_at: Mapped[datetime | None]
