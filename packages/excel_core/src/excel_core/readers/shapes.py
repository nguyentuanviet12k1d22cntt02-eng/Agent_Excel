"""Chữ trong shape, hộp văn bản của file .xlsx (đề bài thường ghi yêu cầu từng bước trong một khối shape).

openpyxl bỏ qua shape khi đọc, nên đọc thẳng phần vẽ (xl/drawings/drawingN.xml) trong gói .xlsx: sheet → quan
hệ `drawing` → các `xdr:sp` (kể cả nằm trong nhóm `xdr:grpSp`), mỗi đoạn `a:p` là một dòng.
"""

import logging
import posixpath
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree

_MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
_PKG_REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"
_XDR = "{http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing}"
_A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
_DRAWING_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/drawing"
_ANCHORS = (f"{_XDR}twoCellAnchor", f"{_XDR}oneCellAnchor", f"{_XDR}absoluteAnchor")

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ShapeText:
    sheet: str
    name: str  # tên shape trong Excel ("Rectangle 2")
    lines: tuple[str, ...]  # mỗi đoạn văn một dòng, đã bỏ đoạn trống
    row: int  # góc trên trái (tính từ 1), để xếp các shape theo vị trí trên trang tính
    col: int


def _rels(archive: zipfile.ZipFile, part: str) -> dict[str, tuple[str, str]]:
    """rId → (loại quan hệ, đường dẫn đích trong gói) của một phần."""
    folder, name = posixpath.split(part)
    rels_path = posixpath.join(folder, "_rels", f"{name}.rels")
    if rels_path not in archive.namelist():
        return {}
    root = ElementTree.fromstring(archive.read(rels_path))
    found = {}
    for rel in root.iter(f"{_PKG_REL}Relationship"):
        target = rel.get("Target", "")
        path = (
            target.lstrip("/")
            if target.startswith("/")
            else posixpath.normpath(posixpath.join(folder, target))
        )
        found[rel.get("Id", "")] = (rel.get("Type", ""), path)
    return found


def _sheet_parts(archive: zipfile.ZipFile) -> list[tuple[str, str]]:
    """(tên sheet, đường dẫn phần sheet) theo thứ tự trong workbook."""
    workbook = "xl/workbook.xml"
    rels = _rels(archive, workbook)
    root = ElementTree.fromstring(archive.read(workbook))
    sheets = []
    for sheet in root.iter(f"{_MAIN}sheet"):
        rel = rels.get(sheet.get(f"{_REL}id", ""))
        if rel:
            sheets.append((sheet.get("name", ""), rel[1]))
    return sheets


def _paragraphs(shape: ElementTree.Element) -> tuple[str, ...]:
    lines = []
    for paragraph in shape.iter(f"{_A}p"):
        text = "".join(t.text or "" for t in paragraph.iter(f"{_A}t"))
        text = " ".join(text.split())
        if text:
            lines.append(text)
    return tuple(lines)


def _anchor_cell(anchor: ElementTree.Element) -> tuple[int, int]:
    start = anchor.find(f"{_XDR}from")
    if start is None:
        return 0, 0
    row, col = start.findtext(f"{_XDR}row"), start.findtext(f"{_XDR}col")
    return int(row or 0) + 1, int(col or 0) + 1


def _drawing_shapes(xml: bytes, sheet: str) -> list[ShapeText]:
    found = []
    for anchor in ElementTree.fromstring(xml):
        if anchor.tag not in _ANCHORS:
            continue
        row, col = _anchor_cell(anchor)
        for shape in anchor.iter(f"{_XDR}sp"):
            lines = _paragraphs(shape)
            if lines:
                props = shape.find(f"{_XDR}nvSpPr/{_XDR}cNvPr")
                name = props.get("name", "") if props is not None else ""
                found.append(ShapeText(sheet, name, lines, row, col))
    return found


def shape_texts(path: Path | str) -> list[ShapeText]:
    """Chữ trong mọi shape có chữ, theo sheet rồi theo vị trí (trên xuống, trái sang).

    Chữ trong hình chỉ là thông tin thêm cho AI: phần vẽ hỏng hay lạ thì bỏ qua, không làm hỏng việc sinh.
    """
    shapes: list[ShapeText] = []
    try:
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
            for sheet, part in _sheet_parts(archive):
                on_sheet = []
                for kind, target in _rels(archive, part).values():
                    if kind != _DRAWING_TYPE or target not in names:
                        continue
                    try:
                        on_sheet += _drawing_shapes(archive.read(target), sheet)
                    except ElementTree.ParseError, ValueError:
                        logger.warning("Bỏ qua phần vẽ không đọc được: %s", target)
                shapes += sorted(on_sheet, key=lambda s: (s.row, s.col))
    except OSError, KeyError, zipfile.BadZipFile, ElementTree.ParseError:
        logger.warning("Không đọc được chữ trong hình vẽ của %s", path, exc_info=True)
        return []
    return shapes
