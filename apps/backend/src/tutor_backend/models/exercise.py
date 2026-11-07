"""Bảng `exercises`: bài tập, file đề và file đáp án cùng bố cục (csdl.md mục 2.2)."""

import uuid
from typing import Any

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from tutor_backend.db.base import Base, TimestampMixin, uuid_pk


class Exercise(TimestampMixin, Base):
    __tablename__ = "exercises"

    id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(64), unique=True)  # = tutor_exercise_id nhúng vào file đề
    title: Mapped[str] = mapped_column(String(200))
    sheet_name: Mapped[str] = mapped_column(String(31))
    starter_file_path: Mapped[str] = mapped_column(String(500))
    solution_file_path: Mapped[str] = mapped_column(String(500))
    prompt_file_path: Mapped[str | None] = mapped_column(String(500))
    prompt_text: Mapped[str | None] = mapped_column(Text)
    skills: Mapped[list[Any]] = mapped_column(default=list)
    warnings: Mapped[list[Any]] = mapped_column(default=list)  # cảnh báo khi tải lên (bố cục lệch...)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
