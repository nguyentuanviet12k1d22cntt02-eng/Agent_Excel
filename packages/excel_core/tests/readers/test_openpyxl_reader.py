from datetime import datetime
from pathlib import Path

import openpyxl
import pytest
from openpyxl.chart import BarChart, PieChart, Reference
from openpyxl.packaging.custom import StringProperty
from openpyxl.styles import Alignment, Border, Color, Font, PatternFill, Side

from excel_core.readers import (
    EXERCISE_ID_PROPERTY,
    display_column_width,
    find_uncalculated_formulas,
    full_request,
    read_workbook,
)
from excel_core.snapshot import (
    CELL_GROUPS,
    ErrorValue,
    PropertyGroup,
    RangeRequest,
    ReadRequest,
    SheetRequest,
    SnapshotMissingError,
)

SHEET = "Bài 01"


def build_workbook(path: Path) -> Path:
    """Workbook nhỏ có đủ loại dữ liệu và đối tượng mà bộ đọc phải hiểu."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = SHEET
    ws.append(["Tên hàng", "Số lượng", "Đơn giá", "Ngày"])
    rows = [("Bút", 10, 3.5), ("Vở", 20, 7), ("Thước", 5, 2.25), ("Kéo", 8, 15)]
    for i, (name, qty, price) in enumerate(rows, start=2):
        ws.append([name, qty, price, datetime(2026, 11, i)])
    ws["E2"] = "=B2*C2"
    ws["E3"] = "#DIV/0!"
    ws["F2"] = True
    ws["F3"] = "1250"  # số gõ dạng chữ
    ws["B2"].number_format = '_(* #,##0_);_(* \\(#,##0\\);_(* "-"??_);_(@_)'
    ws["C2"].number_format = "#,##0.00"
    ws["A1"].font = Font(name="Arial", size=12, bold=True, italic=True, underline="single", color="FFC00000")
    ws["A1"].fill = PatternFill("solid", fgColor=Color(theme=4, tint=0.3999755851924192))
    ws["B1"].fill = PatternFill("solid", fgColor="FFFFFF00")
    ws["A1"].border = Border(top=Side("thin"), bottom=Side("double"))
    ws["B2"].alignment = Alignment(horizontal="right", vertical="center", wrap_text=True)
    ws["C1"].alignment = Alignment(horizontal="centerContinuous")
    ws.merge_cells("H1:J1")
    ws.row_dimensions[4].hidden = True
    ws.row_dimensions[2].height = 30
    ws.column_dimensions["A"].width = 20
    ws.column_dimensions.group("K", "L", hidden=True)
    ws.auto_filter.ref = "A1:D5"
    ws.auto_filter.add_filter_column(1, ["10", "20"])
    ws.page_setup.orientation = "landscape"
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.print_options.horizontalCentered = True
    ws.print_area = "A1:F5"
    ws.oddFooter.center.text = "Trang &P"
    chart = BarChart()
    chart.type = "col"
    chart.title = "Số lượng bán"
    chart.add_data(Reference(ws, min_col=2, min_row=1, max_row=5), titles_from_data=True)
    chart.set_categories(Reference(ws, min_col=1, min_row=2, max_row=5))
    ws.add_chart(chart, "H3")
    pie = PieChart()
    pie.add_data(Reference(ws, min_col=3, min_row=1, max_row=5), titles_from_data=True)
    ws.add_chart(pie, "H20")
    wb.create_sheet("Ghi chú")
    wb.custom_doc_props.append(StringProperty(name=EXERCISE_ID_PROPERTY, value="b99-thu-nghiem"))
    out = path / "sample.xlsx"
    wb.save(out)
    return out


@pytest.fixture
def snapshot(tmp_path: Path):
    return read_workbook(build_workbook(tmp_path))


def test_workbook_level_information(snapshot):
    assert snapshot.source == "openpyxl"
    assert snapshot.sheet_names == (SHEET, "Ghi chú")
    assert snapshot.active_sheet == SHEET
    assert snapshot.exercise_id == "b99-thu-nghiem"


def test_values_are_normalized(snapshot):
    sheet = snapshot.sheet(SHEET)
    assert (sheet.cell("B2").value, sheet.cell("B2").value_kind) == (10.0, "number")
    assert isinstance(sheet.cell("B2").value, float)
    assert (sheet.cell("A2").value, sheet.cell("A2").value_kind) == ("Bút", "text")
    assert sheet.cell("D2").value == datetime(2026, 11, 2)
    assert sheet.cell("D2").value_kind == "date"
    assert sheet.cell("E3").value == ErrorValue("#DIV/0!")
    assert sheet.cell("F2").value_kind == "logical"
    assert sheet.cell("F3").value_kind == "text"  # để value_type bắt được stored_as_text
    assert sheet.cell("Z99").is_empty


def test_formula_without_excel_cache_has_no_value(snapshot):
    cell = snapshot.sheet(SHEET).cell("E2")
    assert (cell.formula, cell.formula_r1c1) == ("=B2*C2", "=RC[-3]*RC[-2]")
    assert cell.value is None  # file chưa qua Excel: không có giá trị cache


def test_number_formats_are_parsed(snapshot):
    sheet = snapshot.sheet(SHEET)
    comma = sheet.cell("B2").number_format
    assert (comma.category, comma.decimals, comma.thousands_separator) == ("accounting", 0, True)
    assert sheet.cell("C2").number_format.decimals == 2
    assert sheet.cell("A2").number_format.category == "general"


def test_styles_are_normalized(snapshot):
    sheet = snapshot.sheet(SHEET)
    a1 = sheet.cell("A1")
    assert (a1.font.name, a1.font.size, a1.font.bold, a1.font.italic, a1.font.underline) == (
        "Arial",
        12.0,
        True,
        True,
        True,
    )
    assert a1.font.color == "#C00000"
    # File openpyxl tạo dùng theme Office 2007: accent1 4F81BD, "Lighter 40%" Excel hiển thị 95B3D7
    assert a1.fill.color in ("#95B3D7", "#95B2D7")  # lệch ±1 so với Excel là chấp nhận được
    assert sheet.cell("B1").fill.color == "#FFFF00"
    assert sheet.cell("A2").fill.color is None
    assert (a1.border.top, a1.border.bottom, a1.border.left) == ("thin", "double", None)
    assert sheet.cell("B2").alignment.horizontal == "right"
    assert sheet.cell("B2").alignment.vertical == "center"
    assert sheet.cell("B2").alignment.wrap_text is True
    assert sheet.cell("C1").alignment.horizontal == "center_across"
    assert sheet.cell("A2").alignment.horizontal == "general"
    assert sheet.cell("A2").font.color == "#000000"


def test_structure(snapshot):
    sheet = snapshot.sheet(SHEET)
    assert "H1:J1" in sheet.merged
    assert sheet.hidden_rows == {4}
    assert sheet.row_heights[2] == 30.0
    assert sheet.row_heights[4] == 0.0  # ẩn: giống COM
    assert sheet.row_heights[3] == 15.0
    assert sheet.col_widths["A"] == display_column_width(20)


def test_hidden_column_group_is_expanded(tmp_path: Path):
    path = build_workbook(tmp_path)
    request = ReadRequest((RangeRequest(SHEET, "A1:M5", frozenset({PropertyGroup.STRUCTURE})),))
    sheet = read_workbook(path, request).sheet(SHEET)
    assert sheet.hidden_cols == {"K", "L"}
    assert sheet.col_widths["M"] == pytest.approx(8.43)


def test_autofilter_columns_by_header(snapshot):
    af = snapshot.sheet(SHEET).autofilter
    assert af.range == "A1:D5"
    assert dict(af.columns) == {"Số lượng": ("10", "20")}


def test_page_setup(snapshot):
    ps = snapshot.sheet(SHEET).page_setup
    assert (ps.orientation, ps.paper_size) == ("landscape", "A4")
    assert ps.fit_to_pages == (1, None)
    assert ps.center_horizontally is True
    assert ps.print_area == "A1:F5"
    assert ps.header_footer == {"footer_center": "Trang &P"}
    assert ps.margins_cm[2] == pytest.approx(0.75 * 2.54, abs=0.01)


def test_charts(snapshot):
    column, pie = snapshot.sheet(SHEET).charts
    assert (column.chart_type, column.title) == ("column", "Số lượng bán")
    assert column.series[0].values_ref == f"{SHEET}!B2:B5"
    assert column.series[0].categories_ref == f"{SHEET}!A2:A5"
    assert column.series[0].name_ref == f"{SHEET}!B1"
    assert pie.chart_type == "pie"
    assert pie.title is None


def test_request_limits_what_is_read(tmp_path: Path):
    path = build_workbook(tmp_path)
    request = ReadRequest(
        ranges=(RangeRequest(SHEET, "B2:C3", frozenset({PropertyGroup.VALUES})),),
        sheets=(SheetRequest(SHEET, frozenset({PropertyGroup.PAGE_SETUP})),),
    )
    snapshot = read_workbook(path, request)
    sheet = snapshot.sheet(SHEET)
    assert set(snapshot.sheets) == {SHEET}
    assert sheet.cell("B2").value == 10.0
    assert sheet.cell("B2").number_format is None
    assert sheet.cell("A1").is_empty  # ngoài vùng yêu cầu
    assert sheet.page_setup is not None
    assert sheet.autofilter is None
    with pytest.raises(SnapshotMissingError):
        sheet.require("B2", PropertyGroup.NUMBER_FORMAT)
    with pytest.raises(SnapshotMissingError):
        sheet.require_sheet_group(PropertyGroup.FILTER)


def test_full_request_covers_every_worksheet(tmp_path: Path):
    request = full_request(build_workbook(tmp_path))
    assert {r.sheet for r in request.ranges} == {SHEET, "Ghi chú"}
    assert all(r.groups == CELL_GROUPS for r in request.ranges)


def test_display_column_width_matches_excel():
    assert display_column_width(9.140625) == 8.43
    assert display_column_width(0) == 0.0


def test_excel_saved_solution_has_formula_values(b22_files):
    _, solution = b22_files
    sheet = read_workbook(solution).sheet("Bài 01")
    f9 = sheet.cell("F9")
    parts = [sheet.cell(a).value for a in ("C9", "D9", "E9")]
    assert f9.formula == "=SUM(C9:E9)"
    assert f9.value == pytest.approx(sum(parts))
    assert {sheet.cell(f"F{r}").formula_r1c1 for r in range(9, 20)} == {"=SUM(RC[-3]:RC[-1])"}
    assert sheet.cell("B9").value_kind == "date"


def test_find_uncalculated_formulas(tmp_path: Path, b22_files):
    # File openpyxl tạo: công thức chưa có giá trị; file Excel đã lưu: đủ giá trị
    assert find_uncalculated_formulas(build_workbook(tmp_path)) == [f"{SHEET}!E2"]
    _, solution = b22_files
    assert find_uncalculated_formulas(solution) == []
