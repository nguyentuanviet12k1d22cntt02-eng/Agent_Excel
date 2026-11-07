"""Dựng kịch bản v1 từ phân tích + kế hoạch; kịch bản dựng ra phải qua 3 tầng kiểm (T5.5)."""

from pathlib import Path

from excel_core.script import self_check_files, validate_script
from tutor_backend.ai.exercise_analysis import analyze_exercise
from tutor_backend.ai.plan import parse_plan, plan_issues, plan_schema
from tutor_backend.ai.script_builder import ExerciseInfo, build_script, merge_checks, step_id

FIXTURES = Path(__file__).resolve().parents[4] / "packages" / "excel_core" / "tests" / "fixtures"
B22 = (FIXTURES / "b22" / "de.xlsx", FIXTURES / "b22" / "dap-an.xlsx")


def test_merge_checks_joins_adjacent_columns_and_keeps_order():
    checks = [
        {"type": "alignment", "range": "F10:F14", "horizontal": ["right"]},
        {"type": "value_equals", "range": "F10:F14", "expected": {"from": "range", "range": "F18:F22"}},
        {"type": "alignment", "range": "G10:G14", "horizontal": ["right"]},
        {"type": "value_equals", "range": "G10:G14", "expected": {"from": "range", "range": "G18:G22"}},
    ]
    assert merge_checks(checks) == [
        {"type": "alignment", "range": "F10:G14", "horizontal": ["right"]},
        {"type": "value_equals", "range": "F10:F14", "expected": {"from": "range", "range": "F18:F22"}},
        {"type": "value_equals", "range": "G10:G14", "expected": {"from": "range", "range": "G18:G22"}},
    ]


def test_step_ids_are_ascii_and_unique():
    used: set[str] = set()
    assert step_id(1, "Định dạng Số lượng", used) == "s1_dinh_dang_so_luong"
    assert step_id(1, "Định dạng Số lượng", used) == "s1_dinh_dang_so_luong_2"
    assert step_id(3, "!!!", used) == "s3"


def test_b22_plan_builds_a_valid_script(b22_plan_factory):
    analysis = analyze_exercise(*B22, "Bài 01")
    schema = plan_schema(analysis, [])
    plan = parse_plan(b22_plan_factory(), schema)
    assert plan_issues(plan, analysis) == []
    info = ExerciseInfo("b22-ham-tinh-tong", "Hàm tính tổng SUM", "Bài 01")
    script = build_script(analysis, plan, info, {}, "fake-model")
    validation = validate_script(script)
    assert validation.ok, [str(i) for i in validation.schema_issues + validation.cross_reference_issues]
    report = self_check_files(script, *B22)
    assert report.ok, report.errors
    assert report.diff_coverage == 1.0
    first = script["steps"][0]
    assert first["targets"]["ui"] == [
        {"tab": "TabHome", "control": "AutoSum", "label": "AutoSum (Σ, tự gõ hàm SUM)"}
    ]
    assert [c["type"] for c in first["checks"]] == [
        "is_formula",
        "formula_uses_function",
        "formula_consistent",
        "value_equals",
    ]
    assert first["hints"][2]["highlight"][-1] == {"ui": {"tab": "TabHome", "control": "AutoSum"}}
    assert script["global_checks"][0]["range"] == "C9:E19"


def test_plan_issues_report_missing_and_duplicated_changes(b22_plan_factory):
    analysis = analyze_exercise(*B22, "Bài 01")
    data = b22_plan_factory()
    data["steps"][1]["change_ids"] = ["c1"]  # c2 bị bỏ sót, c1 nằm ở hai bước
    plan = parse_plan(data, plan_schema(analysis, []))
    assert plan_issues(plan, analysis) == [
        "Thay đổi c1 nằm ở cả bước 1 và bước 2: chỉ để một bước",
        "Thay đổi c2 chưa thuộc bước nào: mỗi thay đổi phải thuộc đúng một bước",
    ]


def test_feedback_for_codes_the_step_cannot_return_is_dropped(b22_plan_factory):
    analysis = analyze_exercise(*B22, "Bài 01")
    data = b22_plan_factory()
    data["steps"][1]["feedback"] = [{"code": "source_modified", "message": "Đừng sửa số liệu gốc."}]
    plan = parse_plan(data, plan_schema(analysis, []))
    script = build_script(analysis, plan, ExerciseInfo("b22-ham-tinh-tong", "SUM", "Bài 01"), {}, "m")
    # source_modified đến từ điều kiện toàn bài data_unchanged nên được giữ
    assert script["steps"][1]["feedback"] == [{"code": "source_modified", "message": "Đừng sửa số liệu gốc."}]
