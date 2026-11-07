import pytest

from excel_core.formula import (
    FormulaError,
    is_r1c1_absolute_along,
    normalize_formula,
    normalize_r1c1,
    parse_formula,
    reference_to_r1c1,
    to_r1c1,
)

# Các mẫu ở b18, b22: tương đối, tuyệt đối, hỗn hợp, vùng, khác sheet (snapshot.md mục 8)
# (công thức, dòng, cột, R1C1 mong đợi)
R1C1_CASES = [
    ("=SUM(C9:E9)", 9, 6, "=SUM(RC[-3]:RC[-1])"),
    ("=F10*G10", 10, 8, "=RC[-2]*RC[-1]"),
    ("=$C$9", 10, 6, "=R9C3"),
    ("=C$9+$C9", 10, 6, "=R9C[-3]+R[-1]C3"),
    ("=SUM(C9:C19)", 20, 3, "=SUM(R[-11]C:R[-1]C)"),
    ("='Bài 01'!C9*2", 9, 6, "='Bài 01'!RC[-3]*2"),
    ("=SUM(A:A)", 5, 3, "=SUM(C[-2])"),
    ("=SUM(2:2)", 5, 3, "=SUM(R[-3])"),
    ("=sum( c9 , d9 )", 9, 6, "=SUM(RC[-3],RC[-2])"),
    ('=IF(A1>=5,"Đạt ", "Không")', 1, 2, '=IF(RC[-1]>=5,"Đạt ","Không")'),
    ("=Table1[Đơn giá]*2", 3, 3, "=Table1[Đơn giá]*2"),
    ("=TaxRate*B2", 2, 3, "=TAXRATE*RC[-1]"),
]


@pytest.mark.parametrize(("formula", "row", "col", "expected"), R1C1_CASES)
def test_to_r1c1(formula: str, row: int, col: int, expected: str):
    assert to_r1c1(formula, row, col) == expected


def test_copied_formulas_share_one_r1c1():
    # Sao chép =SUM(C9:E9) từ F9 xuống F10 thành =SUM(C10:E10): R1C1 giống nhau
    assert to_r1c1("=SUM(C9:E9)", 9, 6) == to_r1c1("=SUM(C10:E10)", 10, 6)


def test_absolute_copy_also_shares_one_r1c1():
    # Đã kiểm chứng trên Excel thật: lỗi $ không làm R1C1 khác nhau (danh-muc-dieu-kien.md 2.2)
    assert to_r1c1("=SUM($C$9:$E$9)", 9, 6) == to_r1c1("=SUM($C$9:$E$9)", 10, 6) == "=SUM(R9C3:R9C5)"


def test_intersection_space_is_kept():
    assert to_r1c1("=SUM(A1:B2 B1:B3)", 1, 1) == "=SUM(RC:R[1]C[1] RC[1]:R[2]C[1])"


def test_reference_to_r1c1_keeps_names():
    assert reference_to_r1c1("MyRange", 1, 1) == "MyRange"


def test_parse_formula_lists_functions_without_xlfn_prefix():
    parts = parse_formula('=_xlfn.CONCAT(LEFT(A1,2), " ", sum(B1:B3))')
    assert parts.functions == ("CONCAT", "LEFT", "SUM")
    assert parts.references == ("A1", "B1:B3")


def test_parse_formula_lists_infix_operators():
    assert parse_formula("=C9+D9+E9").infix_operators == ("+", "+")
    assert parse_formula("=-A1%").infix_operators == ()


def test_normalize_formula_keeps_text_literals():
    assert normalize_formula('= left( a1 , 2 ) & " ab "') == '=LEFT(A1,2)&" ab "'


def test_normalize_r1c1_accepts_hand_written_lowercase():
    assert normalize_r1c1("=rc[-2] * rc[-1]") == "=RC[-2]*RC[-1]"


@pytest.mark.parametrize(
    ("r1c1", "axis", "expected"),
    [
        ("=SUM(R9C3:R9C5)", "R", True),
        ("=SUM(RC[-3]:RC[-1])", "R", False),
        ("=RC[-1]*R2C2", "R", False),  # có một tham chiếu đổi theo dòng: hợp lệ
        ("=SUM(R[-11]C:R[-1]C)", "C", False),
        ("=SUM(R9C:R19C)", "R", True),
        ("=5*2", "R", False),
    ],
)
def test_is_r1c1_absolute_along(r1c1: str, axis: str, expected: bool):
    assert is_r1c1_absolute_along(r1c1, axis) is expected


def test_formula_must_start_with_equal_sign():
    with pytest.raises(FormulaError):
        to_r1c1("SUM(A1)", 1, 1)
