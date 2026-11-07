"""Tầng 2 — ràng buộc chéo mà lược đồ không diễn tả được."""

import copy
from collections.abc import Callable

import pytest

from excel_core.script import cross_reference_issues, find_schema_file, load_script, schema_issues

EXAMPLES = find_schema_file().parent / "examples"


@pytest.fixture
def b09() -> dict:
    return load_script(EXAMPLES / "b09-du-lieu-dang-so.json")


@pytest.fixture
def b22() -> dict:
    return load_script(EXAMPLES / "b22-ham-tinh-tong.json")


def broken(script: dict, change: Callable[[dict], object]) -> list[str]:
    copied = copy.deepcopy(script)
    change(copied)
    assert schema_issues(copied) == [], "ca test phải hợp lệ theo lược đồ để thấy được tầng 2"
    return [str(i) for i in cross_reference_issues(copied)]


def test_missing_reference(b09: dict):
    issues = broken(b09, lambda s: s["steps"][1].update(reference_ids=["ref_khong_co"]))
    assert issues == ["/steps/1: không có nguồn trích dẫn ref_khong_co"]


def test_duplicate_step_id(b22: dict):
    issues = broken(b22, lambda s: s["steps"][1].update(id=s["steps"][0]["id"]))
    assert "/steps: trùng id bước s1_first_total" in issues


def test_completion_points_to_missing_step(b22: dict):
    issues = broken(b22, lambda s: s["completion"]["criteria"][0]["step_ids"].append("s9_khong_co"))
    assert issues == ["/completion/criteria/0: trỏ tới bước không có: s9_khong_co"]


def test_feedback_code_must_be_returnable(b22: dict):
    # s1 không có điều kiện nào trả "missing_sheet"
    issues = broken(
        b22, lambda s: s["steps"][0]["feedback"].append({"code": "missing_sheet", "message": "x"})
    )
    assert issues == ["/steps/0/feedback/3/code: không điều kiện nào của bước trả mã missing_sheet"]


def test_feedback_code_from_global_check_is_allowed(b09: dict):
    feedback = {"code": "source_modified", "message": "Bạn vừa sửa bảng số liệu thô."}
    assert broken(b09, lambda s: s["steps"][0]["feedback"].append(feedback)) == []


def test_immediate_code_must_be_returnable(b09: dict):
    issues = broken(b09, lambda s: s["steps"][3]["signals"]["immediate_codes"].append("missing_chart"))
    assert issues == ["/steps/3/signals/immediate_codes: không điều kiện nào của bước trả mã missing_chart"]


def test_duplicate_feedback_code(b22: dict):
    duplicate = {"code": "wrong_value", "message": "Lặp lại"}
    assert "/steps/2/feedback: mã wrong_value có hơn một phản hồi" in broken(
        b22, lambda s: s["steps"][2]["feedback"].append(duplicate)
    )


def test_highlight_must_stay_inside_targets(b09: dict):
    def move_highlight(s: dict) -> None:
        s["steps"][1]["hints"][2]["highlight"][0]["cells"]["range"] = "F10:F20"

    assert broken(b09, move_highlight) == [
        "/steps/1/hints/2/highlight/0: vùng F10:F20 không nằm trong targets.cells của bước"
    ]


def test_highlight_button_must_be_a_target(b09: dict):
    def other_button(s: dict) -> None:
        s["steps"][1]["hints"][2]["highlight"][1]["ui"]["control"] = "AlignRight"

    assert broken(b09, other_button) == [
        "/steps/1/hints/2/highlight/1: nút AlignRight không có trong targets.ui của bước"
    ]


def test_expected_range_must_have_same_size(b09: dict):
    def shrink(s: dict) -> None:
        s["steps"][0]["checks"][0]["expected"]["range"] = "F18:F21"

    assert broken(b09, shrink) == [
        "/steps/0/checks/0/expected: vùng F18:F21 khác kích thước vùng kiểm F10:F14"
    ]


def test_duplicate_check_id(b09: dict):
    issues = broken(b09, lambda s: s["steps"][0]["checks"][0].update(id="raw_table_kept"))
    assert issues == ["/: trùng id điều kiện raw_table_kept"]
