from datetime import datetime
from pathlib import Path

from excel_core.diff import ChangeKind, diff_files, diff_workbooks
from excel_core.snapshot import (
    ALL_GROUPS,
    CELL_GROUPS,
    SHEET_GROUPS,
    AutoFilterInfo,
    CellSnapshot,
    ChartInfo,
    PageSetupInfo,
    PropertyGroup,
    RangeRead,
    SheetSnapshot,
    WorkbookSnapshot,
    parse_number_format,
)

S = "Bài 01"


def workbook(*sheets: SheetSnapshot, names: tuple[str, ...] | None = None) -> WorkbookSnapshot:
    return WorkbookSnapshot(
        source="openpyxl",
        taken_at=datetime(2026, 11, 7),
        exercise_id=None,
        sheet_names=names or tuple(s.name for s in sheets),
        active_sheet=None,
        sheets={s.name: s for s in sheets},
    )


def sheet(cells: dict[str, CellSnapshot] | None = None, **extra) -> SheetSnapshot:
    return SheetSnapshot(
        name=S,
        cells=cells or {},
        read_ranges=(RangeRead("A1:J30", CELL_GROUPS),),
        sheet_groups=SHEET_GROUPS,
        **extra,
    )


def kinds_and_ranges(diff) -> set[tuple[ChangeKind, str | None]]:
    return {(c.kind, c.range) for c in diff}


def test_b09_fixture_diff(b09_files: tuple[Path, Path]):
    diff = diff_files(*b09_files)
    assert kinds_and_ranges(diff) == {
        (ChangeKind.VALUE, "F10:G14"),
        (ChangeKind.VALUE, "I10:I14"),
        (ChangeKind.NUMBER_FORMAT, "F10:F14"),
        (ChangeKind.NUMBER_FORMAT, "G10:H14"),
        (ChangeKind.NUMBER_FORMAT, "I10:I14"),
        (ChangeKind.ALIGNMENT, "F10:I14"),
    }
    # H10:H14 cùng công thức ở hai file: giá trị khác nhau chỉ là hệ quả, không tính là thay đổi
    assert not diff.of_kind(ChangeKind.FORMULA)


def test_b22_fixture_groups_copied_formulas(b22_files: tuple[Path, Path]):
    diff = diff_files(*b22_files)
    formulas = diff.of_kind(ChangeKind.FORMULA)
    assert [(c.range, c.after) for c in formulas] == [
        ("F9:F19", "=SUM(C9:E9) (R1C1 =SUM(RC[-3]:RC[-1]))"),
        ("C20:F20", "=SUM(C9:C19) (R1C1 =SUM(R[-11]C:R[-1]C))"),
    ]


def test_same_file_has_no_changes(b22_files: tuple[Path, Path]):
    starter, _ = b22_files
    assert len(diff_files(starter, starter)) == 0


def test_formula_overwritten_by_value():
    before = sheet({"H10": CellSnapshot(value=0.0, value_kind="number", formula="=F10*G10")})
    after = sheet({"H10": CellSnapshot(value=500.0, value_kind="number")})
    (change,) = diff_workbooks(workbook(before), workbook(after))
    assert (change.kind, change.range, change.before, change.after) == (
        ChangeKind.FORMULA,
        "H10",
        "=F10*G10",
        "số",
    )


def test_fields_not_read_on_both_sides_are_ignored():
    before = SheetSnapshot(
        name=S,
        cells={"A1": CellSnapshot(value=1.0, value_kind="number")},
        read_ranges=(RangeRead("A1", frozenset({PropertyGroup.VALUES})),),
    )
    after = sheet({"A1": CellSnapshot(value=1.0, value_kind="number", number_format=None)})
    assert len(diff_workbooks(workbook(before), workbook(after))) == 0


def test_structure_changes():
    before = sheet(row_heights={5: 15.0, 6: 15.0}, col_widths={"B": 8.43})
    after = sheet(
        merged=("B2:F2",),
        hidden_rows=frozenset({7, 8, 9}),
        hidden_cols=frozenset({"D"}),
        row_heights={5: 30.0, 6: 15.2},
        col_widths={"B": 20.0},
    )
    found = kinds_and_ranges(diff_workbooks(workbook(before), workbook(after)))
    assert found == {
        (ChangeKind.MERGED, "B2:F2"),
        (ChangeKind.ROW_HIDDEN, "7:9"),
        (ChangeKind.COL_HIDDEN, "D:D"),
        (ChangeKind.ROW_HEIGHT, "5:5"),  # dòng 6 lệch 0,2 pt: dưới ngưỡng
        (ChangeKind.COL_WIDTH, "B:B"),
    }


def test_sheet_object_changes():
    page = PageSetupInfo("portrait", "A4", (1.9, 1.9, 1.8, 1.8), (None, None), False, None, {})
    before = sheet(page_setup=page)
    after = sheet(
        page_setup=PageSetupInfo("landscape", "A4", (1.9, 1.9, 1.8, 1.8), (None, None), False, None, {}),
        autofilter=AutoFilterInfo("A1:F20", {"Đơn giá": (">=5",)}),
        charts=(ChartInfo("column", "Doanh thu", ()),),
    )
    diff = diff_workbooks(workbook(before), workbook(after))
    page_changes = diff.of_kind(ChangeKind.PAGE_SETUP)
    assert [(c.before, c.after) for c in page_changes] == [("orientation=portrait", "orientation=landscape")]
    assert diff.of_kind(ChangeKind.AUTOFILTER)[0].before == "không có"
    assert diff.of_kind(ChangeKind.CHART)
    assert not diff.cell_changes()  # thay đổi theo sheet không có địa chỉ ô


def test_sheet_added_and_removed():
    starter = workbook(sheet(), names=(S, "Nháp"))
    solution = workbook(sheet(), names=(S, "Tổng hợp"))
    found = kinds_and_ranges(diff_workbooks(starter, solution))
    assert found == {(ChangeKind.SHEET_ADDED, None), (ChangeKind.SHEET_REMOVED, None)}


def test_to_text_is_one_line_per_change(b09_files: tuple[Path, Path]):
    text = diff_files(*b09_files).to_text()
    assert len(text.splitlines()) == 6
    assert "[2. Bang_Ke_Ban_Hang] F10:I14 alignment" in text


def test_all_groups_constant_is_complete():
    assert ALL_GROUPS == CELL_GROUPS | SHEET_GROUPS


def test_number_format_excel_copies_into_new_formula_is_ignored():
    # Gõ =SUM(C9:E9) vào ô General: Excel tự lấy định dạng của C9 (T2.6, b22)
    accounting = parse_number_format(r'_(* #,##0_);_(* \(#,##0\);_(* "-"??_);_(@_)')
    source = CellSnapshot(value=25000.0, value_kind="number", number_format=accounting)
    general = parse_number_format("General")
    before = sheet({"C9": source, "F9": CellSnapshot(number_format=general)})
    after = sheet(
        {
            "C9": source,
            "F9": CellSnapshot(
                value=25000.0, value_kind="number", formula="=SUM(C9:E9)", number_format=accounting
            ),
        }
    )
    diff = diff_workbooks(workbook(before), workbook(after))
    assert [c.kind for c in diff] == [ChangeKind.FORMULA]


def test_number_format_chosen_by_author_is_kept():
    percent = parse_number_format("0%")
    general = parse_number_format("General")
    source = CellSnapshot(value=5.0, value_kind="number", number_format=general)
    before = sheet({"C9": source, "F9": CellSnapshot(number_format=general)})
    after = sheet(
        {
            "C9": source,
            "F9": CellSnapshot(value=0.5, value_kind="number", formula="=C9/10", number_format=percent),
        }
    )
    kinds = {c.kind for c in diff_workbooks(workbook(before), workbook(after))}
    assert kinds == {ChangeKind.FORMULA, ChangeKind.NUMBER_FORMAT}
