"""Đọc chữ trong shape của file .xlsx (đề bài 06 ghi các bước thực hành trong một khối hình chữ nhật)."""

import zipfile
from pathlib import Path

import openpyxl

from excel_core.readers.shapes import shape_texts

XDR = "http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
DRAWING_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/drawing"


def _shape(name: str, paragraphs: list[str], row: int, col: int) -> str:
    body = "".join(f"<a:p><a:r><a:t>{text}</a:t></a:r></a:p>" for text in paragraphs)
    return (
        f"<xdr:twoCellAnchor><xdr:from><xdr:col>{col}</xdr:col><xdr:row>{row}</xdr:row></xdr:from>"
        f'<xdr:sp><xdr:nvSpPr><xdr:cNvPr id="2" name="{name}"/></xdr:nvSpPr><xdr:txBody>{body}</xdr:txBody>'
        "</xdr:sp></xdr:twoCellAnchor>"
    )


def build(path: Path) -> Path:
    """File có sheet "Bài tập" vẽ hai shape có chữ (một nằm trong nhóm) và một shape không chữ."""
    wb = openpyxl.Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "Bài tập"
    ws["B2"] = "PHIẾU NHẬP KHO"
    wb.create_sheet("Khác")
    wb.save(path)
    steps = _shape("Rectangle 2", ["Hiển thị cột E", "", "Chèn  cột trống phía sau cột G"], row=1, col=10)
    grouped = (
        "<xdr:twoCellAnchor><xdr:from><xdr:col>5</xdr:col><xdr:row>20</xdr:row></xdr:from><xdr:grpSp>"
        + _shape("Arrow 5", ["Mẫu"], 0, 0)[len("<xdr:twoCellAnchor>") : -len("</xdr:twoCellAnchor>")]
        + "</xdr:grpSp></xdr:twoCellAnchor>"
    )
    empty = _shape("Picture 3", [], row=0, col=0)
    drawing = f'<xdr:wsDr xmlns:xdr="{XDR}" xmlns:a="{A}">{grouped}{empty}{steps}</xdr:wsDr>'
    rels = (
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f'<Relationship Id="rId1" Type="{DRAWING_REL}" Target="../drawings/drawing1.xml"/></Relationships>'
    )
    with zipfile.ZipFile(path, "a") as archive:
        archive.writestr("xl/drawings/drawing1.xml", drawing)
        archive.writestr("xl/worksheets/_rels/sheet1.xml.rels", rels)
    return path


def test_shape_text_is_read_per_paragraph_in_position_order(tmp_path: Path):
    shapes = shape_texts(build(tmp_path / "de.xlsx"))

    assert [(s.sheet, s.name, s.lines) for s in shapes] == [
        ("Bài tập", "Rectangle 2", ("Hiển thị cột E", "Chèn cột trống phía sau cột G")),
        ("Bài tập", "Arrow 5", ("Mẫu",)),
    ]
    assert (shapes[0].row, shapes[0].col) == (2, 11)


def test_workbook_without_drawings_has_no_shape_text(tmp_path: Path):
    path = tmp_path / "trong.xlsx"
    openpyxl.Workbook().save(path)
    assert shape_texts(path) == []


def test_broken_drawing_is_skipped_not_fatal(tmp_path: Path):
    path = build(tmp_path / "de.xlsx")
    broken = tmp_path / "hong.xlsx"
    with zipfile.ZipFile(path) as source, zipfile.ZipFile(broken, "w") as target:
        for item in source.infolist():
            data = b"<xdr:wsDr" if item.filename == "xl/drawings/drawing1.xml" else source.read(item.filename)
            target.writestr(item, data)
    assert shape_texts(broken) == []
    not_a_zip = tmp_path / "khong-phai.xlsx"
    not_a_zip.write_bytes(b"abc")
    assert shape_texts(not_a_zip) == []
