"""Băm mật khẩu (argon2) và token JWT (access 60 phút, refresh 14 ngày; kien-truc.md mục 2, NFR-10)."""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from tutor_backend.core.config import Settings
from tutor_backend.core.errors import UnauthorizedError

JWT_ALGORITHM = "HS256"
_hasher = PasswordHasher()


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


@dataclass(frozen=True)
class TokenClaims:
    user_id: uuid.UUID
    role: str
    token_type: TokenType


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except VerificationError, InvalidHashError:
        return False


def create_token(user_id: uuid.UUID, role: str, token_type: TokenType, settings: Settings) -> str:
    now = datetime.now(UTC)
    lifetime = (
        timedelta(minutes=settings.access_token_minutes)
        if token_type == TokenType.ACCESS
        else timedelta(days=settings.refresh_token_days)
    )
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": token_type.value,
        "iat": now,
        "exp": now + lifetime,
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, _secret(settings), algorithm=JWT_ALGORITHM)


def decode_token(token: str, settings: Settings, expected: TokenType) -> TokenClaims:
    """Giải mã và kiểm token; sai chữ ký, hết hạn, sai loại → UnauthorizedError."""
    try:
        payload = jwt.decode(token, _secret(settings), algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise UnauthorizedError("Phiên đăng nhập đã hết hạn", code="token_expired") from None
    except jwt.PyJWTError:
        raise UnauthorizedError("Token không hợp lệ", code="token_invalid") from None
    if payload.get("type") != expected.value:
        raise UnauthorizedError("Sai loại token", code="token_invalid")
    try:
        return TokenClaims(uuid.UUID(payload["sub"]), str(payload["role"]), expected)
    except KeyError, ValueError:
        raise UnauthorizedError("Token không hợp lệ", code="token_invalid") from None


def _secret(settings: Settings) -> str:
    if settings.jwt_secret is None:  # Settings luôn điền khóa tạm; tới đây là lỗi cấu hình
        raise RuntimeError("Chưa có JWT_SECRET")
    return settings.jwt_secret.get_secret_value()
