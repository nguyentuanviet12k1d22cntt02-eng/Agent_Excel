"""/auth: đăng nhập, làm mới token, thông tin người đang đăng nhập."""

from fastapi import APIRouter

from tutor_backend.api.deps import AnyRole, AppSettings, DbSession
from tutor_backend.schemas.auth import LoginRequest, RefreshRequest, TokenPair
from tutor_backend.schemas.user import UserOut
from tutor_backend.services import account_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", summary="Đăng nhập")
def login(body: LoginRequest, db: DbSession, settings: AppSettings) -> TokenPair:
    return account_service.login(db, body.email, body.password, settings)


@router.post("/refresh", summary="Lấy access token mới bằng refresh token")
def refresh(body: RefreshRequest, db: DbSession, settings: AppSettings) -> TokenPair:
    return account_service.refresh(db, body.refresh_token, settings)


@router.get("/me", summary="Thông tin người đang đăng nhập")
def me(user: AnyRole) -> UserOut:
    return UserOut.model_validate(user)
