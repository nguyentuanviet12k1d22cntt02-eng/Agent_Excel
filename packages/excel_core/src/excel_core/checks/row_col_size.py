"""row_col_size — chiều cao dòng (pt) / độ rộng cột (số ký tự).

Bằng một giá trị, bằng dòng/cột khác, hoặc vừa nội dung.

"Vừa nội dung" (autofit) không tính lại được từ file (cần đo chữ theo phông), nên so với kích thước của chính
dòng/cột đó trong file đáp án, có ngưỡng sai số.
"""

from collections.abc import Mapping

from excel_core.checks.base import CheckContext, CheckResult, CheckSpec, Failures, Read, cell_read
from excel_core.checks.lines import line_range, lines_of, same_as_range
from excel_core.snapshot import PropertyGroup, SheetSnapshot

TYPE = "row_col_size"
CODES = ("wrong_size",)
DEFAULT_TOLERANCE = 0.5


def reads(check: CheckSpec, sheet: str) -> list[Read]:
    axis, lines = lines_of(check)
    found = [cell_read("current", sheet, line_range(axis, lines), PropertyGroup.STRUCTURE)]
    if "same_as" in check:
        found.append(cell_read("current", sheet, same_as_range(check["same_as"]), PropertyGroup.STRUCTURE))
    if check.get("autofit"):
        found.append(cell_read("solution", sheet, line_range(axis, lines), PropertyGroup.STRUCTURE))
    return found


def _sizes(sheet: SheetSnapshot, axis: str) -> Mapping[object, float]:
    return sheet.row_heights if axis == "rows" else sheet.col_widths


def _target_size(check: CheckSpec, ctx: CheckContext, axis: str, line: object) -> float | None:
    if "equals" in check:
        return float(check["equals"])
    if "same_as" in check:
        reference = check["same_as"]
        key: object = int(reference) if reference.isdigit() else reference
        return _sizes(ctx.sheet(check), axis).get(key)
    return _sizes(ctx.sheet(check, "solution"), axis).get(line)


def evaluate(check: CheckSpec, ctx: CheckContext) -> CheckResult:
    axis, lines = lines_of(check)
    sheet = ctx.sheet(check)
    sheet.require(line_range(axis, lines), PropertyGroup.STRUCTURE)
    tolerance = float(check.get("tolerance", DEFAULT_TOLERANCE))
    failures = Failures(CODES)
    for line in lines:
        actual = _sizes(sheet, axis).get(line)
        wanted = _target_size(check, ctx, axis, line)
        if actual is None or wanted is None or abs(actual - wanted) > tolerance:
            failures.add("wrong_size", str(line))
    return failures.result()
