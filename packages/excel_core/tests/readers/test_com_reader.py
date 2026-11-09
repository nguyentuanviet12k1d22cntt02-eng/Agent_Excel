"""Bộ đọc COM cho cùng kết quả với bộ đọc openpyxl trên các bài tự soạn (T7.2).

Cần Excel thật: đặt biến môi trường EXCEL_TESTS=1 rồi chạy pytest với `-m excel`. Mở một phiên
Excel riêng (DispatchEx, ẩn), mở file ở chế độ chỉ đọc, đóng phiên trong `finally`: không động vào Excel đang
mở của người dùng (quy tắc code 2.3 mục 4).

Chỗ khác hợp lệ giữa hai bộ đọc (so theo ý nghĩa, như điều kiện kiểm vẫn so):
- mã định dạng số: cùng loại, số lẻ, dấu nghìn, mẫu ngày; chuỗi mã có thể khác ("\\(" và "(", "mm-dd-yy" và
  "m/d/yyyy");
- viền: COM thấy cả cạnh chung do ô bên cạnh kẻ (điều kiện border vốn chấp nhận cả hai phía);
- độ rộng cột: Excel làm tròn theo pixel của màn hình (150% → 8,09 thay vì 8,43), lệch dưới 0,5 ký tự;
- khổ giấy: file không ghi thì Excel báo theo máy in mặc định;
- vùng in cả cột ($B:$J): openpyxl bỏ qua (có cảnh báo), COM đọc được B1:J1048576.
"""

import os
import random
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from excel_core.address import CellRange, parse_range
from excel_core.readers import full_request, read_workbook
from excel_core.snapshot import (
    BorderInfo,
    CellSnapshot,
    PropertyGroup,
    RangeRequest,
    ReadRequest,
    SheetSnapshot,
)

pytestmark = [
    pytest.mark.excel,
    pytest.mark.skipif(os.environ.get("EXCEL_TESTS") != "1", reason="cần Excel thật: đặt EXCEL_TESTS=1"),
]

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
WIDTH_TOLERANCE = 0.5  # ký tự, bằng dung sai mặc định của điều kiện row_col_size
COLOR_TOLERANCE = 1  # mỗi kênh màu: màu theme + độ sáng quy đổi lệch ±1 (snapshot.md)


@pytest.fixture(scope="module")
def excel() -> Iterator[Any]:
    import pythoncom  # noqa: PLC0415
    import win32com.client  # noqa: PLC0415

    pythoncom.CoInitialize()
    app = win32com.client.DispatchEx("Excel.Application")
    app.Visible = False
    app.DisplayAlerts = False
    try:
        yield app
    finally:
        for index in range(app.Workbooks.Count, 0, -1):
            app.Workbooks(index).Close(SaveChanges=False)
        app.Quit()
        del app
        pythoncom.CoUninitialize()


def _color_close(a: str | None, b: str | None) -> bool:
    if a is None or b is None:
        return a == b
    return all(abs(int(a[i : i + 2], 16) - int(b[i : i + 2], 16)) <= COLOR_TOLERANCE for i in (1, 3, 5))


def _edges(sheet: SheetSnapshot) -> set[tuple[int, int, str, str]]:
    """Mọi cạnh có viền, quy về một cách ghi (cạnh dưới ô trên = cạnh trên ô dưới)."""
    from excel_core.address import parse_cell  # noqa: PLC0415

    found = set()
    for address, cell in sheet.cells.items():
        col, row = parse_cell(address)
        border = cell.border or BorderInfo()
        for side, style in (
            ("top", border.top),
            ("bottom", border.bottom),
            ("left", border.left),
            ("right", border.right),
        ):
            if style is None:
                continue
            if side == "bottom":
                found.add((col, row + 1, "h", style))
            elif side == "top":
                found.add((col, row, "h", style))
            elif side == "right":
                found.add((col + 1, row, "v", style))
            else:
                found.add((col, row, "v", style))
    return found


def _assert_cells_match(address: str, a: CellSnapshot, b: CellSnapshot) -> None:
    assert (a.value, a.value_kind, a.formula, a.formula_r1c1) == (
        b.value,
        b.value_kind,
        b.formula,
        b.formula_r1c1,
    ), address
    if a.number_format or b.number_format:
        fa, fb = a.number_format, b.number_format
        assert fa and fb, address
        assert (fa.category, fa.decimals, fa.thousands_separator, fa.date_pattern) == (
            fb.category,
            fb.decimals,
            fb.thousands_separator,
            fb.date_pattern,
        ), address
    if a.font or b.font:
        assert a.font and b.font, address
        assert (a.font.name, a.font.size, a.font.bold, a.font.italic, a.font.underline) == (
            b.font.name,
            b.font.size,
            b.font.bold,
            b.font.italic,
            b.font.underline,
        ), address
        assert _color_close(a.font.color, b.font.color), (address, a.font.color, b.font.color)
    if a.fill or b.fill:
        assert _color_close(a.fill.color if a.fill else None, b.fill.color if b.fill else None), address
    assert a.alignment == b.alignment, address


CASES = [(folder, name) for folder in ("b09", "b14", "b16", "b22") for name in ("de.xlsx", "dap-an.xlsx")]


@pytest.mark.parametrize(("folder", "name"), CASES)
def test_com_reader_matches_openpyxl(excel: Any, folder: str, name: str):
    from excel_core.readers.com_reader import read_workbook_com  # noqa: PLC0415

    path = FIXTURES / folder / name
    request = full_request(path)
    from_file = read_workbook(path, request)
    workbook = excel.Workbooks.Open(str(path), UpdateLinks=0, ReadOnly=True)
    try:
        from_com = read_workbook_com(workbook, request)
    finally:
        workbook.Close(SaveChanges=False)

    assert from_com.sheet_names == from_file.sheet_names
    for sheet_name, a in from_file.sheets.items():
        b = from_com.sheets[sheet_name]
        for address in set(a.cells) | set(b.cells):
            _assert_cells_match(address, a.cell(address), b.cell(address))
        assert _edges(a) <= _edges(b)
        assert set(a.merged) == set(b.merged)
        assert (a.hidden_rows, a.hidden_cols) == (b.hidden_rows, b.hidden_cols)
        assert a.row_heights == b.row_heights
        assert a.col_widths.keys() == b.col_widths.keys()
        assert all(abs(a.col_widths[c] - b.col_widths[c]) < WIDTH_TOLERANCE for c in a.col_widths)
        assert a.autofilter == b.autofilter
        assert a.charts == b.charts
        if a.page_setup and b.page_setup:
            pa, pb = a.page_setup, b.page_setup
            assert (pa.orientation, pa.margins_cm, pa.fit_to_pages, pa.print_area) == (
                pb.orientation,
                pb.margins_cm,
                pb.fit_to_pages,
                pb.print_area,
            )
            assert pa.paper_size in (None, pb.paper_size)


# Tiêu đề gộp tràn qua nhiều cột (như "PHIẾU NHẬP KHO" B9:J9 của bài 06), ô gộp dọc, chữ nhật, sát nhau
MERGES = ("B2:G2", "B4:B5", "D4:E4", "F6:F9", "H3:I8", "C10:D10", "J1:J12")


def _merged_book(path: Path) -> Path:
    import openpyxl  # noqa: PLC0415

    wb = openpyxl.Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "S"
    ws["B2"] = "TIÊU ĐỀ"
    for rng in MERGES:
        ws.merge_cells(rng)
    for col in range(1, 12):
        ws.cell(14, col, col)
    ws.column_dimensions["E"].hidden = True
    ws.row_dimensions[7].hidden = True
    wb.save(path)
    return path


def test_reading_keeps_the_users_selection(excel: Any, tmp_path: Path):
    """Đọc Range.MergeCells làm Excel nới vùng chọn của người dùng theo ô gộp (bài 06: chọn cột H, app đọc
    lại thì thành B:J). Bộ đọc không được làm đổi vùng chọn, với mọi nhóm thuộc tính."""
    from excel_core.readers.com_reader import full_request_com, read_workbook_com  # noqa: PLC0415

    workbook = excel.Workbooks.Open(str(_merged_book(tmp_path / "gop.xlsx")), ReadOnly=True)
    try:
        ws = workbook.Worksheets("S")
        ws.Activate()
        # Bấm chuột vào tiêu đề cột thì Excel KHÔNG nới theo ô gộp; lệnh Select qua COM thì có. Tạo lại trạng
        # thái bấm chuột: bỏ gộp, chọn cột D, gộp lại
        for rng in MERGES:
            ws.Range(rng).UnMerge()
        ws.Range("D:D").Select()
        for rng in MERGES:
            ws.Range(rng).Merge()
        assert str(excel.Selection.Address) == "$D:$D"

        snapshot = read_workbook_com(workbook, full_request_com(workbook))

        assert str(excel.Selection.Address) == "$D:$D"
        assert set(snapshot.sheets["S"].merged) == set(MERGES)
    finally:
        workbook.Close(SaveChanges=False)


def test_merged_cells_cutting_the_read_range_are_all_found(excel: Any, tmp_path: Path):
    """Ô gộp cắt mép vùng đọc (bắt đầu trước, tràn sau, nằm trong) đều được tìm thấy, đúng địa chỉ."""
    from excel_core.readers.com_reader import read_workbook_com  # noqa: PLC0415

    workbook = excel.Workbooks.Open(str(_merged_book(tmp_path / "gop.xlsx")), ReadOnly=True)
    try:
        merges = [parse_range(m) for m in MERGES]
        rng = random.Random(6)
        for _ in range(60):
            r1, r2 = sorted(rng.sample(range(1, 16), 2))
            c1, c2 = sorted(rng.sample(range(1, 13), 2))
            box = CellRange(c1, r1, c1 if rng.random() < 0.3 else c2, r1 if rng.random() < 0.3 else r2)
            request = ReadRequest((RangeRequest("S", str(box), frozenset({PropertyGroup.STRUCTURE})),))
            found = set(read_workbook_com(workbook, request).sheets["S"].merged)
            assert found == {str(m) for m in merges if m.intersects(box)}, str(box)
    finally:
        workbook.Close(SaveChanges=False)
