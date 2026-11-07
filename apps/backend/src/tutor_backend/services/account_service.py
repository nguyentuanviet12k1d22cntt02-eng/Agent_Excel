"""Tài khoản: đăng nhập, cấp token, tạo và nhập danh sách người dùng (FR-W01, FR-W02)."""

import csv
import io
import logging
import re
import secrets
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from tutor_backend.core.config import Settings
from tutor_backend.core.errors import ConflictError, InvalidError, NotFoundError, UnauthorizedError
from tutor_backend.core.security import (
    TokenType,
    create_token,
    decode_token,
    hash_password,
    verify_password,
)
from tutor_backend.models import User
from tutor_backend.models.enums import Role
from tutor_backend.schemas.auth import TokenPair
from tutor_backend.schemas.common import EMAIL_PATTERN, PageQuery
from tutor_backend.schemas.user import GeneratedPassword, ImportSkip, UserCreate, UserImportResult

logger = logging.getLogger(__name__)

MIN_PASSWORD_LENGTH = 8
GENERATED_PASSWORD_BYTES = 9  # ~12 ký tự, đủ khó đoán cho tài khoản học viên
_INVALID_LOGIN = "Email hoặc mật khẩu không đúng"


def normalize_email(email: str) -> str:
    return email.strip().lower()


def get_user(db: Session, user_id: uuid.UUID) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("Không tìm thấy tài khoản", code="user_not_found")
    return user


def issue_tokens(user: User, settings: Settings) -> TokenPair:
    return TokenPair(
        access_token=create_token(user.id, user.role, TokenType.ACCESS, settings),
        refresh_token=create_token(user.id, user.role, TokenType.REFRESH, settings),
        expires_in=settings.access_token_minutes * 60,
    )


def login(db: Session, email: str, password: str, settings: Settings) -> TokenPair:
    user = db.scalar(select(User).where(User.email == normalize_email(email)))
    # Cùng một thông báo cho sai email và sai mật khẩu: không lộ email nào có tài khoản
    if user is None or not verify_password(password, user.password_hash):
        raise UnauthorizedError(_INVALID_LOGIN, code="invalid_credentials")
    if not user.is_active:
        raise UnauthorizedError("Tài khoản đã bị khóa", code="account_disabled")
    return issue_tokens(user, settings)


def refresh(db: Session, refresh_token: str, settings: Settings) -> TokenPair:
    claims = decode_token(refresh_token, settings, TokenType.REFRESH)
    user = db.get(User, claims.user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("Tài khoản không còn hiệu lực", code="account_disabled")
    return issue_tokens(user, settings)


def user_from_access_token(db: Session, token: str, settings: Settings) -> User:
    claims = decode_token(token, settings, TokenType.ACCESS)
    user = db.get(User, claims.user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("Tài khoản không còn hiệu lực", code="account_disabled")
    return user


def create_user(db: Session, data: UserCreate) -> User:
    email = normalize_email(data.email)
    if db.scalar(select(User.id).where(User.email == email)) is not None:
        raise ConflictError(f"Email {email} đã có tài khoản", code="email_taken")
    user = User(
        email=email,
        full_name=data.full_name.strip(),
        role=data.role,
        password_hash=hash_password(data.password),
    )
    db.add(user)
    db.commit()
    logger.info("Tạo tài khoản %s (%s)", user.id, user.role)
    return user


def list_users(db: Session, role: Role | None, page: PageQuery) -> tuple[list[User], int]:
    query = select(User)
    if role is not None:
        query = query.where(User.role == role)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(query.order_by(User.full_name, User.email).offset(page.offset).limit(page.page_size))
    return list(items), total


def _import_row(row: dict[str, str], existing: set[str]) -> tuple[User | None, str | None, str | None]:
    """(user, mật khẩu tự tạo, lý do bỏ qua)."""
    email = normalize_email(row.get("email") or "")
    full_name = (row.get("full_name") or "").strip()
    role = (row.get("role") or Role.STUDENT).strip().lower()
    password = (row.get("password") or "").strip()
    if not re.match(EMAIL_PATTERN, email):
        return None, None, "email không hợp lệ"
    if email in existing:
        return None, None, "email đã có tài khoản"
    if not full_name:
        return None, None, "thiếu họ tên"
    if role not in set(Role):
        return None, None, f"vai trò không hợp lệ: {role}"
    if password and len(password) < MIN_PASSWORD_LENGTH:
        return None, None, f"mật khẩu ngắn hơn {MIN_PASSWORD_LENGTH} ký tự"
    generated = None if password else secrets.token_urlsafe(GENERATED_PASSWORD_BYTES)
    user = User(
        email=email, full_name=full_name, role=role, password_hash=hash_password(password or generated)
    )
    return user, generated, None


def import_users_csv(db: Session, content: bytes) -> UserImportResult:
    """CSV có tiêu đề: email, full_name, role (mặc định student), password (tùy chọn)."""
    try:
        text = content.decode("utf-8-sig")  # Excel lưu CSV UTF-8 có BOM
    except UnicodeDecodeError:
        raise InvalidError("File CSV phải là UTF-8", code="csv_encoding") from None
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or not {"email", "full_name"} <= {f.strip() for f in reader.fieldnames}:
        raise InvalidError("CSV cần các cột email, full_name (role, password tùy chọn)", code="csv_columns")
    existing = set(db.scalars(select(User.email)))
    created, skipped, generated = 0, [], []
    for line, raw in enumerate(reader, start=2):
        row = {(k or "").strip(): (v or "") for k, v in raw.items()}
        user, password, reason = _import_row(row, existing)
        if user is None:
            skipped.append(ImportSkip(line=line, reason=reason or "không rõ"))
            continue
        db.add(user)
        existing.add(user.email)
        created += 1
        if password:
            generated.append(GeneratedPassword(email=user.email, password=password))
    db.commit()
    return UserImportResult(created=created, skipped=skipped, generated_passwords=generated)
