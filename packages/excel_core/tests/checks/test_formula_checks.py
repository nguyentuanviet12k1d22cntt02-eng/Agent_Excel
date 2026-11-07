"""is_formula, formula_uses_function, formula_consistent, formula_matches_r1c1."""

import pytest


# ---------------------------------------------------------------- is_formula
def test_is_formula(kit):
    check = {"type": "is_formula", "range": "F9:F11"}
    current = kit.book({"F9": kit.formula("F9", "=SUM(C9:E9)", 60), "F10": kit.number(60)})
    result = kit.run(check, current)
    assert (result.code, result.cells) == ("hardcoded_value", ("F10",))
    assert "empty: F11" in result.detail


# ---------------------------------------------------------------- formula_uses_function
@pytest.mark.parametrize(
    ("a1", "code"),
    [
        ("=SUM(C9:E9)", None),
        ("=SUM(C9,D9,E9)", None),  # câu hỏi GVHD b22: bản nháp chấp nhận
        ("=sum(c9:e9)", None),
        ("=C9+D9+E9", "used_operator_instead"),
        ("=SUM(C9+D9+E9)", "used_operator_instead"),
        ("=AVERAGE(C9:E9)", "missing_function"),
        ("=SUM(C9:E9)*1.1", None),
    ],
)
def test_formula_uses_function(kit, a1: str, code: str | None):
    check = {"type": "formula_uses_function", "range": "F9", "functions": ["SUM"]}
    result = kit.run(check, kit.book({"F9": kit.formula("F9", a1, 60)}))
    assert result.code == code


def test_formula_uses_function_can_allow_operator_style(kit):
    check = {
        "type": "formula_uses_function",
        "range": "F9",
        "functions": ["SUM"],
        "forbid_operator_only": False,
    }
    assert kit.run(check, kit.book({"F9": kit.formula("F9", "=SUM(C9+D9+E9)", 60)})).passed
    assert kit.run(check, kit.book({"F9": kit.formula("F9", "=C9+D9+E9", 60)})).code == "missing_function"


def test_formula_uses_function_accepts_any_listed_function(kit):
    check = {"type": "formula_uses_function", "range": "A1", "functions": ["CONCAT", "CONCATENATE"]}
    assert kit.run(check, kit.book({"A1": kit.formula("A1", '=_xlfn.CONCAT(B1," ",C1)')})).passed


def test_formula_uses_function_value_typed_by_hand(kit):
    check = {"type": "formula_uses_function", "range": "F9", "functions": ["SUM"]}
    assert kit.run(check, kit.book({"F9": kit.number(60)})).code == "missing_function"


# ---------------------------------------------------------------- formula_consistent
def column(kit, a1_by_row: dict[int, str]):
    return kit.book({f"F{r}": kit.formula(f"F{r}", a1) for r, a1 in a1_by_row.items()})


def test_formula_consistent_copied_down(kit):
    check = {"type": "formula_consistent", "range": "F9:F11"}
    assert kit.run(check, column(kit, {r: f"=SUM(C{r}:E{r})" for r in (9, 10, 11)})).passed


def test_formula_consistent_detects_retyped_cell(kit):
    check = {"type": "formula_consistent", "range": "F9:F11"}
    current = column(kit, {9: "=SUM(C9:E9)", 10: "=SUM(C10:E10)", 11: "=C11+D11+E11"})
    result = kit.run(check, current)
    assert (result.code, result.cells) == ("inconsistent_formula", ("F11",))


def test_formula_consistent_flags_absolute_copy(kit):
    # $ khi sao chép: R1C1 vẫn đồng nhất (đã kiểm chứng trên Excel), mọi ô ra cùng kết quả
    check = {"type": "formula_consistent", "range": "F9:F11"}
    result = kit.run(check, column(kit, dict.fromkeys((9, 10, 11), "=SUM($C$9:$E$9)")))
    assert result.code == "absolute_reference"


def test_formula_consistent_allows_mixed_reference(kit):
    # Thuế suất cố định ở $B$2, số lượng đổi theo dòng: hợp lệ
    check = {"type": "formula_consistent", "range": "F9:F10"}
    assert kit.run(check, column(kit, {9: "=E9*$B$2", 10: "=E10*$B$2"})).passed


def test_formula_consistent_copied_across(kit):
    check = {"type": "formula_consistent", "range": "C20:E20"}
    current = kit.book({f"{c}20": kit.formula(f"{c}20", f"=SUM({c}9:{c}19)") for c in "CDE"})
    assert kit.run(check, current).passed


def test_formula_consistent_empty_cells(kit):
    check = {"type": "formula_consistent", "range": "F9:F11"}
    result = kit.run(check, column(kit, {9: "=SUM(C9:E9)"}))
    assert (result.code, result.cells) == ("empty", ("F10", "F11"))


# ---------------------------------------------------------------- formula_matches_r1c1
def test_formula_matches_r1c1(kit):
    check = {"type": "formula_matches_r1c1", "range": "H10:H11", "r1c1": "=RC[-2]*RC[-1]"}
    good = kit.book({"H10": kit.formula("H10", "=F10*G10"), "H11": kit.formula("H11", "=F11*G11")})
    assert kit.run(check, good).passed
    swapped = kit.book({"H10": kit.formula("H10", "=F10*G10"), "H11": kit.formula("H11", "=G11*F11")})
    assert kit.run(check, swapped).code == "wrong_formula"


def test_formula_matches_r1c1_value_typed_over_formula(kit):
    # b09 bước 4: gõ đè số lên công thức → mã hardcoded_value (phản hồi ngay)
    check = {"type": "formula_matches_r1c1", "range": "H10", "r1c1": "=RC[-2]*RC[-1]"}
    assert kit.run(check, kit.book({"H10": kit.number(4375)})).code == "hardcoded_value"
