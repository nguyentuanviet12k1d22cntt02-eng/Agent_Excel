"""Chỉ số đánh giá kịch bản AI so với kịch bản viết tay (T5.8)."""

import copy
import json
from pathlib import Path

import pytest

from tutor_backend.ai.evaluation import (
    RunResult,
    check_agreement,
    edit_rate,
    markdown_table,
    step_match_rate,
    summary_rows,
)

EXAMPLES = Path(__file__).resolve().parents[4] / "schemas" / "tutor-script" / "v1" / "examples"


@pytest.fixture
def b09() -> dict:
    return json.loads((EXAMPLES / "b09-du-lieu-dang-so.json").read_text(encoding="utf-8"))


def test_identical_scripts_match_fully(b09: dict):
    assert step_match_rate(b09, b09) == 1.0
    assert check_agreement(b09, b09) == 1.0
    assert edit_rate(b09, b09) == 0.0


def test_step_matching_uses_target_overlap(b09: dict):
    merged = copy.deepcopy(b09)
    # AI gộp bước định dạng Số lượng vào bước nhập Số lượng: cùng vùng F10:F14 nên vẫn khớp cả hai
    merged["steps"][0]["checks"] += merged["steps"][1]["checks"]
    del merged["steps"][1]
    assert step_match_rate(merged, b09) == 1.0
    moved = copy.deepcopy(b09)
    # Bước Đơn giá (G10:G14) là bước duy nhất làm vùng đó: AI làm sai chỗ thì bước tay này không khớp
    moved["steps"][2]["targets"]["cells"] = [{"range": "A1", "role": "target"}]
    assert step_match_rate(moved, b09) == pytest.approx(5 / 6)


def test_check_agreement_counts_missing_checks(b09: dict):
    fewer = copy.deepcopy(b09)
    fewer["steps"][1]["checks"] = [{"type": "value_type", "range": "F10:F14", "kind": "number"}]
    total = len(b09["global_checks"]) + sum(len(s["checks"]) for s in b09["steps"])
    assert check_agreement(fewer, b09) == pytest.approx((total - 1) / total)


def test_edit_rate_counts_changed_or_removed_steps(b09: dict):
    edited = copy.deepcopy(b09)
    edited["steps"][0]["task"] = "Câu chữ giảng viên viết lại."
    del edited["steps"][5]
    assert edit_rate(b09, edited) == pytest.approx(2 / 6)


def test_summary_table_averages_runs():
    results = [
        RunResult("b22", 1, True, 1, 4000, 2000, 5000, 2, 1.0, 0, 1.0, 0.9),
        RunResult("b22", 2, True, 2, 6000, 3000, 7000, 3, 1.0, 0, 0.5, 0.7),
    ]

    class Case:
        name = "b22"
        reference = {"steps": [1, 2, 3]}

    (row,) = summary_rows(results, [Case()])  # type: ignore[list-item]
    assert row == ["b22", "2/2", "1.5", "6.0", "5000 / 2500", "2.5 (3)", "100%", "0", "75%", "80%"]
    assert markdown_table(["A", "B"], [["1", "2"]]).splitlines() == ["| A | B |", "|---|---|", "| 1 | 2 |"]
