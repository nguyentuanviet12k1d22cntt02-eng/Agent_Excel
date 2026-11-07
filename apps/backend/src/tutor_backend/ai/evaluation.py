"""Đánh giá chất lượng kịch bản AI sinh so với kịch bản viết tay (T5.8, đề cương mục 5.2).

Chỉ số cho mỗi lần sinh:
- **hợp lệ**: qua cả 3 tầng kiểm sau tối đa N lần gọi; số lần gọi, token, thời gian;
- **tỷ lệ bước đúng**: phần bước của kịch bản tay có một bước AI làm đúng việc đó (vùng mục tiêu trùng nhau,
  Jaccard ≥ 0,5);
- **tỷ lệ điều kiện trùng**: phần điều kiện của kịch bản tay mà kịch bản AI cũng kiểm (cùng loại, phủ vùng);
- **tỷ lệ bước phải sửa**: so revision AI với bản giảng viên sửa từ nó (`ai_edited`), khi có dữ liệu thật.

LLM cho kết quả khác nhau giữa các lần với cùng đầu vào (T2.6), nên chạy nhiều lần mỗi bài và báo trung bình.
"""

import json
import statistics
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from excel_core.address import parse_range
from tutor_backend.ai.exercise_analysis import analyze_exercise
from tutor_backend.ai.llm_client import LLMClient, LLMError
from tutor_backend.ai.script_agent import generate_script
from tutor_backend.ai.script_builder import ExerciseInfo

STEP_MATCH_THRESHOLD = 0.5

type Cell = tuple[str, int, int]


@dataclass(frozen=True)
class EvaluationCase:
    name: str
    starter: Path
    solution: Path
    info: ExerciseInfo
    reference: dict[str, Any] | None = None  # kịch bản viết tay để so (nếu có)


@dataclass(frozen=True)
class RunResult:
    case: str
    run: int
    ok: bool
    attempts: int
    prompt_tokens: int
    completion_tokens: int
    llm_ms: int
    steps: int
    coverage: float | None
    hint_issues: int
    step_match: float | None
    check_agreement: float | None
    error: str | None = None


def _cells(rng: str, sheet: str) -> set[Cell]:
    box = parse_range(rng)
    return {(sheet, c, r) for r in box.rows() for c in box.cols()}


def target_cells(step: dict[str, Any], default_sheet: str) -> set[Cell]:
    cells: set[Cell] = set()
    for target in step["targets"]["cells"]:
        if target["role"] == "target":
            cells |= _cells(target["range"], target.get("sheet") or default_sheet)
    return cells


def jaccard(a: set[Cell], b: set[Cell]) -> float:
    return len(a & b) / len(a | b) if a | b else 0.0


def step_match_rate(ai: dict[str, Any], reference: dict[str, Any]) -> float:
    """Phần bước của kịch bản tay có bước AI cùng vùng mục tiêu (Jaccard ≥ ngưỡng)."""
    sheet_ai, sheet_ref = ai["exercise"]["sheet"], reference["exercise"]["sheet"]
    ai_targets = [target_cells(s, sheet_ai) for s in ai["steps"]]
    matched = 0
    for step in reference["steps"]:
        wanted = target_cells(step, sheet_ref)
        if ai_targets and max(jaccard(wanted, got) for got in ai_targets) >= STEP_MATCH_THRESHOLD:
            matched += 1
    return matched / len(reference["steps"]) if reference["steps"] else 1.0


def _check_key(check: dict[str, Any], sheet: str) -> tuple[str, set[Cell]]:
    if "range" in check:
        return check["type"], _cells(check["range"], check.get("sheet") or sheet)
    return check["type"], set()


def check_agreement(ai: dict[str, Any], reference: dict[str, Any]) -> float:
    """Phần điều kiện của kịch bản tay mà kịch bản AI cũng kiểm: cùng loại, vùng AI phủ vùng kịch bản tay."""
    sheet_ai, sheet_ref = ai["exercise"]["sheet"], reference["exercise"]["sheet"]
    ai_checks = [_check_key(c, sheet_ai) for c in _all_checks(ai)]
    wanted = [_check_key(c, sheet_ref) for c in _all_checks(reference)]
    found = sum(1 for kind, cells in wanted if any(k == kind and cells <= got for k, got in ai_checks))
    return found / len(wanted) if wanted else 1.0


def _all_checks(script: dict[str, Any]) -> list[dict[str, Any]]:
    return [*script.get("global_checks", []), *(c for s in script["steps"] for c in s["checks"])]


def edit_rate(ai: dict[str, Any], edited: dict[str, Any]) -> float:
    """Tỷ lệ bước phải sửa: bước AI bị giảng viên đổi nội dung hoặc bỏ đi (so theo id bước)."""
    after = {step["id"]: step for step in edited["steps"]}
    changed = sum(1 for step in ai["steps"] if after.get(step["id"]) != step)
    return changed / len(ai["steps"]) if ai["steps"] else 0.0


def run_case(case: EvaluationCase, llm: LLMClient, run: int, max_attempts: int) -> RunResult:
    analysis = analyze_exercise(case.starter, case.solution, case.info.sheet)
    try:
        outcome = generate_script(analysis, case.info, [], llm, (case.starter, case.solution), max_attempts)
    except LLMError as exc:
        return RunResult(case.name, run, False, 0, 0, 0, 0, 0, None, 0, None, None, str(exc))
    script, report = outcome.script, outcome.report or {}
    reference = case.reference
    return RunResult(
        case=case.name,
        run=run,
        ok=outcome.ok,
        attempts=outcome.attempts,
        prompt_tokens=outcome.prompt_tokens,
        completion_tokens=outcome.completion_tokens,
        llm_ms=outcome.llm_ms,
        steps=len(script["steps"]) if script else 0,
        coverage=report.get("diff_coverage"),
        hint_issues=len(report.get("hint_text_issues", [])),
        step_match=step_match_rate(script, reference) if script and reference else None,
        check_agreement=check_agreement(script, reference) if script and reference else None,
        error="; ".join(outcome.remaining_issues[:2]) or None,
    )


def run_evaluation(
    cases: Sequence[EvaluationCase],
    llm_factory: Callable[[], LLMClient],
    runs: int,
    max_attempts: int,
    on_result: Callable[[RunResult], None] | None = None,
) -> list[RunResult]:
    results = []
    for case in cases:
        for run in range(1, runs + 1):
            result = run_case(case, llm_factory(), run, max_attempts)
            results.append(result)
            if on_result:
                on_result(result)
    return results


def _mean(values: Iterable[float | None]) -> float | None:
    present = [v for v in values if v is not None]
    return statistics.fmean(present) if present else None


def _fmt(value: float | None, percent: bool = False, digits: int = 1) -> str:
    if value is None:
        return "—"
    return f"{value * 100:.0f}%" if percent else f"{value:.{digits}f}"


def _tokens(results: Sequence[RunResult]) -> str:
    prompt = _fmt(_mean(r.prompt_tokens for r in results), digits=0)
    completion = _fmt(_mean(r.completion_tokens for r in results), digits=0)
    return f"{prompt} / {completion}"


def summary_rows(results: Sequence[RunResult], cases: Sequence[EvaluationCase]) -> list[list[str]]:
    """Một dòng mỗi bài: trung bình qua các lần chạy."""
    rows = []
    for case in cases:
        mine = [r for r in results if r.case == case.name]
        if not mine:
            continue
        hand_steps = len(case.reference["steps"]) if case.reference else None
        rows.append(
            [
                case.name,
                f"{sum(r.ok for r in mine)}/{len(mine)}",
                _fmt(_mean(r.attempts for r in mine)),
                _fmt(_mean(r.llm_ms / 1000 for r in mine)),
                _tokens(mine),
                f"{_fmt(_mean(r.steps for r in mine))}" + (f" ({hand_steps})" if hand_steps else ""),
                _fmt(_mean(r.coverage for r in mine), percent=True),
                str(sum(r.hint_issues for r in mine)),
                _fmt(_mean(r.step_match for r in mine), percent=True),
                _fmt(_mean(r.check_agreement for r in mine), percent=True),
            ]
        )
    return rows


SUMMARY_HEADER = [
    "Bài",
    "Hợp lệ (3 tầng)",
    "Số lần gọi",
    "Thời gian AI (s)",
    "Token vào / ra",
    "Số bước AI (tay)",
    "Độ phủ diff",
    "Lỗi chữ gợi ý",
    "Bước đúng",
    "Điều kiện trùng",
]


def markdown_table(header: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join(lines)


def results_json(results: Sequence[RunResult]) -> str:
    return json.dumps([r.__dict__ for r in results], ensure_ascii=False, indent=2)
