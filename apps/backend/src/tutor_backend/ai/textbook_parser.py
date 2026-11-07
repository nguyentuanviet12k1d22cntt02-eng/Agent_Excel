"""Tách giáo trình PDF/DOCX thành các mục theo tiêu đề (T5.4).

Tiêu đề nhận ra bằng kiểu đoạn "Heading ..." của Word (DOCX), hoặc mẫu dòng "BÀI 22: ...", "Chương 2",
"1.2 ..." (tài liệu định dạng bằng tay, PDF). Mỗi mục giữ đường dẫn tiêu đề ("Chương 3 > Bài 22 Hàm SUM")
và trang.
"""

import io
import re
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass

import docx
from docx.document import Document
from docx.opc.exceptions import PackageNotFoundError
from docx.table import Table
from docx.text.paragraph import Paragraph
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from tutor_backend.ai.vietnamese import strip_accents

MAX_HEADING_LENGTH = 120
# So trên chữ đã bỏ dấu: PDF đôi khi mất dấu khi trích chữ, giáo trình cũ gõ "BAI 22" không dấu
_HEADING_LINE = re.compile(
    r"^\s*(?:(?:chuong|bai|phan|muc|chapter|lesson)\s+[\w.]+\s*[:.\-–]?|(?:\d+\.){1,3}\d*\s+\S)",
    re.IGNORECASE,
)
_HEADING_STYLE = re.compile(r"^(heading|title|tiêu đề)\s*(\d*)$", re.IGNORECASE)


class TextbookParseError(ValueError):
    """Không đọc được nội dung giáo trình."""


@dataclass(frozen=True)
class Section:
    heading: str  # đường dẫn tiêu đề, ví dụ "Chương 3 > Bài 22. Hàm SUM"
    page: int | None
    text: str


@dataclass
class _Builder:
    sections: list[Section]
    path: list[tuple[int, str]]
    lines: list[str]
    page: int | None = None

    def heading(self, level: int, text: str, page: int | None) -> None:
        self.flush()
        while self.path and self.path[-1][0] >= level:
            self.path.pop()
        self.path.append((level, text))
        self.page = page

    def line(self, text: str, page: int | None) -> None:
        if not self.lines:
            self.page = page if page is not None else self.page
        self.lines.append(text)

    def flush(self) -> None:
        text = "\n".join(line for line in self.lines if line.strip()).strip()
        if text:
            heading = " > ".join(title for _, title in self.path)
            self.sections.append(Section(heading, self.page, text))
        self.lines = []


def _normalize(text: str) -> str:
    return re.sub(r"[ \t ]+", " ", text).strip()


def heading_level(line: str) -> int | None:
    """Cấp tiêu đề đoán từ chữ: chương/phần là 1, bài/mục là 2, "1.2" là số dấu chấm + 1.

    Không phải tiêu đề thì trả về None.
    """
    text = _normalize(line)
    if not text or len(text) > MAX_HEADING_LENGTH or not _HEADING_LINE.match(strip_accents(text)):
        return None
    first = strip_accents(text.split()[0]).lower()
    if first in ("chuong", "phan", "chapter"):
        return 1
    if first in ("bai", "muc", "lesson"):
        return 2
    number = re.match(r"^((?:\d+\.){1,3}\d*)", text)
    return 1 + number.group(1).rstrip(".").count(".") if number else 2


def _docx_blocks(document: Document) -> Iterator[Paragraph | Table]:
    """Đoạn văn và bảng theo đúng thứ tự trong tài liệu."""
    for child in document.element.body.iterchildren():
        if child.tag.endswith("}p"):
            yield Paragraph(child, document)
        elif child.tag.endswith("}tbl"):
            yield Table(child, document)


def _style_level(paragraph: Paragraph) -> int | None:
    name = paragraph.style.name if paragraph.style is not None else ""
    match = _HEADING_STYLE.match(name or "")
    if not match:
        return None
    return int(match.group(2) or 1)


def parse_docx(data: bytes) -> list[Section]:
    try:
        document = docx.Document(io.BytesIO(data))
    except (ValueError, KeyError, OSError, zipfile.BadZipFile, PackageNotFoundError) as exc:
        raise TextbookParseError(f"Không đọc được file DOCX: {exc}") from exc
    builder = _Builder([], [], [])
    for block in _docx_blocks(document):
        if isinstance(block, Table):
            for row in block.rows:
                cells = [_normalize(cell.text) for cell in row.cells]
                builder.line(" | ".join(dict.fromkeys(c for c in cells if c)), None)
            continue
        text = _normalize(block.text)
        if not text:
            continue
        level = _style_level(block) or heading_level(text)
        if level is not None:
            builder.heading(level, text, None)
        else:
            builder.line(text, None)
    builder.flush()
    return builder.sections


def parse_pdf(data: bytes) -> list[Section]:
    try:
        reader = PdfReader(io.BytesIO(data))
        pages = [page.extract_text() or "" for page in reader.pages]
    except (PdfReadError, ValueError, KeyError, OSError) as exc:
        raise TextbookParseError(f"Không đọc được file PDF: {exc}") from exc
    builder = _Builder([], [], [])
    for number, text in enumerate(pages, start=1):
        for raw in text.splitlines():
            line = _normalize(raw)
            if not line:
                continue
            level = heading_level(line)
            if level is not None:
                builder.heading(level, line, number)
            else:
                builder.line(line, number)
    builder.flush()
    if not builder.sections and not any(p.strip() for p in pages):
        raise TextbookParseError("PDF không có chữ (có thể là ảnh quét): cần bản PDF có chữ hoặc DOCX")
    return builder.sections


def parse_textbook(data: bytes, file_type: str) -> list[Section]:
    if file_type == "docx":
        return parse_docx(data)
    if file_type == "pdf":
        return parse_pdf(data)
    raise TextbookParseError(f"Loại file không hỗ trợ: {file_type}")
