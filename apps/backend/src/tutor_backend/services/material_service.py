"""Giáo trình: tải lên, danh sách, xóa (FR-W03). Lập chỉ mục cho RAG chạy nền (T5.4, `ai/rag.py`)."""

import logging
import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, sessionmaker

from tutor_backend.ai import rag
from tutor_backend.ai.textbook_parser import TextbookParseError, parse_textbook
from tutor_backend.core.errors import ConflictError, NotFoundError
from tutor_backend.models import Textbook, TextbookChunk, User, exercise_textbooks
from tutor_backend.models.enums import TextbookStatus
from tutor_backend.schemas.textbook import TextbookOut
from tutor_backend.services.storage import FileStore
from tutor_backend.services.uploads import require_type

logger = logging.getLogger(__name__)

TEXTBOOK_TYPES = {"pdf", "docx"}


def _to_out(db: Session, textbook: Textbook) -> TextbookOut:
    count = db.scalar(select(func.count()).where(TextbookChunk.textbook_id == textbook.id)) or 0
    return TextbookOut.model_validate(textbook).model_copy(update={"chunk_count": count})


def get_textbook(db: Session, textbook_id: uuid.UUID) -> Textbook:
    textbook = db.get(Textbook, textbook_id)
    if textbook is None:
        raise NotFoundError("Không tìm thấy giáo trình", code="textbook_not_found")
    return textbook


def textbook_out(db: Session, textbook_id: uuid.UUID) -> TextbookOut:
    # Đọc lại từ CSDL: tiến trình nền có thể vừa đổi trạng thái trong phiên khác
    textbook = db.get(Textbook, textbook_id, populate_existing=True)
    if textbook is None:
        raise NotFoundError("Không tìm thấy giáo trình", code="textbook_not_found")
    return _to_out(db, textbook)


def list_textbooks(db: Session) -> list[TextbookOut]:
    return [_to_out(db, t) for t in db.scalars(select(Textbook).order_by(Textbook.title))]


def upload_textbook(db: Session, store: FileStore, title: str, data: bytes, user: User) -> Textbook:
    """Lưu file và tạo bản ghi (trạng thái `uploaded`); việc lập chỉ mục do router xếp vào tiến trình nền."""
    kind = require_type(data, TEXTBOOK_TYPES, "file")
    textbook_id = uuid.uuid4()
    path = store.save(f"textbooks/{textbook_id}.{kind}", data)
    textbook = Textbook(
        id=textbook_id, title=title.strip(), file_path=path, file_type=kind, uploaded_by=user.id
    )
    db.add(textbook)
    db.commit()
    logger.info("Tải lên giáo trình %s (%s, %d byte)", textbook_id, kind, len(data))
    return textbook


def delete_textbook(db: Session, store: FileStore, textbook_id: uuid.UUID) -> None:
    textbook = get_textbook(db, textbook_id)
    used = db.scalar(select(func.count()).where(exercise_textbooks.c.textbook_id == textbook_id)) or 0
    if used:
        raise ConflictError(
            f"Giáo trình đang gắn với {used} bài tập, gỡ khỏi bài trước khi xóa", code="textbook_in_use"
        )
    if textbook.status == TextbookStatus.INDEXING:
        raise ConflictError("Giáo trình đang được lập chỉ mục, thử lại sau", code="textbook_busy")
    db.delete(textbook)
    db.commit()
    store.delete(textbook.file_path)


def index_textbook(session_factory: sessionmaker[Session], store: FileStore, textbook_id: uuid.UUID) -> None:
    """Tiến trình nền: tách giáo trình thành đoạn cho RAG. Lỗi ghi vào `textbooks.error`, không ném ra."""
    with session_factory() as db:
        textbook = db.get(Textbook, textbook_id)
        if textbook is None:
            return
        textbook.status, textbook.error = TextbookStatus.INDEXING, None
        db.commit()
        try:
            sections = parse_textbook(store.path(textbook.file_path).read_bytes(), textbook.file_type)
            chunks = rag.chunk_sections(sections)
            if not chunks:
                raise TextbookParseError("Không tìm thấy nội dung chữ trong giáo trình")
            db.execute(delete(TextbookChunk).where(TextbookChunk.textbook_id == textbook_id))
            db.add_all(
                TextbookChunk(textbook_id=textbook_id, ord=i, heading=heading, page=page, content=content)
                for i, (heading, page, content) in enumerate(chunks)
            )
            textbook.status = TextbookStatus.READY
            logger.info("Lập chỉ mục giáo trình %s: %d đoạn", textbook_id, len(chunks))
        except (TextbookParseError, OSError) as exc:
            db.rollback()
            textbook = db.get(Textbook, textbook_id)
            if textbook is None:
                return
            textbook.status, textbook.error = TextbookStatus.FAILED, str(exc)
            logger.warning("Lập chỉ mục giáo trình %s lỗi: %s", textbook_id, exc)
        db.commit()


def search_passages(
    db: Session, query: str, textbook_ids: list[uuid.UUID] | None, limit: int
) -> list[rag.Passage]:
    return rag.search(db, query, textbook_ids, limit)
