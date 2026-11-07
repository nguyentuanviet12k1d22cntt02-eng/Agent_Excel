"""Phân tích bài trước khi gọi AI: thay đổi, nhãn, vùng nguồn, vùng giữ nguyên, sắp xếp (T5.5)."""

from pathlib import Path

import pytest

from tutor_backend.ai.exercise_analysis import analyze_exercise

FIXTURES = Path(__file__).resolve().parents[4] / "packages" / "excel_core" / "tests" / "fixtures"
SHEETS = {"b09": "2. Bang_Ke_Ban_Hang", "b22": "Bài 01", "b14": "Bang_Diem", "b16": "Bai 01"}


def analyze(name: str):
    return analyze_exercise(FIXTURES / name / "de.xlsx", FIXTURES / name / "dap-an.xlsx", SHEETS[name])


@pytest.fixture(scope="module")
def b09():
    return analyze("b09")


def test_b09_value_changes_point_to_raw_table(b09):
    values = {c.range: c for c in b09.changes if c.kind == "value"}
    assert set(values) == {"F10:F14", "G10:G14", "I10:I14"}
    quantity = values["F10:F14"]
    assert quantity.label == "cột Số lượng"
    assert quantity.context == "mỗi dòng ứng với một Mã hàng"
    assert quantity.sources[0][0] == "F18:F22"
    assert quantity.checks[0]["expected"] == {"from": "range", "range": "F18:F22"}
    assert quantity.checks[1] == {"type": "value_type", "range": "F10:F14", "kind": "number"}


def test_b09_number_formats_are_checked_by_meaning(b09):
    formats = {c.range: c.checks[0] for c in b09.changes if c.kind == "number_format"}
    assert formats["F10:F14"] == {
        "type": "number_format",
        "range": "F10:F14",
        "categories": ["number", "accounting"],
        "decimals": 0,
        "thousands_separator": True,
    }
    assert formats["I10:I14"]["decimals"] == 3


def test_b09_protects_existing_formulas_and_raw_data(b09):
    assert {(c["type"], c["range"]) for c in b09.global_checks} == {
        ("is_formula", "H10:H14"),
        ("data_unchanged", "B16:I22"),
    }
    assert any("KHÔNG được gõ đè" in p for p in b09.preserved)


def test_descriptions_never_contain_cell_addresses_or_values():
    analysis = analyze("b22")
    for change in analysis.changes:
        assert "C9" not in change.description and "=SUM" not in change.description
    assert (
        analysis.changes[0].description == "nhập công thức: dùng hàm SUM; một công thức sao chép cho cả vùng"
    )
    assert (analysis.changes[0].label, analysis.changes[0].context) == (
        "cột Tổng tiền",
        "mỗi dòng ứng với một Ngày",
    )
    assert analysis.global_checks == (
        {"type": "data_unchanged", "range": "C9:E19", "description": "Không sửa dữ liệu gốc."},
    )


def test_b16_sort_is_recognised():
    (change,) = analyze("b16").changes
    assert change.kind == "sort"
    assert change.checks == ({"type": "sorted_by", "range": "A3:D9", "key_column": "Lương", "order": "desc"},)


def test_b14_formatting_and_auto_row_height():
    analysis = analyze("b14")
    kinds = {(c.kind, c.range) for c in analysis.changes}
    assert ("merged", "A1:E1") in kinds
    assert ("border", "A3:E8") in kinds
    assert not any(c.kind == "row_height" for c in analysis.changes)  # Excel tự giãn dòng khi chữ to lên
    header = next(c for c in analysis.changes if c.kind == "font" and c.range == "A3:E3")
    assert header.label.startswith("dòng tiêu đề STT, Họ tên")
    assert header.checks == ({"type": "font", "range": "A3:E3", "bold": True},)
