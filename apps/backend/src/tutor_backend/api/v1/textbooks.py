"""/textbooks: giáo trình cho RAG (tải lên, lập chỉ mục chạy nền, tìm đoạn liên quan)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Form, Query, Response, UploadFile, status

from tutor_backend.api.deps import AppSettings, DbSession, Jobs, SessionFactory, Staff, Store
from tutor_backend.schemas.textbook import PassageOut, TextbookOut
from tutor_backend.services import material_service
from tutor_backend.services.uploads import read_limited

router = APIRouter(prefix="/textbooks", tags=["materials"])


@router.get("", summary="Danh sách giáo trình")
def list_textbooks(db: DbSession, _: Staff) -> list[TextbookOut]:
    return material_service.list_textbooks(db)


@router.post(
    "", status_code=status.HTTP_202_ACCEPTED, summary="Tải lên giáo trình (PDF/DOCX); lập chỉ mục chạy nền"
)
def upload_textbook(
    title: Annotated[str, Form(min_length=1, max_length=200)],
    file: UploadFile,
    db: DbSession,
    store: Store,
    settings: AppSettings,
    jobs: Jobs,
    session_factory: SessionFactory,
    user: Staff,
) -> TextbookOut:
    data = read_limited(file.file, settings.max_upload_bytes, "file")
    textbook = material_service.upload_textbook(db, store, title, data, user)
    jobs.submit(material_service.index_textbook, session_factory, store, textbook.id)
    return material_service.textbook_out(db, textbook.id)


# Đặt trước "/{textbook_id}" để "search" không bị hiểu là id
@router.get("/search", summary="Tìm đoạn giáo trình liên quan (RAG, BM25)")
def search_textbooks(
    db: DbSession,
    _: Staff,
    q: Annotated[str, Query(min_length=1, max_length=500)],
    textbook_ids: Annotated[list[uuid.UUID] | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=20)] = 5,
) -> list[PassageOut]:
    passages = material_service.search_passages(db, q, textbook_ids, limit)
    return [PassageOut.model_validate(p) for p in passages]


@router.get("/{textbook_id}", summary="Chi tiết giáo trình")
def get_textbook(textbook_id: uuid.UUID, db: DbSession, _: Staff) -> TextbookOut:
    return material_service.textbook_out(db, textbook_id)


@router.delete("/{textbook_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Xóa giáo trình")
def delete_textbook(textbook_id: uuid.UUID, db: DbSession, store: Store, _: Staff) -> Response:
    material_service.delete_textbook(db, store, textbook_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
