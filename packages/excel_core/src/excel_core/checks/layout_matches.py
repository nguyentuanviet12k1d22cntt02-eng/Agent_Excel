"""layout_matches — bảng sau khi chèn/xóa dòng, cột khớp bố cục đáp án.

Địa chỉ ô dịch chuyển sau khi chèn/xóa, nên so cả vùng với đáp án cùng bố cục; cột khóa (theo tiêu đề) dùng
để báo dòng nào lệch.
"""

from excel_core.address import cell_address
from excel_core.checks.base import CheckContext, CheckResult, CheckSpec, Read, cell_read, check_range
from excel_core.checks.table import find_column, normalize_header
from excel_core.checks.values import values_equal
from excel_core.snapshot import PropertyGroup

TYPE = "layout_matches"
CODES = ("wrong_layout",)


def reads(check: CheckSpec, sheet: str) -> list[Read]:
    return [
        cell_read("current", sheet, check["range"], PropertyGroup.VALUES),
        cell_read("solution", sheet, check["range"], PropertyGroup.VALUES),
    ]


def evaluate(check: CheckSpec, ctx: CheckContext) -> CheckResult:
    table = check_range(check)
    current, solution = ctx.sheet(check), ctx.sheet(check, "solution")
    current.require(table, PropertyGroup.VALUES)
    solution.require(table, PropertyGroup.VALUES)
    headers = [cell_address(col, table.min_row) for col in table.cols()]
    wrong_headers = [
        a
        for a in headers
        if normalize_header(current.cell(a).value) != normalize_header(solution.cell(a).value)
    ]
    if wrong_headers:
        return CheckResult.fail("wrong_layout", wrong_headers, "dòng tiêu đề khác đáp án")
    key_col = find_column(solution, table, check["key_column"])
    wrong_rows = [
        row
        for row in range(table.min_row + 1, table.max_row + 1)
        if any(
            not values_equal(
                current.cell(cell_address(col, row)).value, solution.cell(cell_address(col, row)).value
            )
            for col in table.cols()
        )
    ]
    if wrong_rows:
        keys = [cell_address(key_col, row) for row in wrong_rows]
        return CheckResult.fail("wrong_layout", keys, f"{len(wrong_rows)} dòng khác đáp án")
    return CheckResult.ok()
