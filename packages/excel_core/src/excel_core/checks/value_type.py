"""value_type — mọi ô trong vùng đúng kiểu dữ liệu (số, ngày, chữ, đúng/sai)."""

from excel_core.checks.base import (
    CheckContext,
    CheckResult,
    CheckSpec,
    Failures,
    Read,
    cell_read,
    check_range,
)
from excel_core.checks.values import is_number_stored_as_text, looks_like_date, looks_like_logical
from excel_core.snapshot import CellSnapshot, PropertyGroup

TYPE = "value_type"
CODES = ("stored_as_text", "wrong_type", "empty")


def reads(check: CheckSpec, sheet: str) -> list[Read]:
    return [cell_read("current", sheet, check["range"], PropertyGroup.VALUES)]


def _stored_as_text(cell: CellSnapshot, kind: str) -> bool:
    if cell.value_kind != "text" or not isinstance(cell.value, str):
        return False
    if kind == "number":
        return is_number_stored_as_text(cell)
    if kind == "date":
        return looks_like_date(cell.value)
    return kind == "logical" and looks_like_logical(cell.value)


def evaluate(check: CheckSpec, ctx: CheckContext) -> CheckResult:
    target = check_range(check)
    sheet = ctx.sheet(check)
    sheet.require(target, PropertyGroup.VALUES)
    kind = check["kind"]
    failures = Failures(CODES)
    for address, cell in sheet.iter_cells(target):
        if cell.value_kind == kind:
            continue
        if cell.value_kind == "empty":
            failures.add("empty", address)
        elif _stored_as_text(cell, kind):
            failures.add("stored_as_text", address)
        else:
            failures.add("wrong_type", address)
    return failures.result()
