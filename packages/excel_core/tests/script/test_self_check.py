"""Tầng 3 — tự kiểm trên file đề và file đáp án (T4.5: "2 kịch bản viết tay chạy qua được")."""

import copy
import os
from collections.abc import Callable
from pathlib import Path

import pytest

from excel_core.readers import read_workbook
from excel_core.script import find_schema_file, load_script, self_check, self_check_files, self_check_request

EXAMPLES = find_schema_file().parent / "examples"
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
CASES = {"b09": "b09-du-lieu-dang-so", "b22": "b22-ham-tinh-tong"}


def files(name: str) -> tuple[Path, Path]:
    return FIXTURES / name / "de.xlsx", FIXTURES / name / "dap-an.xlsx"


@pytest.mark.parametrize("name", sorted(CASES))
def test_hand_written_scripts_pass_self_check(name: str):
    report = self_check_files(load_script(EXAMPLES / f"{CASES[name]}.json"), *files(name))
    assert report.ok, report.errors
    assert report.diff_coverage == 1.0
    assert all(c.passes_on_solution for c in report.checks)
    assert report.hint_text_issues == ()


def test_guard_check_passing_on_starter_is_only_a_warning():
    # b09 bước 4: công thức Thành tiền có sẵn trên đề; điều kiện giữ công thức đạt sẵn là đúng ý
    report = self_check_files(load_script(EXAMPLES / "b09-du-lieu-dang-so.json"), *files("b09"))
    assert report.ok
    assert any("s4_amount_format" in w and "formula_matches_r1c1" in w for w in report.warnings)


@pytest.fixture(scope="module")
def b22_snapshots():
    script = load_script(EXAMPLES / "b22-ham-tinh-tong.json")
    request = self_check_request(script, *files("b22"))
    starter, solution = files("b22")
    return script, read_workbook(starter, request), read_workbook(solution, request)


def run_mutated(snapshots, change: Callable[[dict], object]):
    script, starter, solution = snapshots
    copied = copy.deepcopy(script)
    change(copied)
    return self_check(copied, starter, solution)


def test_check_failing_on_solution_is_an_error(b22_snapshots):
    def wrong_function(s: dict) -> None:
        s["steps"][0]["checks"][1]["functions"] = ["AVERAGE"]

    report = run_mutated(b22_snapshots, wrong_function)
    assert not report.ok
    assert any("s1_first_total" in e and "không đạt trên đáp án" in e for e in report.errors)


def test_step_already_done_on_starter_is_an_error(b22_snapshots):
    def only_guard(s: dict) -> None:
        s["steps"][0]["checks"] = [{"type": "data_unchanged", "range": "C9:E19"}]

    report = run_mutated(b22_snapshots, only_guard)
    assert "bước s1_first_total: mọi điều kiện đã đạt sẵn trên file đề" in report.errors


def test_uncovered_diff_is_reported(b22_snapshots):
    report = run_mutated(b22_snapshots, lambda s: s["steps"].pop())  # bỏ bước dòng TỔNG CỘNG
    assert report.diff_coverage == 0.5
    assert report.uncovered_ranges == ("Bài 01!C20:F20 (formula)",)


def test_hint_text_with_address_and_invented_number(b22_snapshots):
    def chatty_hint(s: dict) -> None:
        s["steps"][0]["hints"][1]["text"] = "Gõ =SUM(C9:E9) vào ô F9, kết quả sẽ là 123.456."

    issues = run_mutated(b22_snapshots, chatty_hint).hint_text_issues
    assert {i["text"] for i in issues} == {"C9:E9", "F9", "123.456"}


def test_function_keys_and_paper_sizes_are_not_addresses(b22_snapshots):
    def keys(s: dict) -> None:
        s["steps"][0]["hints"][1]["text"] = "Bấm F4 để cố định địa chỉ, in trên khổ A4."

    assert run_mutated(b22_snapshots, keys).hint_text_issues == ()


def test_report_to_dict_matches_api_shape(b22_snapshots):
    data = run_mutated(b22_snapshots, lambda s: None).to_dict()
    assert set(data) >= {"checks", "diff_coverage", "uncovered_ranges", "hint_text_issues"}
    assert set(data["checks"][0]) >= {"step_id", "check_index", "passes_on_solution", "fails_on_starter"}


LOCAL = Path(__file__).resolve().parents[4] / "samples" / "_local"


@pytest.mark.parametrize("name", sorted(CASES))
def test_hand_written_scripts_on_center_samples(name: str):
    """Chạy trên bài gốc của trung tâm (không lên git): chỉ khi bật EXCEL_CORE_LOCAL_SAMPLES=1."""
    folder = LOCAL / CASES[name]
    if os.environ.get("EXCEL_CORE_LOCAL_SAMPLES") != "1" or not (folder / "dap-an.xlsx").is_file():
        pytest.skip("cần samples/_local và EXCEL_CORE_LOCAL_SAMPLES=1")
    report = self_check_files(
        load_script(EXAMPLES / f"{CASES[name]}.json"), folder / "de.xlsx", folder / "dap-an.xlsx"
    )
    assert report.ok, report.errors
