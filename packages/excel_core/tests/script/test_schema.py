"""Tầng 1 — lược đồ kịch bản v1 (T3.2): lược đồ hợp lệ, ví dụ hợp lệ, và chặn được các lỗi hay gặp."""

import copy
import json
from collections.abc import Callable
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from excel_core.script import find_schema_file, load_script, schema_issues, validate_script

SCHEMA_FILE = find_schema_file()
EXAMPLES = sorted((SCHEMA_FILE.parent / "examples").glob("*.json"))


def test_schema_is_valid_draft_2020_12():
    Draft202012Validator.check_schema(json.loads(SCHEMA_FILE.read_text(encoding="utf-8")))


def test_has_examples():
    assert {p.stem for p in EXAMPLES} >= {"b09-du-lieu-dang-so", "b22-ham-tinh-tong"}


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.stem)
def test_example_passes_tier_1_and_2(path: Path):
    result = validate_script(load_script(path))
    assert result.ok, [str(i) for i in result.schema_issues + result.cross_reference_issues]


@pytest.fixture
def b09() -> dict:
    return load_script(SCHEMA_FILE.parent / "examples" / "b09-du-lieu-dang-so.json")


def mutated(script: dict, change: Callable[[dict], object]) -> dict:
    copied = copy.deepcopy(script)
    change(copied)
    return copied


@pytest.mark.parametrize(
    ("label", "change"),
    [
        ("thiếu cấp gợi ý 4", lambda s: s["steps"][0]["hints"].pop()),
        ("cấp gợi ý sai thứ tự", lambda s: s["steps"][0]["hints"].reverse()),
        ("cấp 3 không chỉ vị trí", lambda s: s["steps"][0]["hints"][2].pop("highlight")),
        ("cấp 4 không có thao tác", lambda s: s["steps"][0]["hints"][3].pop("actions")),
        (
            "địa chỉ ghép nhiều vùng",
            lambda s: s["steps"][0]["targets"]["cells"][0].update(range="A1:A5,C1:C5"),
        ),
        ("địa chỉ có tên sheet", lambda s: s["steps"][0]["targets"]["cells"][0].update(range="Sheet1!A1")),
        (
            "loại điều kiện không có",
            lambda s: s["steps"][0]["checks"].append({"type": "magic", "range": "A1"}),
        ),
        ("tham số lạ trong điều kiện", lambda s: s["steps"][0]["checks"][0].update(foo=1)),
        ("value_equals thiếu expected", lambda s: s["steps"][0]["checks"][0].pop("expected")),
        (
            "number_format không có tiêu chí",
            lambda s: s["steps"][1]["checks"].__setitem__(0, {"type": "number_format", "range": "F10:F14"}),
        ),
        ("bước không có điều kiện", lambda s: s["steps"][0].update(checks=[])),
        (
            "điều kiện toàn bài không phải loại bảo vệ",
            lambda s: s["global_checks"].append({"type": "font", "range": "A1", "bold": True}),
        ),
        (
            "nút Ribbon lưu theo tên hiển thị có dấu cách",
            lambda s: s["steps"][1]["targets"]["ui"][0].update(control="Comma Style"),
        ),
        ("sai phiên bản lược đồ", lambda s: s.update(schema_version="2")),
        ("mã bài có chữ hoa", lambda s: s["exercise"].update(id="B09")),
    ],
)
def test_rejects_invalid(b09: dict, label: str, change: Callable[[dict], object]):
    assert schema_issues(mutated(b09, change)), f"lược đồ phải chặn: {label}"


def test_issue_has_json_pointer_path(b09: dict):
    issues = schema_issues(mutated(b09, lambda s: s["steps"][0]["checks"][0].update(foo=1)))
    assert any(i.path.startswith("/steps/0/checks/0") for i in issues)


def test_tier_2_is_skipped_when_tier_1_fails(b09: dict):
    result = validate_script(mutated(b09, lambda s: s.update(schema_version="2")))
    assert not result.schema_ok
    assert result.cross_reference_issues == ()
