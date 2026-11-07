"""`GET /health`: máy chủ và CSDL còn chạy không (dùng khi triển khai, T8.2)."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

import tutor_backend
from tutor_backend.api.deps import DbSession

router = APIRouter(tags=["health"])


@router.get("/health", summary="Kiểm tra máy chủ và CSDL")
def health(db: DbSession) -> JSONResponse:
    try:
        db.execute(text("SELECT 1"))
        database = "ok"
    except SQLAlchemyError:
        database = "error"
    status = 200 if database == "ok" else 503
    body = {
        "status": "ok" if status == 200 else "degraded",
        "database": database,
        "version": tutor_backend.__version__,
    }
    return JSONResponse(body, status_code=status)
