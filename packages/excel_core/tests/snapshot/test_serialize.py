import json
from datetime import datetime

import pytest

from excel_core.snapshot import (
    ALL_GROUPS,
    AlignmentInfo,
    AutoFilterInfo,
    BorderInfo,
    CellSnapshot,
    ChartInfo,
    ChartSeriesInfo,
    ErrorValue,
    FillInfo,
    FontInfo,
    PageSetupInfo,
    PropertyGroup,
    RangeRead,
    SheetSnapshot,
    SnapshotFormatError,
    WorkbookSnapshot,
    parse_number_format,
    snapshot_from_dict,
    snapshot_to_dict,
)


def rich_snapshot() -> WorkbookSnapshot:
    cells = {
        "F10": CellSnapshot(
            value=1250.0,
            value_kind="number",
            number_format=parse_number_format("#,##0"),
            font=FontInfo("Calibri", 11.0, True, False, False, "#000000"),
            fill=FillInfo("#FFFF00"),
            border=BorderInfo(top="thin", bottom="double"),
            alignment=AlignmentInfo("right", "bottom", False),
        ),
        "H10": CellSnapshot(
            value=15625.0, value_kind="number", formula="=F10*G10", formula_r1c1="=RC[-2]*RC[-1]"
        ),
        "B10": CellSnapshot(value="Bút bi", value_kind="text"),
        "C10": CellSnapshot(value=datetime(2026, 11, 7, 8, 30), value_kind="date"),
        "D10": CellSnapshot(value=ErrorValue("#DIV/0!"), value_kind="error"),
        "E10": CellSnapshot(value=True, value_kind="logical"),
    }
    sheet = SheetSnapshot(
        name="2. Bang_Ke_Ban_Hang",
        cells=cells,
        read_ranges=(
            RangeRead("B9:I14", frozenset(ALL_GROUPS - {PropertyGroup.CHARTS} - {PropertyGroup.FILTER})),
        ),
        sheet_groups=frozenset({PropertyGroup.FILTER, PropertyGroup.PAGE_SETUP, PropertyGroup.CHARTS}),
        merged=("B2:I2",),
        hidden_rows=frozenset({12, 13}),
        hidden_cols=frozenset({"K"}),
        row_heights={9: 30.0},
        col_widths={"B": 8.43},
        autofilter=AutoFilterInfo("B9:I14", {"Đơn giá": (">=5",)}),
        page_setup=PageSetupInfo(
            orientation="landscape",
            paper_size="A4",
            margins_cm=(1.9, 1.9, 1.8, 1.8),
            fit_to_pages=(1, None),
            center_horizontally=True,
            print_area="B2:I22",
            header_footer={"footer_center": "Trang &P"},
        ),
        charts=(ChartInfo("column", "Số lượng", (ChartSeriesInfo("S!F9", "S!D10:D14", "S!F10:F14"),)),),
    )
    return WorkbookSnapshot(
        source="openpyxl",
        taken_at=datetime(2026, 11, 7, 9, 0),
        exercise_id="b09-du-lieu-dang-so",
        sheet_names=("1. Thuc_Hanh", "2. Bang_Ke_Ban_Hang"),
        active_sheet="2. Bang_Ke_Ban_Hang",
        sheets={sheet.name: sheet},
    )


def test_round_trip_through_json_keeps_everything():
    original = rich_snapshot()
    text = json.dumps(snapshot_to_dict(original), ensure_ascii=False)
    restored = snapshot_from_dict(json.loads(text))
    assert restored == original


def test_integer_numbers_come_back_as_float():
    data = snapshot_to_dict(rich_snapshot())
    data["snapshot"]["sheets"]["2. Bang_Ke_Ban_Hang"]["cells"]["F10"]["value"] = 1250
    value = snapshot_from_dict(data).sheets["2. Bang_Ke_Ban_Hang"].cells["F10"].value
    assert value == 1250.0
    assert isinstance(value, float)


def test_default_fields_are_omitted_to_keep_logs_small():
    data = snapshot_to_dict(rich_snapshot())
    assert data["snapshot"]["sheets"]["2. Bang_Ke_Ban_Hang"]["cells"]["B10"] == {
        "value": "Bút bi",
        "value_kind": "text",
    }


def test_unknown_format_version_is_rejected():
    with pytest.raises(SnapshotFormatError):
        snapshot_from_dict({"format_version": 99, "snapshot": {}})
