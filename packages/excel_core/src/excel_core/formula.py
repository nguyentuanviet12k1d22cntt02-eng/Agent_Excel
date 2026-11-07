"""Phân tích công thức Excel (cú pháp tiếng Anh): chuyển A1 → R1C1, tìm tên hàm, phép tính.

Hai bộ đọc đều tính `formula_r1c1` bằng `to_r1c1()` ở đây (không lấy `FormulaR1C1` của COM), để
`formula_consistent` và `formula_matches_r1c1` cho cùng kết quả trên file và trên Excel đang chạy.
"""

import re
from dataclasses import dataclass

from openpyxl.formula.tokenizer import Token, Tokenizer, TokenizerError

_CELL_REF = re.compile(r"^(\$?)([A-Za-z]{1,3})(\$?)([0-9]{1,7})$")
_COL_REF = re.compile(r"^(\$?)([A-Za-z]{1,3})$")
_ROW_REF = re.compile(r"^(\$?)([0-9]{1,7})$")
_FUNCTION_PREFIXES = ("_xlfn._xlws.", "_xlfn.", "_xlws.")
ARITHMETIC_OPERATORS = frozenset({"+", "-", "*", "/", "^"})
# Tham chiếu có cấu trúc kiểu Table1[Cột]: trong ngoặc vuông có chữ (R1C1 chỉ có số)
_STRUCTURED_REF = re.compile(r"\[[^\]\-0-9]")


class FormulaError(ValueError):
    """Công thức không phân tích được."""


@dataclass(frozen=True)
class FormulaParts:
    """Thành phần của một công thức đã phân tích."""

    functions: tuple[str, ...]  # tên hàm theo thứ tự xuất hiện, chữ hoa, bỏ tiền tố _xlfn.
    references: tuple[str, ...]  # tham chiếu ô/vùng như viết trong công thức
    infix_operators: tuple[str, ...]  # + - * / ^ & = < > ...


def _tokens(formula: str) -> list[Token]:
    if not formula.startswith("="):
        raise FormulaError(f"Công thức phải bắt đầu bằng '=': {formula!r}")
    try:
        return Tokenizer(formula).items
    except TokenizerError as exc:
        raise FormulaError(f"Không phân tích được công thức {formula!r}: {exc}") from exc


def function_name(token_value: str) -> str:
    """ "_xlfn.CONCAT(" → "CONCAT"."""
    name = token_value.rstrip("(").upper()
    for prefix in _FUNCTION_PREFIXES:
        if name.startswith(prefix.upper()):
            return name[len(prefix) :]
    return name


def parse_formula(formula: str) -> FormulaParts:
    """Tách tên hàm, tham chiếu và phép toán của công thức."""
    functions, references, operators = [], [], []
    for token in _tokens(formula):
        if token.type == Token.FUNC and token.subtype == Token.OPEN:
            functions.append(function_name(token.value))
        elif token.type == Token.OPERAND and token.subtype == Token.RANGE:
            references.append(token.value)
        elif token.type == Token.OP_IN:
            operators.append(token.value)
    return FormulaParts(tuple(functions), tuple(references), tuple(operators))


def _split_sheet(reference: str) -> tuple[str, str]:
    """ "'Bài 01'!$C$9" → ("'Bài 01'!", "$C$9")."""
    if "!" not in reference:
        return "", reference
    sheet, ref = reference.rsplit("!", 1)
    return sheet + "!", ref


def _r1c1_part(axis: str, absolute: bool, target: int, origin: int) -> str:
    if absolute:
        return f"{axis}{target}"
    offset = target - origin
    return axis if offset == 0 else f"{axis}[{offset}]"


def _column_number(letters: str) -> int:
    number = 0
    for char in letters.upper():
        number = number * 26 + ord(char) - ord("A") + 1
    return number


def _endpoint_to_r1c1(text: str, row: int, col: int) -> str | None:
    if match := _CELL_REF.match(text):
        col_abs, letters, row_abs, digits = match.groups()
        return _r1c1_part("R", bool(row_abs), int(digits), row) + _r1c1_part(
            "C", bool(col_abs), _column_number(letters), col
        )
    if match := _COL_REF.match(text):
        return _r1c1_part("C", bool(match.group(1)), _column_number(match.group(2)), col)
    if match := _ROW_REF.match(text):
        return _r1c1_part("R", bool(match.group(1)), int(match.group(2)), row)
    return None


def reference_to_r1c1(reference: str, row: int, col: int) -> str:
    """Một tham chiếu A1 (có thể có tên sheet) → R1C1 tính từ ô (row, col). Tên vùng, bảng giữ nguyên."""
    sheet, ref = _split_sheet(reference)
    endpoints = ref.split(":")
    converted = [_endpoint_to_r1c1(e, row, col) for e in endpoints]
    if len(endpoints) > 2 or any(c is None for c in converted):
        return reference
    if len(converted) == 2 and converted[0] == converted[1] and not _CELL_REF.match(endpoints[0]):
        converted = converted[:1]  # Excel viết cột A:A tại C5 là "C[-2]", không phải "C[-2]:C[-2]"
    return sheet + ":".join(c for c in converted if c is not None)


def _keep_space(previous: Token | None, following: Token | None) -> bool:
    """Khoảng trắng giữa hai vùng là phép giao, phải giữ; còn lại bỏ."""
    if previous is None or following is None:
        return False
    left = (previous.type == Token.OPERAND and previous.subtype == Token.RANGE) or (
        previous.type == Token.FUNC and previous.subtype == Token.CLOSE
    )
    right = (following.type == Token.OPERAND and following.subtype == Token.RANGE) or (
        following.type == Token.FUNC and following.subtype == Token.OPEN
    )
    return left and right


def _rebuild(formula: str, row: int | None, col: int | None) -> str:
    tokens = _tokens(formula)
    parts = []
    for i, token in enumerate(tokens):
        if token.type == Token.WSPACE:
            previous = tokens[i - 1] if i > 0 else None
            following = tokens[i + 1] if i + 1 < len(tokens) else None
            if _keep_space(previous, following):
                parts.append(" ")
            continue
        if token.type == Token.FUNC and token.subtype == Token.OPEN:
            parts.append(function_name(token.value) + "(")
        elif token.type == Token.OPERAND and token.subtype == Token.RANGE:
            sheet, ref = _split_sheet(token.value)
            ref = ref if _STRUCTURED_REF.search(ref) else ref.upper()
            if row is not None and col is not None:
                parts.append(reference_to_r1c1(sheet + ref, row, col))
            else:
                parts.append(sheet + ref)
        elif token.type == Token.OPERAND and token.subtype in (Token.LOGICAL, Token.ERROR):
            parts.append(token.value.upper())
        else:
            parts.append(token.value)
    return "=" + "".join(parts)


def normalize_formula(formula: str) -> str:
    """Bỏ khoảng trắng thừa, chữ hoa tên hàm và địa chỉ, bỏ tiền tố _xlfn. (chuỗi trong nháy giữ nguyên)."""
    return _rebuild(formula, None, None)


def to_r1c1(formula: str, row: int, col: int) -> str:
    """Công thức A1 tại ô (row, col) → công thức R1C1 đã chuẩn hóa.

    Ví dụ: "=SUM(C9:E9)" tại F9 → "=SUM(RC[-3]:RC[-1])"; "=$C$9" → "=R9C3".
    """
    return _rebuild(formula, row, col)


def normalize_r1c1(formula: str) -> str:
    """Chuẩn hóa công thức R1C1 viết tay (trong kịch bản) để so với `to_r1c1()`."""
    return normalize_formula(formula)


def is_r1c1_absolute_along(r1c1: str, axis: str) -> bool:
    """Mọi tham chiếu trong công thức R1C1 đều cố định theo trục `axis` ("R" hoặc "C")?

    Dùng để nhận ra lỗi sao chép công thức có địa chỉ tuyệt đối: sao chép xuống mà mọi tham chiếu cố định
    dòng thì mọi ô cho cùng một kết quả. Công thức không có tham chiếu ô nào thì trả về False.
    """
    pattern = re.compile(rf"{axis}(\[-?[0-9]+\]|[0-9]+)?")
    found = False
    for reference in parse_formula(r1c1).references:
        _, ref = _split_sheet(reference)
        for endpoint in ref.split(":"):
            match = pattern.search(endpoint)
            if not match:
                continue
            found = True
            if not (match.group(1) or "").isdigit():
                return False
    return found
