"""Công cụ dựng snapshot nhanh cho test điều kiện (dùng qua fixture `kit`)."""

from datetime import datetime
from types import SimpleNamespace

import pytest

from excel_core.address import parse_cell
from excel_core.checks import CheckContext, CheckResult, run_check
from excel_core.formula import normalize_formula, to_r1c1
from excel_core.snapshot import (
    CELL_GROUPS,
    SHEET_GROUPS,
    CellSnapshot,
    RangeRead,
    SheetSnapshot,
    WorkbookSnapshot,
    parse_number_format,
)

SHEET = "S"


def number(value: float, fmt: str | None = None, **extra) -> CellSnapshot:
    return CellSnapshot(
        value=float(value), value_kind="number", number_format=parse_number_format(fmt), **extra
    )


def text(value: str, **extra) -> CellSnapshot:
    return CellSnapshot(value=value, value_kind="text", **extra)


def formula(address: str, a1: str, value: float | None = None, **extra) -> CellSnapshot:
    col, row = parse_cell(address)
    kind = "empty" if value is None else "number"
    return CellSnapshot(
        value=None if value is None else float(value),
        value_kind=kind,
        formula=normalize_formula(a1),
        formula_r1c1=to_r1c1(a1, row, col),
        **extra,
    )


def sheet(cells: dict[str, CellSnapshot] | None = None, *, name: str = SHEET, read: str = "A1:Z60", **fields):
    return SheetSnapshot(
        name=name,
        cells=cells or {},
        read_ranges=(RangeRead(read, CELL_GROUPS),),
        sheet_groups=SHEET_GROUPS,
        **fields,
    )


def book(*sheets: SheetSnapshot | dict[str, CellSnapshot], names: tuple[str, ...] | None = None, **fields):
    built = [s if isinstance(s, SheetSnapshot) else sheet(s, **fields) for s in (sheets or ({},))]
    return WorkbookSnapshot(
        source="openpyxl",
        taken_at=datetime(2026, 11, 7),
        exercise_id=None,
        sheet_names=names or tuple(s.name for s in built),
        active_sheet=built[0].name,
        sheets={s.name: s for s in built},
    )


def ctx(current: WorkbookSnapshot, **references) -> CheckContext:
    return CheckContext(current=current, default_sheet=SHEET, **references)


def run(check: dict, current: WorkbookSnapshot, **references) -> CheckResult:
    return run_check(check, ctx(current, **references))


@pytest.fixture
def kit() -> SimpleNamespace:
    return SimpleNamespace(
        SHEET=SHEET, number=number, text=text, formula=formula, sheet=sheet, book=book, ctx=ctx, run=run
    )
