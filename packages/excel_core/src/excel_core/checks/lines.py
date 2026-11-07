"""Dòng/cột trong tham số `rows` ("5:7") hoặc `cols` ("C:D") của điều kiện."""

from excel_core.address import CellRange, column_index, parse_cols, parse_rows
from excel_core.checks.base import CheckSpec


def lines_of(check: CheckSpec) -> tuple[str, list[int] | list[str]]:
    """("rows", [5, 6, 7]) hoặc ("cols", ["C", "D"])."""
    if "rows" in check:
        return "rows", list(parse_rows(check["rows"]))
    return "cols", parse_cols(check["cols"])


def line_range(axis: str, lines: list[int] | list[str]) -> CellRange:
    """Vùng ô đại diện để đọc nhóm STRUCTURE của các dòng/cột này."""
    if axis == "rows":
        rows = [int(r) for r in lines]
        return CellRange(1, min(rows), 1, max(rows))
    cols = [column_index(str(c)) for c in lines]
    return CellRange(min(cols), 1, max(cols), 1)


def same_as_range(reference: str) -> CellRange:
    """Tham số `same_as` ("4" hoặc "B") → vùng đại diện."""
    if reference.isdigit():
        return CellRange(1, int(reference), 1, int(reference))
    col = column_index(reference)
    return CellRange(col, 1, col, 1)
