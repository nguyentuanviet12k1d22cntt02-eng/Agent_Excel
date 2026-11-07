"""Phân tích mã định dạng số en-US thành ý nghĩa: loại, số chữ số thập phân, dấu nghìn.

Điều kiện `number_format` so theo ý nghĩa, không so chuỗi mã (danh-muc-dieu-kien.md mục 1): máy vi-VN và
en-US cho mã khác nhau, Comma Style mỗi máy một kiểu (`_(* #,##0.00_)...` hoặc `_-* #,##0.00_-...`).
"""

import re
from functools import lru_cache

from excel_core.snapshot.model import NumberCategory, NumberFormatInfo

SHORT_DATE = "short_date"
# Định dạng ngày dựng sẵn id 14: openpyxl đọc ra "mm-dd-yy", COM (LCID 1033) ra "m/d/yyyy" (T2.1)
_SHORT_DATE_CODES = frozenset({"mm-dd-yy", "m/d/yyyy", "m/d/yy", "mm/dd/yyyy", "mm/dd/yy"})
_CURRENCY_TEXT = frozenset({"$", "€", "£", "¥", "₫", "đ", "vnd", "vnđ", "usd"})

_QUOTED = re.compile(r'"([^"]*)"')
_BRACKET = re.compile(r"\[([^\]]*)\]")
_ESCAPED = re.compile(r"\\(.)")
_PAD_OR_FILL = re.compile(r"[_*](.)")


def _first_section(code: str) -> str:
    """Phần định dạng cho số dương: trước dấu ";" đầu tiên nằm ngoài nháy và ngoặc vuông."""
    depth_quote = False
    depth_bracket = False
    for i, char in enumerate(code):
        if char == '"':
            depth_quote = not depth_quote
        elif not depth_quote and char == "[":
            depth_bracket = True
        elif not depth_quote and char == "]":
            depth_bracket = False
        elif char == ";" and not depth_quote and not depth_bracket:
            return code[:i]
    return code


def _has_currency(section: str) -> bool:
    for text in _QUOTED.findall(section):
        if text.strip().lower() in _CURRENCY_TEXT:
            return True
    for text in _BRACKET.findall(section):
        if text.startswith("$") and len(text) > 1 and text[1] != "-":
            return True  # [$€-x], [$₫-42A]; còn [$-409] chỉ là mã vùng
    bare = _BRACKET.sub("", _QUOTED.sub("", section))
    return any(symbol in bare for symbol in ("$", "€", "£", "¥", "₫"))


def _strip_literals(section: str) -> tuple[str, set[str]]:
    """Bỏ chữ trong nháy, ký tự thoát, ký tự đệm; trả về phần còn lại và các thẻ trong ngoặc vuông."""
    brackets = {b.lower() for b in _BRACKET.findall(section)}
    text = _QUOTED.sub("", section)
    text = _BRACKET.sub("", text)
    text = _ESCAPED.sub("", text)
    text = _PAD_OR_FILL.sub("", text)
    return text, brackets


def _decimals(numeric: str) -> int:
    if "." not in numeric:
        return 0
    after = numeric.split(".", 1)[1]
    count = 0
    for char in after:
        if char in "0#?":
            count += 1
        elif char in "eE%":
            break
    return count


def _thousands(numeric: str) -> bool:
    integer = numeric.split(".", 1)[0]
    # Dấu phẩy nằm giữa hai ký tự chữ số mới là dấu nghìn; dấu phẩy ở cuối là chia cho 1.000
    return re.search(r"[0#?],+[0#?]", integer) is not None


def _date_time_category(text: str, brackets: set[str]) -> NumberCategory | None:
    lowered = text.lower()
    if any(b in ("h", "hh", "m", "mm", "s", "ss") for b in brackets):
        return "time"
    has_date = re.search(r"[yd]", lowered) is not None
    has_time = re.search(r"[hs]", lowered) is not None or "am/pm" in lowered or "a/p" in lowered
    if has_date:
        return "date"
    if has_time:
        return "time"
    if "m" in lowered and not re.search(r"[0#?]", lowered):
        return "date"  # chỉ có tháng, ví dụ "mmmm"
    return None


def normalize_date_pattern(code: str) -> str:
    """Mẫu ngày để so sánh: chữ thường, bỏ mã vùng; định dạng ngày dựng sẵn → "short_date"."""
    lowered = _BRACKET.sub("", code.lower()).strip()
    lowered = lowered.replace("\\", "").replace(";@", "")
    return SHORT_DATE if lowered in _SHORT_DATE_CODES else lowered


@lru_cache(maxsize=1024)
def parse_number_format(code: str | None) -> NumberFormatInfo:
    """Mã định dạng en-US → NumberFormatInfo. Mã rỗng hoặc None coi như General."""
    raw = (code or "General").strip() or "General"
    section = _first_section(raw)
    text, brackets = _strip_literals(section)
    stripped = text.strip()

    if stripped.lower() in ("general", ""):
        if not stripped and _QUOTED.search(section):
            return NumberFormatInfo(raw, "custom", None, False)
        return NumberFormatInfo(raw, "general", None, False)
    if stripped == "@":
        return NumberFormatInfo(raw, "text", None, False)

    date_or_time = _date_time_category(stripped, brackets)
    if date_or_time is not None:
        pattern = normalize_date_pattern(raw) if date_or_time == "date" else None
        return NumberFormatInfo(raw, date_or_time, None, False, pattern)

    has_digits = re.search(r"[0#?]", stripped) is not None
    if not has_digits:
        return NumberFormatInfo(raw, "custom", None, False)

    decimals = _decimals(stripped)
    thousands = _thousands(stripped)
    if re.search(r"[eE][+-]", stripped):
        category: NumberCategory = "scientific"
    elif "%" in stripped:
        category = "percent"
    elif "/" in stripped:
        category = "fraction"
    elif "*" in section and re.search(r"(?<!\\)\*", _QUOTED.sub("", section)):
        category = "accounting"  # ký tự lấp đầy "* " là dấu hiệu của định dạng kế toán
    elif _has_currency(section):
        category = "currency"
    else:
        category = "number"
    return NumberFormatInfo(raw, category, decimals, thousands)
