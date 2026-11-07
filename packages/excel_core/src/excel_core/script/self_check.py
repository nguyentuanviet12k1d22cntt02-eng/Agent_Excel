"""Tầng 3: tự kiểm kịch bản trên file đề và file đáp án (T4.5; Backend dùng cho tác tử sinh kịch bản T5.5).

- Mỗi điều kiện của bước phải **đạt trên đáp án**; mỗi bước phải **chưa đạt trên đề** (bước đạt sẵn là vô
  nghĩa). Một điều kiện riêng lẻ đạt sẵn trên đề chỉ là cảnh báo: có thể là điều kiện giữ (ví dụ công thức
  có sẵn không bị gõ đè).
- Điều kiện toàn bài phải đạt trên cả đề và đáp án.
- Độ phủ diff: thay đổi nào từ đề sang đáp án chưa có điều kiện cùng loại kiểm.
- Chữ gợi ý không ghi địa chỉ ô (overlay đã chỉ, quyết định 8 GĐ2) và không có số liệu không có trong bài.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from excel_core.address import CellRange, parse_range
from excel_core.checks import (
    LIVE_ONLY_TYPES,
    CheckContext,
    CheckResult,
    CheckStatus,
    read_requests,
    run_check,
)
from excel_core.diff import CELL_KINDS, ChangeKind, WorkbookDiff, diff_workbooks, pair_request
from excel_core.readers import read_workbook
from excel_core.script.hint_text import hint_text_issues
from excel_core.snapshot import ReadRequest, WorkbookSnapshot, merge_requests

type Script = Mapping[str, Any]

# Loại thay đổi → các loại điều kiện kiểm được thay đổi đó (để tính độ phủ diff)
COVERING_CHECKS: dict[ChangeKind, frozenset[str]] = {
    ChangeKind.VALUE: frozenset({"value_equals", "value_type", "layout_matches", "sorted_by"}),
    ChangeKind.FORMULA: frozenset(
        {"is_formula", "formula_uses_function", "formula_consistent", "formula_matches_r1c1", "value_equals"}
    ),
    ChangeKind.NUMBER_FORMAT: frozenset({"number_format"}),
    ChangeKind.FONT: frozenset({"font"}),
    ChangeKind.FILL: frozenset({"fill"}),
    ChangeKind.BORDER: frozenset({"border"}),
    ChangeKind.ALIGNMENT: frozenset({"alignment"}),
    ChangeKind.MERGED: frozenset({"merged"}),
}


@dataclass(frozen=True)
class CheckOutcome:
    """Kết quả tự kiểm một điều kiện (khớp SelfCheckReport.checks trong openapi.yaml)."""

    step_id: str | None  # None: điều kiện toàn bài
    check_index: int
    type: str
    on_solution: CheckResult
    on_starter: CheckResult

    @property
    def passes_on_solution(self) -> bool:
        return self.on_solution.passed

    @property
    def fails_on_starter(self) -> bool:
        return self.on_starter.status == CheckStatus.FAILED


@dataclass(frozen=True)
class SelfCheckReport:
    checks: tuple[CheckOutcome, ...]
    diff_coverage: float
    uncovered_ranges: tuple[str, ...]
    hint_text_issues: tuple[dict[str, str], ...]
    errors: tuple[str, ...] = field(default=())  # chặn: phải sửa trước khi gửi duyệt
    warnings: tuple[str, ...] = field(default=())  # giảng viên xem lại

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict[str, Any]:
        """Dạng JSON cho API (SelfCheckReport, không gồm schema_ok và cross_reference_errors)."""
        return {
            "checks": [
                {
                    "step_id": c.step_id,
                    "check_index": c.check_index,
                    "type": c.type,
                    "passes_on_solution": c.passes_on_solution,
                    "fails_on_starter": c.fails_on_starter,
                    "code_on_starter": c.on_starter.code,
                }
                for c in self.checks
            ],
            "diff_coverage": self.diff_coverage,
            "uncovered_ranges": list(self.uncovered_ranges),
            "hint_text_issues": list(self.hint_text_issues),
            "errors": list(self.errors),
            "warnings": list(self.warnings),
        }


def _outcome(
    step_id: str | None,
    index: int,
    check: Mapping[str, Any],
    starter: WorkbookSnapshot,
    solution: WorkbookSnapshot,
) -> CheckOutcome:
    def run(current: WorkbookSnapshot) -> CheckResult:
        ctx = CheckContext(current=current, default_sheet=check["sheet"], starter=starter, solution=solution)
        return run_check(check, ctx)

    return CheckOutcome(step_id, index, check["type"], run(solution), run(starter))


def _with_default_sheet(check: Mapping[str, Any], sheet: str) -> dict[str, Any]:
    return {**check, "sheet": check.get("sheet") or sheet}


def _judge_steps(outcomes: list[CheckOutcome], script: Script) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    for o in outcomes:
        where = f"bước {o.step_id}" if o.step_id else "điều kiện toàn bài"
        label = f"{where}, điều kiện {o.check_index} ({o.type})"
        if o.type in LIVE_ONLY_TYPES or o.on_solution.status == CheckStatus.NOT_EVALUABLE:
            warnings.append(f"{label}: không tự kiểm được trên file ({o.on_solution.detail})")
        elif not o.passes_on_solution:
            errors.append(f"{label}: không đạt trên đáp án ({o.on_solution.code}: {o.on_solution.detail})")
        elif o.step_id is None and not o.on_starter.passed:
            errors.append(f"{label}: không đạt trên file đề ({o.on_starter.code})")
        elif o.step_id is not None and o.on_starter.passed:
            warnings.append(f"{label}: đã đạt sẵn trên file đề (điều kiện giữ?)")
    for step in script["steps"]:
        mine = [
            o
            for o in outcomes
            if o.step_id == step["id"] and o.on_starter.status != CheckStatus.NOT_EVALUABLE
        ]
        if mine and all(o.on_starter.passed for o in mine):
            errors.append(f"bước {step['id']}: mọi điều kiện đã đạt sẵn trên file đề")
    return errors, warnings


def _coverage(diff: WorkbookDiff, script: Script) -> tuple[float, tuple[str, ...]]:
    default_sheet = script["exercise"]["sheet"]
    checked: list[tuple[str, str, CellRange]] = []
    for step in script["steps"]:
        for check in step["checks"]:
            if "range" in check:
                checked.append(
                    (check["type"], check.get("sheet") or default_sheet, parse_range(check["range"]))
                )
    changes = [c for c in diff.cell_changes() if c.kind in CELL_KINDS and c.kind in COVERING_CHECKS]
    uncovered = []
    for change in changes:
        rng = parse_range(change.range or "")
        types = COVERING_CHECKS[change.kind]
        boxes = [box for kind, sheet, box in checked if kind in types and sheet == change.sheet]
        if not all(any(b.contains_cell(col, row) for b in boxes) for row in rng.rows() for col in rng.cols()):
            uncovered.append(f"{change.sheet}!{change.range} ({change.kind.value})")
    coverage = 1.0 if not changes else round((len(changes) - len(uncovered)) / len(changes), 3)
    return coverage, tuple(uncovered)


def self_check(script: Script, starter: WorkbookSnapshot, solution: WorkbookSnapshot) -> SelfCheckReport:
    """Tầng 3 trên hai snapshot đã đọc (nên đọc bằng `self_check_request`)."""
    sheet = script["exercise"]["sheet"]
    outcomes = [
        _outcome(None, i, _with_default_sheet(check, sheet), starter, solution)
        for i, check in enumerate(script.get("global_checks", []))
    ]
    for step in script["steps"]:
        outcomes += [
            _outcome(step["id"], i, _with_default_sheet(check, sheet), starter, solution)
            for i, check in enumerate(step["checks"])
        ]
    errors, warnings = _judge_steps(outcomes, script)
    coverage, uncovered = _coverage(diff_workbooks(starter, solution), script)
    if uncovered:
        warnings.append(f"độ phủ diff {coverage:.0%}: chưa kiểm {', '.join(uncovered)}")
    hint_issues = tuple(hint_text_issues(script, starter, solution))
    warnings += [f"bước {i['step_id']}: {i['issue']} ({i['text']})" for i in hint_issues]
    return SelfCheckReport(tuple(outcomes), coverage, uncovered, hint_issues, tuple(errors), tuple(warnings))


def self_check_request(script: Script, starter_path: Path | str, solution_path: Path | str) -> ReadRequest:
    """Một yêu cầu đọc dùng cho cả hai file: vùng đang dùng (để diff) + mọi vùng các điều kiện cần."""
    sheet = script["exercise"]["sheet"]
    checks = [*script.get("global_checks", []), *(c for s in script["steps"] for c in s["checks"])]
    needed = read_requests(checks, sheet).values()
    return merge_requests([pair_request(starter_path, solution_path), *needed])


def self_check_files(script: Script, starter_path: Path | str, solution_path: Path | str) -> SelfCheckReport:
    """Tầng 3 trên hai file .xlsx (file đáp án phải được Excel lưu để có giá trị công thức)."""
    request = self_check_request(script, starter_path, solution_path)
    return self_check(script, read_workbook(starter_path, request), read_workbook(solution_path, request))
