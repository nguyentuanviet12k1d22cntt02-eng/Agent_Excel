"""Lược đồ kịch bản v1 (T3.2): lược đồ hợp lệ, ví dụ hợp lệ, và chặn được các lỗi hay gặp."""

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

SCHEMA_DIR = Path(__file__).resolve().parents[3] / "schemas" / "tutor-script" / "v1"
SCHEMA = json.loads((SCHEMA_DIR / "tutor-script.schema.json").read_text(encoding="utf-8"))
EXAMPLES = sorted((SCHEMA_DIR / "examples").glob("*.json"))
VALIDATOR = Draft202012Validator(SCHEMA)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def errors(script: dict) -> list[str]:
    return [e.message for e in VALIDATOR.iter_errors(script)]


def cross_reference_errors(script: dict) -> list[str]:
    """Ràng buộc lược đồ JSON không diễn tả được: id không trùng, id được trỏ tới phải tồn tại."""
    problems = []
    step_ids = [s["id"] for s in script["steps"]]
    ref_ids = {r["id"] for r in script.get("references", [])}
    if len(step_ids) != len(set(step_ids)):
        problems.append("trùng id bước")
    for step in script["steps"]:
        for ref in step.get("reference_ids", []) + [
            r for h in step["hints"] for r in h.get("reference_ids", [])
        ]:
            if ref not in ref_ids:
                problems.append(f"{step['id']}: không có nguồn {ref}")
        for i, hint in enumerate(step["hints"], start=1):
            if hint["level"] != i:
                problems.append(f"{step['id']}: gợi ý thứ {i} có level {hint['level']}")
    for criterion in script.get("completion", {}).get("criteria", []):
        problems += [
            f"tiêu chí trỏ tới bước không có: {s}" for s in criterion["step_ids"] if s not in step_ids
        ]
    return problems


def test_schema_is_valid_draft_2020_12():
    Draft202012Validator.check_schema(SCHEMA)


def test_has_examples():
    assert {p.stem for p in EXAMPLES} >= {"b09-du-lieu-dang-so", "b22-ham-tinh-tong"}


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.stem)
def test_example_is_valid(path: Path):
    script = load(path)
    assert errors(script) == []
    assert cross_reference_errors(script) == []


@pytest.fixture
def b09() -> dict:
    return load(SCHEMA_DIR / "examples" / "b09-du-lieu-dang-so.json")


def mutated(script: dict, change: callable) -> dict:
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
def test_rejects_invalid(b09: dict, label: str, change: callable):
    assert errors(mutated(b09, change)), f"lược đồ phải chặn: {label}"


def test_cross_reference_catches_missing_reference(b09: dict):
    broken = mutated(b09, lambda s: s["steps"][1].update(reference_ids=["ref_khong_co"]))
    assert errors(broken) == []
    assert cross_reference_errors(broken) == ["s2_quantity_format: không có nguồn ref_khong_co"]
