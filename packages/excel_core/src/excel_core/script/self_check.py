"""Tầng 3: tự kiểm kịch bản trên file đề và file đáp án (T4.5; Backend dùng cho tác tử sinh kịch bản T5.5).

- Mỗi điều kiện của bước phải **đạt trên đáp án**; mỗi bước phải **chưa đạt trên đề** (bước đạt sẵn là vô
  nghĩa). Một điều kiện riêng lẻ đạt sẵn trên đề chỉ là cảnh báo: có thể là điều kiện giữ (ví dụ công thức
  có sẵn không bị gõ đè).
- Kịch bản theo quy trình (bước có `operation`): làm lần lượt các thao tác trên file đề (procedure.py);
  bước có thao tác phải đạt trên trạng thái **ngay sau** thao tác và chưa đạt trên trạng thái **ngay trước**;
  bước không có thao tác so như trên nhưng "đề" là trạng thái lúc tới bước đó. Làm hết các thao tác mà bố cục,
  dòng/cột ẩn còn khác đáp án là lỗi (AI hiểu sai đề).
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
from excel_core.diff import CELL_KINDS, LAYOUT_KINDS, ChangeKind, WorkbookDiff, diff_workbooks, pair_request
from excel_core.procedure import Operation, ProcedureError, apply_operation, check_operation, with_sheet
from excel_core.readers import read_workbook
from excel_core.script.hint_text import hint_text_issues
from excel_core.snapshot import CELL_GROUPS, RangeRequest, ReadRequest, WorkbookSnapshot, merge_requests

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
    states: tuple[WorkbookSnapshot, WorkbookSnapshot] | None = None,
) -> CheckOutcome:
    """`states` = (trước bước, sau bước) khi kịch bản theo quy trình; mặc định là (đề, đáp án)."""
    before, after = states or (starter, solution)

    def run(current: WorkbookSnapshot) -> CheckResult:
        ctx = CheckContext(current=current, default_sheet=check["sheet"], starter=starter, solution=solution)
        return run_check(check, ctx)

    return CheckOutcome(step_id, index, check["type"], run(after), run(before))


def _with_default_sheet(check: Mapping[str, Any], sheet: str) -> dict[str, Any]:
    return {**check, "sheet": check.get("sheet") or sheet}


def _judge_steps(outcomes: list[CheckOutcome], script: Script) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    procedural = {step["id"] for step in script["steps"] if "operation" in step}
    for o in outcomes:
        where = f"bước {o.step_id}" if o.step_id else "điều kiện toàn bài"
        label = f"{where}, điều kiện {o.check_index} ({o.type})"
        if o.type in LIVE_ONLY_TYPES or o.on_solution.status == CheckStatus.NOT_EVALUABLE:
            warnings.append(f"{label}: không tự kiểm được trên file ({o.on_solution.detail})")
        elif not o.passes_on_solution:
            errors.append(f"{label}: không đạt trên đáp án ({o.on_solution.code}: {o.on_solution.detail})")
        elif o.step_id is None and not o.on_starter.passed:
            errors.append(f"{label}: không đạt trên file đề ({o.on_starter.code})")
        elif o.step_id is not None and o.on_starter.passed and o.step_id not in procedural:
            # Bước quy trình: ô mốc ngay trước chỗ chèn/xóa vốn đã đúng từ trước, không cần cảnh báo
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


def is_procedure(script: Script) -> bool:
    """Kịch bản theo quy trình trong đề: có bước mang thao tác cấu trúc (`operation`)."""
    return any("operation" in step for step in script["steps"])


def step_states(
    script: Script, starter: WorkbookSnapshot, solution: WorkbookSnapshot
) -> dict[str, tuple[WorkbookSnapshot, WorkbookSnapshot]]:
    """(trước, sau) của từng bước khi làm lần lượt các thao tác trên file đề. Ném ProcedureError."""
    sheet = script["exercise"]["sheet"]
    current = starter
    states: dict[str, tuple[WorkbookSnapshot, WorkbookSnapshot]] = {}
    for number, step in enumerate(script["steps"], start=1):
        if "operation" not in step:
            states[step["id"]] = (current, solution)
            continue
        try:
            op = Operation.from_json(step["operation"])
            check_operation(current.sheet(sheet), op)
            page = apply_operation(current.sheet(sheet), op)
        except ProcedureError as exc:
            raise ProcedureError(f"bước {number} ({step['id']}): {exc}") from exc
        after = with_sheet(current, page)
        states[step["id"]] = (current, after)
        current = after
    return states


def _procedure_errors(
    script: Script,
    states: Mapping[str, tuple[WorkbookSnapshot, WorkbookSnapshot]],
    solution: WorkbookSnapshot,
) -> list[str]:
    """Làm hết các thao tác mà bố cục hay dòng/cột ẩn còn khác đáp án: quy trình không dẫn tới đáp án."""
    sheet = script["exercise"]["sheet"]
    last = [step["id"] for step in script["steps"] if "operation" in step][-1]
    final = states[last][1]
    structural = LAYOUT_KINDS | {ChangeKind.COL_HIDDEN, ChangeKind.ROW_HIDDEN}
    left = [c for c in diff_workbooks(final, solution).changes if c.sheet == sheet and c.kind in structural]
    return [f"làm hết các thao tác của quy trình mà còn khác đáp án: {c.after} {c.range}" for c in left]


def self_check(script: Script, starter: WorkbookSnapshot, solution: WorkbookSnapshot) -> SelfCheckReport:
    """Tầng 3 trên hai snapshot đã đọc (nên đọc bằng `self_check_request`)."""
    sheet = script["exercise"]["sheet"]
    states: Mapping[str, tuple[WorkbookSnapshot, WorkbookSnapshot]] = {}
    procedure_errors: list[str] = []
    if is_procedure(script):
        try:
            states = step_states(script, starter, solution)
            procedure_errors = _procedure_errors(script, states, solution)
        except ProcedureError as exc:
            procedure_errors = [f"quy trình không làm được: {exc}"]
    outcomes = [
        _outcome(None, i, _with_default_sheet(check, sheet), starter, solution)
        for i, check in enumerate(script.get("global_checks", []))
    ]
    for step in script["steps"]:
        step_pair = states.get(step["id"])
        outcomes += [
            _outcome(step["id"], i, _with_default_sheet(check, sheet), starter, solution, step_pair)
            for i, check in enumerate(step["checks"])
        ]
    errors, warnings = _judge_steps(outcomes, script)
    errors = procedure_errors + errors
    coverage, uncovered = _coverage(diff_workbooks(starter, solution), script)
    if uncovered:
        warnings.append(f"độ phủ diff {coverage:.0%}: chưa kiểm {', '.join(uncovered)}")
    hint_issues = tuple(hint_text_issues(script, starter, solution))
    warnings += [f"bước {i['step_id']}: {i['issue']} ({i['text']})" for i in hint_issues]
    return SelfCheckReport(tuple(outcomes), coverage, uncovered, hint_issues, tuple(errors), tuple(warnings))


def self_check_request(script: Script, starter_path: Path | str, solution_path: Path | str) -> ReadRequest:
    """Một yêu cầu đọc dùng cho cả hai file: vùng đang dùng (để diff) + mọi vùng các điều kiện cần.

    Kịch bản theo quy trình: điều kiện ghi địa chỉ theo trạng thái giữa chừng (cột mới chèn, cột đã dời), nên
    đọc trọn từ A1 tới hết vùng đang dùng; vùng đã đọc dời theo từng thao tác.
    """
    sheet = script["exercise"]["sheet"]
    checks = [*script.get("global_checks", []), *(c for s in script["steps"] for c in s["checks"])]
    needed = read_requests(checks, sheet).values()
    pair = pair_request(starter_path, solution_path)
    extra: list[ReadRequest | RangeRequest] = []
    if is_procedure(script):
        for read in pair.ranges:
            if read.sheet == sheet:
                rng = parse_range(read.range)
                extra.append(RangeRequest(sheet, str(CellRange(1, 1, rng.max_col, rng.max_row)), CELL_GROUPS))
    return merge_requests([pair, *needed, *extra])


def self_check_files(script: Script, starter_path: Path | str, solution_path: Path | str) -> SelfCheckReport:
    """Tầng 3 trên hai file .xlsx (file đáp án phải được Excel lưu để có giá trị công thức)."""
    request = self_check_request(script, starter_path, solution_path)
    return self_check(script, read_workbook(starter_path, request), read_workbook(solution_path, request))
