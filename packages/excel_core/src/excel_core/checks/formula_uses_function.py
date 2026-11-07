"""formula_uses_function — công thức dùng (ít nhất một trong) các hàm yêu cầu.

Phân biệt "chỉ cần đúng giá trị" (value_equals) với "phải dùng đúng hàm" (điều kiện này). Với
`forbid_operator_only` (mặc định bật): công thức cộng từng ô bằng phép tính, kể cả bọc trong hàm gộp
như `=SUM(C9+D9+E9)`, trả mã `used_operator_instead`. `=SUM(C9,D9,E9)` vẫn đạt (câu hỏi GVHD b22, bản nháp).
"""

from excel_core.checks.base import (
    CheckContext,
    CheckResult,
    CheckSpec,
    Failures,
    Read,
    cell_read,
    check_range,
)
from excel_core.formula import ARITHMETIC_OPERATORS, FormulaError, FormulaParts, parse_formula
from excel_core.snapshot import PropertyGroup

TYPE = "formula_uses_function"
CODES = ("used_operator_instead", "missing_function", "empty")
# Hàm gộp: bọc phép cộng từng ô trong các hàm này là dùng phép tính thay cho hàm
AGGREGATE_FUNCTIONS = frozenset({"SUM", "AVERAGE", "MIN", "MAX", "COUNT", "COUNTA", "PRODUCT"})


def reads(check: CheckSpec, sheet: str) -> list[Read]:
    return [cell_read("current", sheet, check["range"], PropertyGroup.VALUES, PropertyGroup.FORMULAS)]


def is_operator_only(parts: FormulaParts) -> bool:
    """Tính bằng phép toán trên từng ô lẻ (=C9+D9+E9, =SUM(C9+D9+E9)), không dùng vùng."""
    has_arithmetic = any(op in ARITHMETIC_OPERATORS for op in parts.infix_operators)
    only_single_cells = all(":" not in ref for ref in parts.references)
    only_aggregates = all(f in AGGREGATE_FUNCTIONS for f in parts.functions)
    return has_arithmetic and only_single_cells and len(parts.references) > 1 and only_aggregates


def _cell_code(formula: str, required: set[str], forbid_operator_only: bool) -> str | None:
    try:
        parts = parse_formula(formula)
    except FormulaError:
        return "missing_function"
    if forbid_operator_only and is_operator_only(parts):
        return "used_operator_instead"
    return None if required & set(parts.functions) else "missing_function"


def evaluate(check: CheckSpec, ctx: CheckContext) -> CheckResult:
    target = check_range(check)
    sheet = ctx.sheet(check)
    sheet.require(target, PropertyGroup.FORMULAS)
    required = {f.upper() for f in check["functions"]}
    forbid = bool(check.get("forbid_operator_only", True))
    failures = Failures(CODES)
    for address, cell in sheet.iter_cells(target):
        if cell.formula is None:
            failures.add("empty" if cell.value_kind == "empty" else "missing_function", address)
            continue
        code = _cell_code(cell.formula, required, forbid)
        if code:
            failures.add(code, address)
    return failures.result()
