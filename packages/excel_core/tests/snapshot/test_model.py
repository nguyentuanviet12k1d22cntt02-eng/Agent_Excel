import dataclasses
from datetime import datetime

import pytest

from excel_core.snapshot import (
    EMPTY_CELL,
    CellSnapshot,
    PropertyGroup,
    RangeRead,
    SheetSnapshot,
    SnapshotMissingError,
    WorkbookSnapshot,
)

VALUES = frozenset({PropertyGroup.VALUES})


def make_sheet() -> SheetSnapshot:
    return SheetSnapshot(
        name="Bài 01",
        cells={"F9": CellSnapshot(value=60.0, value_kind="number", formula="=SUM(C9:E9)")},
        read_ranges=(RangeRead("C9:F19", VALUES | {PropertyGroup.FORMULAS}),),
    )


def test_missing_cell_inside_read_range_is_empty():
    sheet = make_sheet()
    assert sheet.cell("C10") is EMPTY_CELL
    assert sheet.cell("C10").is_empty
    assert sheet.cell("F9").is_formula


def test_require_accepts_subrange_of_read_range():
    assert str(make_sheet().require("F9:F19", PropertyGroup.FORMULAS)) == "F9:F19"


@pytest.mark.parametrize(
    ("rng", "group"),
    [("F9:F20", PropertyGroup.VALUES), ("F9", PropertyGroup.NUMBER_FORMAT)],
)
def test_require_raises_when_request_did_not_cover(rng: str, group: PropertyGroup):
    with pytest.raises(SnapshotMissingError):
        make_sheet().require(rng, group)


def test_sheet_level_group_must_be_read():
    with pytest.raises(SnapshotMissingError):
        make_sheet().require_sheet_group(PropertyGroup.PAGE_SETUP)


def test_workbook_distinguishes_absent_sheet_from_unread_sheet():
    wb = WorkbookSnapshot(
        source="openpyxl",
        taken_at=datetime(2026, 11, 7),
        exercise_id=None,
        sheet_names=("Bài 01", "Bài 02"),
        active_sheet="Bài 01",
        sheets={"Bài 01": make_sheet()},
    )
    assert wb.sheet("Bài 01").name == "Bài 01"
    assert wb.has_sheet("Bài 02")
    with pytest.raises(SnapshotMissingError, match="chưa được đọc"):
        wb.sheet("Bài 02")
    with pytest.raises(SnapshotMissingError, match="không có sheet"):
        wb.sheet("Bài 03")


def test_snapshot_is_immutable():
    with pytest.raises(dataclasses.FrozenInstanceError):
        make_sheet().name = "khác"  # type: ignore[misc]
