"""/users: danh sách, tạo tài khoản, nhập CSV (chỉ quản trị)."""

from typing import Annotated

from fastapi import APIRouter, Query, UploadFile, status

from tutor_backend.api.deps import Admin, DbSession
from tutor_backend.models.enums import Role
from tutor_backend.schemas.common import PageQuery
from tutor_backend.schemas.user import UserCreate, UserImportResult, UserOut, UserPage
from tutor_backend.services import account_service

router = APIRouter(prefix="/users", tags=["accounts"])


@router.get("", summary="Danh sách tài khoản")
def list_users(
    db: DbSession,
    _: Admin,
    page: Annotated[PageQuery, Query()],
    role: Role | None = None,
) -> UserPage:
    items, total = account_service.list_users(db, role, page)
    return UserPage(items=[UserOut.model_validate(u) for u in items], total=total)


@router.post("", status_code=status.HTTP_201_CREATED, summary="Tạo tài khoản")
def create_user(body: UserCreate, db: DbSession, _: Admin) -> UserOut:
    return UserOut.model_validate(account_service.create_user(db, body))


@router.post("/import", summary="Nhập danh sách tài khoản từ CSV (email, full_name, role, password)")
def import_users(file: UploadFile, db: DbSession, _: Admin) -> UserImportResult:
    return account_service.import_users_csv(db, file.file.read())
