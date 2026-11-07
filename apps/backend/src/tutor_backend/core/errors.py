"""Lỗi chung của API: mọi lỗi trả về dạng `Problem` (openapi.yaml) với `code` ổn định.

Web và Desktop dựa vào `code` để hiện thông báo tiếng Việt, nên không đổi tên mã đã dùng.
"""

import logging
from collections.abc import Sequence
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

PROBLEM_MEDIA_TYPE = "application/problem+json"


class AppError(Exception):
    """Lỗi nghiệp vụ có mã ổn định. Service ném lỗi này; router không tự tạo response lỗi."""

    status_code = HTTPStatus.BAD_REQUEST
    code = "bad_request"

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        errors: Sequence[dict[str, str]] = (),
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code or self.code
        self.errors = list(errors)


class UnauthorizedError(AppError):
    status_code = HTTPStatus.UNAUTHORIZED
    code = "unauthorized"


class ForbiddenError(AppError):
    status_code = HTTPStatus.FORBIDDEN
    code = "forbidden"


class NotFoundError(AppError):
    status_code = HTTPStatus.NOT_FOUND
    code = "not_found"


class ConflictError(AppError):
    status_code = HTTPStatus.CONFLICT
    code = "conflict"


class InvalidError(AppError):
    status_code = HTTPStatus.UNPROCESSABLE_ENTITY
    code = "invalid"


def problem(
    status: int,
    code: str,
    message: str,
    errors: Sequence[dict[str, str]] = (),
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    body: dict[str, Any] = {"code": code, "message": message}
    if errors:
        body["errors"] = list(errors)
    return JSONResponse(body, status_code=status, media_type=PROBLEM_MEDIA_TYPE, headers=headers)


def _validation_errors(exc: RequestValidationError) -> list[dict[str, str]]:
    return [
        {
            "path": "/" + "/".join(str(part) for part in error.get("loc", ())),
            "message": str(error.get("msg", "")),
        }
        for error in exc.errors()
    ]


_HTTP_CODES = {
    HTTPStatus.NOT_FOUND: ("not_found", "Không tìm thấy"),
    HTTPStatus.METHOD_NOT_ALLOWED: ("method_not_allowed", "Phương thức không được hỗ trợ"),
    HTTPStatus.UNAUTHORIZED: ("unauthorized", "Chưa đăng nhập hoặc token hết hạn"),
    HTTPStatus.FORBIDDEN: ("forbidden", "Không có quyền thực hiện thao tác này"),
}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == HTTPStatus.UNAUTHORIZED else None
        return problem(exc.status_code, exc.code, exc.message, exc.errors, headers)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        return problem(
            HTTPStatus.UNPROCESSABLE_ENTITY,
            "validation_error",
            "Dữ liệu gửi lên không hợp lệ",
            _validation_errors(exc),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code, message = _HTTP_CODES.get(HTTPStatus(exc.status_code), ("http_error", str(exc.detail)))
        return problem(exc.status_code, code, message, headers=getattr(exc, "headers", None))

    @app.exception_handler(Exception)
    async def _unexpected(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Lỗi không lường trước ở %s %s", request.method, request.url.path, exc_info=exc)
        return problem(
            HTTPStatus.INTERNAL_SERVER_ERROR, "internal_error", "Lỗi máy chủ, vui lòng thử lại sau"
        )
