"""row_col_hidden, row_col_size, layout_matches, sheet_exists."""

from excel_core.checks import CheckStatus


# ---------------------------------------------------------------- row_col_hidden
def test_row_col_hidden_rows(kit):
    check = {"type": "row_col_hidden", "rows": "5:7", "hidden": True}
    assert kit.run(check, kit.book(kit.sheet(hidden_rows=frozenset({5, 6, 7})))).passed
    result = kit.run(check, kit.book(kit.sheet(hidden_rows=frozenset({5, 6}))))
    assert (result.code, result.cells) == ("wrong_visibility", ("7",))


def test_row_col_hidden_cols_shown_again(kit):
    check = {"type": "row_col_hidden", "cols": "C:D", "hidden": False}
    assert kit.run(check, kit.book(kit.sheet())).passed
    assert kit.run(check, kit.book(kit.sheet(hidden_cols=frozenset({"D"})))).cells == ("D",)


# ---------------------------------------------------------------- row_col_size
def test_row_col_size_equals(kit):
    check = {"type": "row_col_size", "rows": "9", "equals": 30}
    assert kit.run(check, kit.book(kit.sheet(row_heights={9: 30.2}))).passed
    assert kit.run(check, kit.book(kit.sheet(row_heights={9: 15.0}))).code == "wrong_size"


def test_row_col_size_same_as(kit):
    check = {"type": "row_col_size", "cols": "C:D", "same_as": "B"}
    current = kit.book(kit.sheet(col_widths={"B": 20.0, "C": 20.0, "D": 12.0}))
    assert kit.run(check, current).cells == ("D",)


def test_row_col_size_autofit_compares_with_solution(kit):
    check = {"type": "row_col_size", "cols": "D", "autofit": True}
    solution = kit.book(kit.sheet(col_widths={"D": 14.29}))
    assert kit.run(check, kit.book(kit.sheet(col_widths={"D": 14.0})), solution=solution).passed
    assert kit.run(check, kit.book(kit.sheet(col_widths={"D": 8.43})), solution=solution).code == "wrong_size"


# ---------------------------------------------------------------- layout_matches
def table(kit, rows: list[tuple[str, float]]):
    cells = {"B5": kit.text("Mã hàng"), "C5": kit.text("Số lượng")}
    for i, (code, qty) in enumerate(rows, start=6):
        cells[f"B{i}"] = kit.text(code)
        cells[f"C{i}"] = kit.number(qty)
    return kit.book(cells)


def test_layout_matches(kit):
    check = {"type": "layout_matches", "range": "B5:C8", "key_column": "Mã hàng"}
    solution = table(kit, [("A1", 10), ("A2", 20), ("A3", 30)])
    assert kit.run(check, table(kit, [("A1", 10), ("A2", 20), ("A3", 30)]), solution=solution).passed
    result = kit.run(check, table(kit, [("A1", 10), ("A3", 30), ("A2", 20)]), solution=solution)
    assert (result.code, result.cells) == ("wrong_layout", ("B7", "B8"))


def test_layout_matches_unknown_key_column_is_script_error(kit):
    check = {"type": "layout_matches", "range": "B5:C8", "key_column": "Không có"}
    rows = [("A1", 10)]
    result = kit.run(check, table(kit, rows), solution=table(kit, rows))
    assert result.status == CheckStatus.NOT_EVALUABLE


# ---------------------------------------------------------------- sheet_exists
def test_sheet_exists(kit):
    check = {"type": "sheet_exists", "name_pattern": "tổng hợp.*"}
    assert kit.run(check, kit.book(names=("S", "Tổng hợp 2026"))).passed
    assert kit.run(check, kit.book(names=("S", "Sheet2"))).code == "missing_sheet"
