"""Bộ kiểm tra điều kiện kiểm chứng, mỗi loại điều kiện một module (T4.4).

Danh mục: docs/thiet-ke/danh-muc-dieu-kien.md. Cùng một bộ điều kiện chạy ở Backend (trên file, openpyxl) và
Desktop (trên Excel đang chạy, COM), vì cả hai cùng đưa vào snapshot đã chuẩn hóa.
"""

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from types import ModuleType

from excel_core.checks import (
    alignment,
    autofilter,
    border,
    chart,
    data_unchanged,
    fill,
    font,
    formula_consistent,
    formula_matches_r1c1,
    formula_uses_function,
    header_footer,
    is_formula,
    layout_matches,
    merged,
    number_format,
    observation_only,
    page_setup,
    printed_to_pdf,
    row_col_hidden,
    row_col_size,
    sheet_exists,
    sorted_by,
    value_equals,
    value_type,
    visible_rows,
)
from excel_core.checks.base import (
    CheckContext,
    CheckResult,
    CheckSpec,
    CheckSpecError,
    CheckStatus,
    MissingReferenceError,
    Read,
    Source,
)
from excel_core.snapshot import ReadRequest, SheetNotFoundError, merge_requests

_MODULES: tuple[ModuleType, ...] = (
    value_equals,
    value_type,
    data_unchanged,
    is_formula,
    formula_uses_function,
    formula_consistent,
    formula_matches_r1c1,
    number_format,
    alignment,
    font,
    fill,
    border,
    merged,
    row_col_hidden,
    row_col_size,
    layout_matches,
    sheet_exists,
    autofilter,
    visible_rows,
    sorted_by,
    page_setup,
    header_footer,
    chart,
    printed_to_pdf,
    observation_only,
)


@dataclass(frozen=True)
class CheckDefinition:
    type: str
    codes: tuple[str, ...]  # theo thứ tự ưu tiên
    reads: Callable[[CheckSpec, str], list[Read]]
    evaluate: Callable[[CheckSpec, CheckContext], CheckResult]


DEFINITIONS: dict[str, CheckDefinition] = {
    m.TYPE: CheckDefinition(m.TYPE, tuple(m.CODES), m.reads, m.evaluate) for m in _MODULES
}
# Chỉ Desktop chấm được (sự kiện, xác nhận của học viên): tự kiểm trên file bỏ qua
LIVE_ONLY_TYPES = frozenset({printed_to_pdf.TYPE, observation_only.TYPE})


def codes_for(check_type: str) -> tuple[str, ...]:
    """Các mã lỗi điều kiện loại này có thể trả về."""
    definition = DEFINITIONS.get(check_type)
    return definition.codes if definition else ()


def check_reads(check: CheckSpec, default_sheet: str) -> list[Read]:
    definition = DEFINITIONS.get(check["type"])
    if definition is None:
        return []
    return definition.reads(check, check.get("sheet") or default_sheet)


def read_requests(checks: Iterable[CheckSpec], default_sheet: str) -> dict[Source, ReadRequest]:
    """Gộp nhu cầu đọc của nhiều điều kiện thành một ReadRequest cho mỗi nguồn (current/starter/solution)."""
    by_source: dict[Source, list[Read]] = {}
    for check in checks:
        for read in check_reads(check, default_sheet):
            by_source.setdefault(read.source, []).append(read)
    return {source: merge_requests(r.request for r in reads) for source, reads in by_source.items()}


def reference_requests(checks: Iterable[CheckSpec], default_sheet: str) -> dict[Source, ReadRequest]:
    """Phần cần đọc trên file đề và file đáp án: Backend gửi kèm kịch bản cho Desktop (snapshot.md mục 7)."""
    requests = read_requests(checks, default_sheet)
    return {source: request for source, request in requests.items() if source != "current"}


def run_check(check: CheckSpec, ctx: CheckContext) -> CheckResult:
    """Chấm một điều kiện. Loại lạ, thiếu file tham chiếu, tham số sai → NOT_EVALUABLE (phiên vẫn chạy)."""
    definition = DEFINITIONS.get(check.get("type", ""))
    if definition is None:
        return CheckResult.not_evaluable(f"loại điều kiện chưa hỗ trợ: {check.get('type')!r}")
    try:
        return definition.evaluate(check, ctx)
    except (MissingReferenceError, SheetNotFoundError) as exc:
        return CheckResult.not_evaluable(str(exc))
    except CheckSpecError as exc:
        return CheckResult.not_evaluable(f"tham số điều kiện sai: {exc}")


__all__ = [
    "DEFINITIONS",
    "LIVE_ONLY_TYPES",
    "CheckContext",
    "CheckDefinition",
    "CheckResult",
    "CheckSpec",
    "CheckSpecError",
    "CheckStatus",
    "Read",
    "Source",
    "check_reads",
    "codes_for",
    "read_requests",
    "reference_requests",
    "run_check",
]
