"""Schema tài khoản (openapi.yaml: User, UserCreate, /users/import)."""

import uuid

from pydantic import BaseModel, Field

from tutor_backend.models.enums import Role
from tutor_backend.schemas.common import ApiModel, Email, Password


class UserOut(ApiModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: Role
    is_active: bool


class UserCreate(BaseModel):
    email: Email
    full_name: str = Field(min_length=1, max_length=200)
    role: Role
    password: Password


class UserPage(BaseModel):
    items: list[UserOut]
    total: int


class ImportSkip(BaseModel):
    line: int
    reason: str


class GeneratedPassword(BaseModel):
    email: str
    password: str


class UserImportResult(BaseModel):
    created: int
    skipped: list[ImportSkip]
    # Mật khẩu tạo ngẫu nhiên cho dòng CSV không có cột password: chỉ trả về một lần để phát cho học viên
    generated_passwords: list[GeneratedPassword] = []
