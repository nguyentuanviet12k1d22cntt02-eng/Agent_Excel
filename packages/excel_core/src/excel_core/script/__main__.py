r"""Kiểm một kịch bản JSON theo 3 tầng.

    .venv\Scripts\python -m excel_core.script kich-ban.json
    .venv\Scripts\python -m excel_core.script kich-ban.json --starter de.xlsx --solution dap-an.xlsx
    .venv\Scripts\python -m excel_core.script kich-ban.json --starter de.xlsx --solution dap-an.xlsx ^
        --current bai-lam.xlsx          chấm thử file bài làm như Desktop sẽ chấm

Mã thoát 0 khi không có lỗi chặn, 1 khi có.
"""

import argparse
import json
import sys
from pathlib import Path

from excel_core.script import load_script, self_check_files, validate_script
from excel_core.script.grade import GradeReport, grade_files

MARKS = {"passed": "✓", "failed": "✗", "not_evaluable": "?"}


def _print_grade(report: GradeReport) -> None:
    for check in report.global_checks:
        result = check.result
        print(f"Toàn bài #{check.index + 1} {check.type}: {MARKS[result.status.value]} {result.code or ''}")
    for step in report.steps:
        here = "  ← học viên đang ở bước này" if step.step_id == report.current_step_id else ""
        print(f"{MARKS[step.status.value]} {step.step_id} — {step.title}{here}")
        for check in step.checks:
            result = check.result
            cells = f" ({', '.join(result.cells[:5])})" if result.cells else ""
            print(f"    {MARKS[result.status.value]} {check.type} {result.code or ''}{cells} {result.detail}")
        for feedback in step.feedback:
            print(f"    gia sư nói: {feedback['message']}")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="python -m excel_core.script", description="Kiểm kịch bản 3 tầng.")
    parser.add_argument("script", type=Path, help="file kịch bản .json")
    parser.add_argument("--starter", type=Path, help="file đề (.xlsx) để chạy tầng 3")
    parser.add_argument("--solution", type=Path, help="file đáp án (.xlsx) để chạy tầng 3")
    parser.add_argument("--json", action="store_true", help="in báo cáo tầng 3 dạng JSON")
    parser.add_argument("--current", type=Path, help="file bài làm (.xlsx) để chấm thử từng bước")
    args = parser.parse_args()

    script = load_script(args.script)
    validation = validate_script(script)
    print(f"Tầng 1 (lược đồ): {'đạt' if validation.schema_ok else 'KHÔNG ĐẠT'}")
    for issue in validation.schema_issues:
        print(f"  - {issue}")
    if validation.schema_ok:
        print(f"Tầng 2 (tham chiếu chéo): {'đạt' if not validation.cross_reference_issues else 'KHÔNG ĐẠT'}")
        for issue in validation.cross_reference_issues:
            print(f"  - {issue}")
    if not validation.ok or not (args.starter and args.solution):
        return 0 if validation.ok else 1

    if args.current:
        _print_grade(grade_files(script, args.current, args.starter, args.solution))
        return 0
    report = self_check_files(script, args.starter, args.solution)
    if args.json:
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    verdict = "đạt" if report.ok else "KHÔNG ĐẠT"
    print(f"Tầng 3 (tự kiểm trên file): {verdict}, độ phủ diff {report.diff_coverage:.0%}")
    for error in report.errors:
        print(f"  [lỗi] {error}")
    for warning in report.warnings:
        print(f"  [xem lại] {warning}")
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
