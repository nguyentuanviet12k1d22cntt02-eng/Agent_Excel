"""Nhận file tải lên: giới hạn dung lượng, nhận dạng loại file theo nội dung (không tin phần mở rộng)."""

import io
import zipfile
from typing import BinaryIO

from tutor_backend.core.errors import InvalidError

_ZIP_MARKERS = {"xlsx": "xl/workbook.xml", "docx": "word/document.xml"}


def read_limited(stream: BinaryIO, max_bytes: int, field: str) -> bytes:
    data = stream.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise InvalidError(
            f"File quá lớn (tối đa {max_bytes // (1024 * 1024)} MB)",
            code="file_too_large",
            errors=[{"path": f"/{field}", "message": "file quá lớn"}],
        )
    if not data:
        raise InvalidError(
            "File rỗng", code="file_empty", errors=[{"path": f"/{field}", "message": "file rỗng"}]
        )
    return data


def detect_type(data: bytes) -> str | None:
    """Loại file: pdf, xlsx, docx hoặc None. File Office là ZIP có tệp đánh dấu bên trong."""
    if data.startswith(b"%PDF-"):
        return "pdf"
    if not data.startswith(b"PK"):
        return None
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            names = set(archive.namelist())
    except zipfile.BadZipFile:
        return None
    return next((kind for kind, marker in _ZIP_MARKERS.items() if marker in names), None)


def require_type(data: bytes, allowed: set[str], field: str) -> str:
    kind = detect_type(data)
    if kind not in allowed:
        expected = ", ".join(sorted(f".{k}" for k in allowed))
        raise InvalidError(
            f"File không đúng định dạng (cần {expected})",
            code="file_type_invalid",
            errors=[{"path": f"/{field}", "message": f"cần {expected}"}],
        )
    return kind
