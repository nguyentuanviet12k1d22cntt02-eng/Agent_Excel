"""Bảng đăng ký điều kiện: đủ loại theo lược đồ, mã lỗi khớp mô tả, gộp yêu cầu đọc."""

import json
import re
from pathlib import Path

import pytest

from excel_core.checks import (
    DEFINITIONS,
    CheckStatus,
    codes_for,
    read_requests,
    reference_requests,
    run_check,
)
from excel_core.snapshot import PropertyGroup

SCHEMA = json.loads(
    (Path(__file__).resolve().parents[4] / "schemas/tutor-script/v1/tutor-script.schema.json").read_text(
        encoding="utf-8"
    )
)
SCHEMA_TYPES = sorted(ref["$ref"].removeprefix("#/$defs/check_") for ref in SCHEMA["$defs"]["check"]["oneOf"])


def test_every_schema_check_type_has_an_implementation():
    assert sorted(DEFINITIONS) == SCHEMA_TYPES


@pytest.mark.parametrize("check_type", SCHEMA_TYPES)
def test_schema_description_lists_the_codes_the_check_returns(check_type: str):
    # Mô tả trong lược đồ là tài liệu cho giảng viên và AI viết feedback[].code: phải khớp với code
    description = SCHEMA["$defs"][f"check_{check_type}"]["description"]
    match = re.search(r"Mã lỗi: ([a-z_, ]+)\.", description)
    assert match, f"check_{check_type}: mô tả chưa liệt kê mã lỗi"
    listed = {c.strip() for c in match.group(1).split(",")}
    assert listed == set(codes_for(check_type))


def test_unknown_check_type_is_not_evaluable(kit):
    result = run_check({"type": "magic"}, kit.ctx(kit.book()))
    assert result.status == CheckStatus.NOT_EVALUABLE


def test_read_requests_are_grouped_by_source():
    checks = [
        {"type": "value_equals", "range": "F10:F14", "expected": {"from": "solution"}},
        {"type": "number_format", "range": "F10:F14", "decimals": 0},
        {"type": "data_unchanged", "range": "B17:I22"},
        {"type": "page_setup", "orientation": "landscape", "sheet": "In"},
    ]
    requests = read_requests(checks, "S")
    current = {(r.sheet, r.range): r.groups for r in requests["current"].ranges}
    assert current[("S", "F10:F14")] == {PropertyGroup.VALUES, PropertyGroup.NUMBER_FORMAT}
    assert requests["current"].sheet_groups("In") == {PropertyGroup.PAGE_SETUP}
    assert {r.range for r in requests["solution"].ranges} == {"F10:F14"}
    assert {r.range for r in requests["starter"].ranges} == {"B17:I22"}
    assert set(reference_requests(checks, "S")) == {"solution", "starter"}


def test_renamed_sheet_is_not_evaluable_instead_of_crashing(kit):
    # Học viên đổi tên sheet làm bài: Desktop không được dừng giữa phiên
    check = {"type": "is_formula", "range": "A1", "sheet": "Bài 01"}
    result = run_check(check, kit.ctx(kit.book(names=("Bài 01 (đã đổi)",))))
    assert result.status == CheckStatus.NOT_EVALUABLE
    assert "không có sheet" in result.detail
