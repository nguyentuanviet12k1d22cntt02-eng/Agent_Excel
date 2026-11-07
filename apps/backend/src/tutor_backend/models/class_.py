"""Bảng `classes`, `class_members` (nhóm thực nghiệm), `class_exercises` (bài được giao)."""

import uuid
from datetime import date, datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from tutor_backend.db.base import Base, CreatedAtMixin, TimestampMixin, uuid_pk
from tutor_backend.models.enums import StudyGroup, enum_check


class Class(TimestampMixin, Base):
    __tablename__ = "classes"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(200))
    teacher_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    starts_on: Mapped[date | None]
    ends_on: Mapped[date | None]


class ClassMember(CreatedAtMixin, Base):
    """`study_group` quyết định Desktop chạy chế độ `tutor` hay `control` (FR-D15)."""

    __tablename__ = "class_members"
    __table_args__ = (enum_check("study_group", StudyGroup),)

    class_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("classes.id", ondelete="CASCADE"), primary_key=True
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    study_group: Mapped[str] = mapped_column(String(16))


class ClassExercise(CreatedAtMixin, Base):
    __tablename__ = "class_exercises"

    class_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("classes.id", ondelete="CASCADE"), primary_key=True
    )
    exercise_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("exercises.id", ondelete="CASCADE"), primary_key=True
    )
    due_at: Mapped[datetime | None]
