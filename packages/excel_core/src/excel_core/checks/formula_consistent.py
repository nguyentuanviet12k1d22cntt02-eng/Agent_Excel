"""formula_consistent — mọi ô cùng một công thức R1C1 (công thức được sao chép).

Lỗi địa chỉ tuyệt đối khi sao chép vẫn cho R1C1 đồng nhất (đã kiểm chứng trên Excel). Vì vậy khi mọi tham
chiếu đều cố định theo chiều sao chép (mọi ô cho cùng kết quả) thì trả `absolute_reference`. Trong kịch bản
vẫn luôn kèm `value_equals`.
"""

from collections import Counter

from excel_core.checks.base import (
    CheckContext,
    CheckResult,
    CheckSpec,
    Failures,
    Read,
    cell_read,
    check_range,
)
from excel_core.formula import is_r1c1_absolute_along
from excel_core.snapshot import PropertyGroup

TYPE = "formula_consistent"
CODES = ("absolute_reference", "inconsistent_formula", "empty")


def reads(check: CheckSpec, sheet: str) -> list[Read]:
    return [cell_read("current", sheet, check["range"], PropertyGroup.VALUES, PropertyGroup.FORMULAS)]


def _absolute_along_copy(r1c1: str, copied_down: bool, copied_across: bool) -> bool:
    if copied_down and is_r1c1_absolute_along(r1c1, "R"):
        return True
    return copied_across and is_r1c1_absolute_along(r1c1, "C")


def evaluate(check: CheckSpec, ctx: CheckContext) -> CheckResult:
    target = check_range(check)
    sheet = ctx.sheet(check)
    sheet.require(target, PropertyGroup.FORMULAS)
    failures = Failures(CODES)
    patterns: dict[str, str] = {}
    for address, cell in sheet.iter_cells(target):
        if cell.formula is None:
            failures.add("empty" if cell.value_kind == "empty" else "inconsistent_formula", address)
        else:
            patterns[address] = cell.formula_r1c1 or cell.formula
    if patterns:
        common, _ = Counter(patterns.values()).most_common(1)[0]
        for address, pattern in patterns.items():
            if pattern != common:
                failures.add("inconsistent_formula", address)
        if not failures and _absolute_along_copy(common, target.height > 1, target.width > 1):
            failures.add("absolute_reference", target.top_left)
    return failures.result()
