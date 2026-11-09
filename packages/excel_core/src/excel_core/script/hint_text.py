"""Rà chữ trong thẻ yêu cầu và gợi ý: không ghi địa chỉ ô, không có số liệu không có trong bài.

- Địa chỉ ô: vị trí đã có overlay chỉ (cấp 3), ghi trong chữ dễ sai khi bài đổi bố cục (quyết định 8 GĐ2).
- Số liệu: T2.6 thấy AI bịa số. Chỉ xét số "đáng kể" (có phần thập phân hoặc từ 3 chữ số trở lên), vì số
  nhỏ như "2 số lẻ", "bấm 2 lần" là chữ hướng dẫn bình thường. Số đo trong `operation.sizes` của bước (lấy
  từ file đáp án) được ghi trong chữ của bước đó.
"""

import re
from collections.abc import Iterator, Mapping
from typing import Any

from excel_core.checks.values import FLOAT_EPSILON, excel_serial, number_from_text
from excel_core.snapshot import WorkbookSnapshot

_ADDRESS = re.compile(
    r"(?<![\w$])\$?([A-Z]{1,3})\$?([1-9][0-9]{0,6})(?::\$?[A-Z]{1,3}\$?[1-9][0-9]{0,6})?(?!\w)"
)
_KEY_PREFIX = re.compile(r"(phím|bấm|nhấn|ấn)\s*$", re.IGNORECASE)
_NUMBER = re.compile(r"(?<![\w.,])\d[\d.,]*\d|(?<![\w.,])\d(?![\w.,])")
NOT_ADDRESSES = frozenset({"A3", "A4", "A5", "B4", "B5"})  # khổ giấy
# Nhãn trên giao diện Excel có số, không phải số liệu bài ("Use 1000 Separator")
_UI_LABELS = re.compile(r"1000 separator|(excel|office)\s*\d{4}", re.IGNORECASE)
FUNCTION_KEYS = frozenset(f"F{i}" for i in range(1, 13))


def _texts(step: Mapping[str, Any]) -> Iterator[str]:
    yield step["task"]
    for hint in step["hints"]:
        yield hint["text"]
        yield from hint.get("actions", [])
        if "alternative" in hint:
            yield hint["alternative"]


def _addresses(text: str) -> list[str]:
    found = []
    for match in _ADDRESS.finditer(text):
        token = match.group(0)
        if token in NOT_ADDRESSES:
            continue
        if token in FUNCTION_KEYS and _KEY_PREFIX.search(text[: match.start()]):
            continue  # "bấm F4" là phím, không phải ô
        found.append(token)
    return found


def _significant_numbers(text: str) -> list[tuple[str, float]]:
    numbers = []
    for match in _NUMBER.finditer(_UI_LABELS.sub(" ", text)):
        token = match.group(0)
        digits = sum(ch.isdigit() for ch in token)
        if digits < 3 and not re.search(r"\d[.,]\d", token):
            continue
        value = number_from_text(token)
        if value is not None:
            numbers.append((token, value))
    return numbers


def _workbook_numbers(*snapshots: WorkbookSnapshot) -> list[float]:
    values = []
    for snapshot in snapshots:
        for sheet in snapshot.sheets.values():
            for cell in sheet.cells.values():
                if cell.value_kind == "number":
                    values.append(float(cell.value))  # type: ignore[arg-type]
                elif cell.value_kind == "date":
                    values.append(excel_serial(cell.value))  # type: ignore[arg-type]
    return values


def _number_in(value: float, pool: list[float]) -> bool:
    # Số trong chữ có thể là phần trăm của tỉ lệ trong ô (12,5% ↔ 0.125) hoặc số đã làm tròn
    candidates = (value, value / 100)
    return any(abs(v - p) <= max(0.005, FLOAT_EPSILON * abs(p)) for v in candidates for p in pool)


def hint_text_issues(
    script: Mapping[str, Any], starter: WorkbookSnapshot, solution: WorkbookSnapshot
) -> Iterator[dict[str, str]]:
    pool = _workbook_numbers(starter, solution)
    for step in script["steps"]:
        # Bước đổi kích thước theo quy trình: số đo trong `operation` lấy từ file đáp án, ghi trong chữ được
        sizes = [float(v) for v in step.get("operation", {}).get("sizes", {}).values()]
        step_pool = pool + sizes
        for text in _texts(step):
            for address in _addresses(text):
                yield {
                    "step_id": step["id"],
                    "text": address,
                    "issue": "có địa chỉ ô trong chữ (đã có overlay chỉ)",
                }
            for token, value in _significant_numbers(text):
                if not _number_in(value, step_pool):
                    yield {
                        "step_id": step["id"],
                        "text": token,
                        "issue": "số liệu không có trong file đề/đáp án",
                    }
