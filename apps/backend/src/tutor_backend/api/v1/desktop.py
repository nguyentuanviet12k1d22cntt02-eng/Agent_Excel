"""/desktop: API riêng cho Desktop gia sư (bài được giao, kịch bản đang phát hành, mức kỹ năng)."""

from typing import Annotated

from fastapi import APIRouter, Header, Path, Response, status
from fastapi.responses import JSONResponse

from tutor_backend.api.deps import DbSession, Store, Student
from tutor_backend.models.enums import SupportState
from tutor_backend.schemas.desktop import Assignment, DesktopScript
from tutor_backend.services import desktop_service, progress_service

router = APIRouter(prefix="/desktop", tags=["desktop"])

CODE_PATTERN = r"^[a-z0-9][a-z0-9-]{2,63}$"


@router.get("/assignments", summary="Bài được giao cho học viên, kèm bản phát hành hiện tại")
def assignments(db: DbSession, student: Student) -> list[Assignment]:
    return desktop_service.assignments(db, student)


@router.get(
    "/exercises/{exercise_code}/script",
    summary="Kịch bản ĐANG PHÁT HÀNH của bài (theo mã bài đọc từ file đề)",
    response_model=DesktopScript,
    responses={304: {"description": "Bản Desktop đang có vẫn là bản mới nhất"}},
)
def published_script(
    exercise_code: Annotated[str, Path(pattern=CODE_PATTERN)],
    db: DbSession,
    store: Store,
    student: Student,
    if_none_match: Annotated[str | None, Header()] = None,
) -> Response:
    script = desktop_service.published_script(db, store, student, exercise_code)
    etag = f'"{script.version_id}"'
    if if_none_match and etag in {tag.strip().removeprefix("W/") for tag in if_none_match.split(",")}:
        return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers={"ETag": etag})
    return JSONResponse(script.model_dump(mode="json"), headers={"ETag": etag})


@router.get("/skill-states", summary="Mức hỗ trợ theo kỹ năng của học viên (cho luật giảm dần trợ giúp)")
def skill_states(db: DbSession, student: Student) -> dict[str, SupportState]:
    return progress_service.skill_states(db, student)
