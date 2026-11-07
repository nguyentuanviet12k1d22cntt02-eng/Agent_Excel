"""Bảng `users`: tài khoản cả 3 vai trò (csdl.md mục 2.1)."""

import uuid

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from tutor_backend.db.base import Base, TimestampMixin, uuid_pk
from tutor_backend.models.enums import Role, enum_check


class User(TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (enum_check("role", Role),)

    id: Mapped[uuid.UUID] = uuid_pk()
    email: Mapped[str] = mapped_column(String(254), unique=True)  # luôn lưu chữ thường
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(16))
    is_active: Mapped[bool] = mapped_column(default=True)
