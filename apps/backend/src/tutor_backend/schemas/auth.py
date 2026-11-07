"""Schema đăng nhập, token (openapi.yaml: /auth/*, TokenPair)."""

from pydantic import BaseModel

from tutor_backend.schemas.common import Email


class LoginRequest(BaseModel):
    email: Email
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int  # giây
    token_type: str = "bearer"
