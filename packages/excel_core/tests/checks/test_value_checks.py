"""value_equals, value_type, data_unchanged."""

from datetime import datetime

from excel_core.checks import CheckStatus
from excel_core.snapshot import CellSnapshot


# ---------------------------------------------------------------- value_equals
def test_value_equals_from_solution(kit):
    check = {"type": "value_equals", "range": "F10:F11", "expected": {"from": "solution"}}
    solution = kit.book({"F10": kit.number(1250), "F11": kit.number(300)})
    assert kit.run(
        check, kit.book({"F10": kit.number(1250), "F11": kit.number(300)}), solution=solution
    ).passed
    result = kit.run(check, kit.book({"F10": kit.number(1250), "F11": kit.number(301)}), solution=solution)
    assert (result.code, result.cells) == ("wrong_value", ("F11",))


def test_value_equals_reports_stored_as_text_before_empty(kit):
    check = {"type": "value_equals", "range": "F10:F11", "expected": {"from": "solution"}}
    solution = kit.book({"F10": kit.number(1250), "F11": kit.number(300)})
    result = kit.run(check, kit.book({"F10": kit.text("1,250")}), solution=solution)
    assert (result.code, result.cells) == ("stored_as_text", ("F10",))


def test_value_equals_empty_when_nothing_entered(kit):
    check = {"type": "value_equals", "range": "F10", "expected": {"from": "solution"}}
    result = kit.run(check, kit.book({}), solution=kit.book({"F10": kit.number(5)}))
    assert result.code == "empty"


def test_value_equals_from_other_range_in_same_workbook(kit):
    # b09: Số lượng F10:F14 phải bằng bảng thô F18:F22
    check = {"type": "value_equals", "range": "F10:F11", "expected": {"from": "range", "range": "F18:F19"}}
    current = kit.book(
        {"F10": kit.number(7), "F11": kit.number(8), "F18": kit.number(7), "F19": kit.number(8)}
    )
    assert kit.run(check, current).passed


def test_value_equals_range_of_other_size_is_not_evaluable(kit):
    check = {"type": "value_equals", "range": "F10:F11", "expected": {"from": "range", "range": "F18:F20"}}
    assert kit.run(check, kit.book({})).status == CheckStatus.NOT_EVALUABLE


def test_value_equals_literal_and_tolerance(kit):
    check = {
        "type": "value_equals",
        "range": "H10",
        "expected": {"from": "literal", "value": 4.375},
        "tolerance": 0.005,
    }
    assert kit.run(check, kit.book({"H10": kit.number(4.378)})).passed
    assert not kit.run(check, kit.book({"H10": kit.number(4.39)})).passed


def test_value_equals_text_is_exact(kit):
    # Bài TRIM/UPPER: khoảng trắng và hoa thường đều có nghĩa
    check = {"type": "value_equals", "range": "A1", "expected": {"from": "literal", "value": "Hà Nội"}}
    assert kit.run(check, kit.book({"A1": kit.text("Hà Nội")})).passed
    assert kit.run(check, kit.book({"A1": kit.text("Hà Nội ")})).code == "wrong_value"


def test_value_equals_without_solution_is_not_evaluable(kit):
    check = {"type": "value_equals", "range": "F10", "expected": {"from": "solution"}}
    assert kit.run(check, kit.book({})).status == CheckStatus.NOT_EVALUABLE


# ---------------------------------------------------------------- value_type
def test_value_type_number(kit):
    check = {"type": "value_type", "range": "F10:F12", "kind": "number"}
    current = kit.book({"F10": kit.number(1), "F11": kit.text("1250"), "F12": kit.text("abc")})
    result = kit.run(check, current)
    assert (result.code, result.cells) == ("stored_as_text", ("F11",))
    assert "wrong_type: F12" in result.detail


def test_value_type_date(kit):
    check = {"type": "value_type", "range": "B9:B10", "kind": "date"}
    date_cell = CellSnapshot(value=datetime(2026, 11, 1), value_kind="date")
    assert kit.run(check, kit.book({"B9": date_cell, "B10": date_cell})).passed
    assert kit.run(check, kit.book({"B9": date_cell, "B10": kit.text("01/11/2026")})).code == "stored_as_text"
    assert kit.run(check, kit.book({"B9": date_cell, "B10": kit.number(46327)})).code == "wrong_type"


def test_value_type_empty(kit):
    assert kit.run({"type": "value_type", "range": "A1", "kind": "text"}, kit.book({})).code == "empty"


# ---------------------------------------------------------------- data_unchanged
def test_data_unchanged_passes_when_source_kept(kit):
    check = {"type": "data_unchanged", "range": "C9:D9"}
    data = {"C9": kit.number(25000), "D9": kit.formula("D9", "=C9*2", 50000)}
    assert kit.run(check, kit.book(data), starter=kit.book(data)).passed


def test_data_unchanged_formula_cell_may_change_value(kit):
    check = {"type": "data_unchanged", "range": "H10"}
    starter = kit.book({"H10": kit.formula("H10", "=F10*G10", 0)})
    current = kit.book({"H10": kit.formula("H10", "=F10*G10", 4375)})
    assert kit.run(check, current, starter=starter).passed


def test_data_unchanged_detects_overwritten_formula_first(kit):
    check = {"type": "data_unchanged", "range": "C9:D9"}
    starter = kit.book({"C9": kit.number(1), "D9": kit.formula("D9", "=C9*2", 2)})
    current = kit.book({"C9": kit.number(5), "D9": kit.number(2)})
    result = kit.run(check, current, starter=starter)
    assert (result.code, result.cells) == ("formula_overwritten", ("D9",))
    assert "source_modified: C9" in result.detail
