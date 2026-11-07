"""Phụ thuộc dùng chung cho router (khai báo bằng `Annotated` để tái dùng và để ruff B008 không báo)."""

from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session, sessionmaker

from tutor_backend.core.config import Settings
from tutor_backend.core.errors import ForbiddenError, UnauthorizedError
from tutor_backend.core.jobs import JobRunner
from tutor_backend.db.session import get_db
from tutor_backend.models import User
from tutor_backend.models.enums import Role
from tutor_backend.services import account_service
from tutor_backend.services.storage import FileStore


def get_settings_dep(request: Request) -> Settings:
    return request.app.state.settings


def get_jobs(request: Request) -> JobRunner:
    return request.app.state.jobs


def get_session_factory(request: Request) -> sessionmaker[Session]:
    """Cho tiến trình nền: mỗi công việc mở phiên CSDL riêng (phiên của request đóng khi trả lời)."""
    return request.app.state.session_factory


def get_store(request: Request) -> FileStore:
    return FileStore(request.app.state.settings.files_dir)


DbSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings_dep)]
Jobs = Annotated[JobRunner, Depends(get_jobs)]
Store = Annotated[FileStore, Depends(get_store)]
SessionFactory = Annotated[sessionmaker[Session], Depends(get_session_factory)]

_bearer = HTTPBearer(auto_error=False, description="Access token lấy từ POST /api/v1/auth/login")


def get_current_user(
    db: DbSession,
    settings: AppSettings,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if credentials is None:
        raise UnauthorizedError("Chưa đăng nhập", code="not_authenticated")
    return account_service.user_from_access_token(db, credentials.credentials, settings)


CurrentUser = Annotated[User, Depends(get_current_user)]


class RoleGuard:
    """Chặn người dùng không có vai trò được phép (`x-roles` trong openapi.yaml).

    Giữ `roles` thành thuộc tính để test đối chiếu được quyền của từng API với đặc tả.
    """

    def __init__(self, *roles: Role) -> None:
        self.roles = frozenset(roles)

    def __call__(self, user: CurrentUser) -> User:
        if user.role not in self.roles:
            raise ForbiddenError("Bạn không có quyền thực hiện thao tác này", code="forbidden_role")
        return user


ADMIN = RoleGuard(Role.ADMIN)
STAFF = RoleGuard(Role.ADMIN, Role.TEACHER)
STUDENT = RoleGuard(Role.STUDENT)
STUDENT_OR_TEACHER = RoleGuard(Role.STUDENT, Role.TEACHER)
ANY_ROLE = RoleGuard(Role.ADMIN, Role.TEACHER, Role.STUDENT)

Admin = Annotated[User, Depends(ADMIN)]
Staff = Annotated[User, Depends(STAFF)]
Student = Annotated[User, Depends(STUDENT)]
StudentOrTeacher = Annotated[User, Depends(STUDENT_OR_TEACHER)]
AnyRole = Annotated[User, Depends(ANY_ROLE)]
