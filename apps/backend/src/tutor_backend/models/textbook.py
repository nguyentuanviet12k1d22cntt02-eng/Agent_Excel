"""Bảng `textbooks`, `textbook_chunks` (đoạn cho RAG), `exercise_textbooks` (bài ↔ giáo trình)."""

import uuid

from sqlalchemy import Column, ForeignKey, Index, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column

from tutor_backend.db.base import Base, CreatedAtMixin, TimestampMixin, uuid_pk
from tutor_backend.models.enums import FileType, TextbookStatus, enum_check

exercise_textbooks = Table(
    "exercise_textbooks",
    Base.metadata,
    Column("exercise_id", ForeignKey("exercises.id", ondelete="CASCADE"), primary_key=True),
    Column("textbook_id", ForeignKey("textbooks.id", ondelete="CASCADE"), primary_key=True),
)


class Textbook(TimestampMixin, Base):
    __tablename__ = "textbooks"
    __table_args__ = (enum_check("file_type", FileType), enum_check("status", TextbookStatus))

    id: Mapped[uuid.UUID] = uuid_pk()
    title: Mapped[str] = mapped_column(String(200))
    file_path: Mapped[str] = mapped_column(String(500))
    file_type: Mapped[str] = mapped_column(String(8))
    status: Mapped[str] = mapped_column(String(16), default=TextbookStatus.UPLOADED)
    error: Mapped[str | None] = mapped_column(Text)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))


class TextbookChunk(CreatedAtMixin, Base):
    """Một đoạn giáo trình theo mục. Tìm kiếm BM25 tính trong Python (T5.4), nên không cần cột tsvector."""

    __tablename__ = "textbook_chunks"
    __table_args__ = (Index("ix_textbook_chunks_textbook_ord", "textbook_id", "ord"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    textbook_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("textbooks.id", ondelete="CASCADE"))
    ord: Mapped[int]
    heading: Mapped[str] = mapped_column(Text, default="")
    page: Mapped[int | None]
    content: Mapped[str] = mapped_column(Text)
