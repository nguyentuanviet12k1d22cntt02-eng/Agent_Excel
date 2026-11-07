"""sheet_exists — có trang tính tên khớp mẫu (regex khớp cả tên, không phân biệt hoa thường)."""

import re

from excel_core.checks.base import CheckContext, CheckResult, CheckSpec, Read

TYPE = "sheet_exists"
CODES = ("missing_sheet",)


def reads(check: CheckSpec, sheet: str) -> list[Read]:
    return []  # danh sách tên sheet luôn có trong snapshot


def evaluate(check: CheckSpec, ctx: CheckContext) -> CheckResult:
    try:
        pattern = re.compile(check["name_pattern"], re.IGNORECASE)
    except re.error as exc:
        return CheckResult.not_evaluable(f"Mẫu tên sheet không hợp lệ: {exc}")
    if any(pattern.fullmatch(name.strip()) for name in ctx.current.sheet_names):
        return CheckResult.ok()
    return CheckResult.fail("missing_sheet", detail=f"không có sheet khớp {check['name_pattern']!r}")
