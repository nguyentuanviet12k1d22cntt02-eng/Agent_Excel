"""Chuỗi thao tác dẫn từng bước trên Excel (`step.guide`): chọn đúng cột/dòng → bấm nút → chọn mục trong menu.

Chỉ là logic: luồng giám sát đưa vào vùng đang chọn và mục nào đang hiện trên màn hình, ra chỗ đang dẫn. Chỗ
đang dẫn được tính lại mỗi lần nên tự quay lui khi học viên làm lệch: bỏ chọn vùng (hay chọn sai cột) thì về
bước chọn, đóng menu hay bấm ra ngoài thì về nút mở menu.
"""

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from excel_core.address import AddressError, column_index, column_letter

_AREA = re.compile(r"^([A-Z]{1,3})?([1-9][0-9]*)?(?::([A-Z]{1,3})?([1-9][0-9]*)?)?$")
WHOLE = "*"  # vùng chọn cả dòng khi đang xét cột (hoặc cả cột khi xét dòng): phủ mọi cột/dòng


@dataclass(frozen=True)
class GuideItem:
    action: str  # select | click
    text: str
    axis: str | None = None  # select: cols | rows
    lines: tuple[str, ...] = ()
    control: str | None = None  # click: idMso nút Ribbon hoặc mã mục menu
    tab: str | None = None


@dataclass(frozen=True)
class Guide:
    items: tuple[GuideItem, ...]
    sheet: str


def parse_guide(step: Mapping[str, Any] | None) -> tuple[GuideItem, ...]:
    if step is None:
        return ()
    return tuple(
        GuideItem(
            action=item["action"],
            text=item["text"],
            axis=item.get("axis"),
            lines=tuple(item.get("lines", ())),
            control=item.get("control"),
            tab=item.get("tab"),
        )
        for item in step.get("guide", ())
    )


def selected_lines(address: str, axis: str) -> frozenset[str]:
    """Cột (chữ) hoặc dòng (số dạng chữ) mà vùng chọn phủ: "$D:$F", "$D:$E,$H:$H", "$D$5:$F$9", "$5:$7"."""
    lines: set[str] = set()
    for area in re.split(r"[,;]", address.replace("$", "")):
        match = _AREA.match(area.strip())
        if not area.strip() or not match:
            continue
        col1, row1, col2, row2 = match.groups()
        try:
            if axis == "cols":
                if col1 is None:
                    lines.add(WHOLE)
                    continue
                first, last = sorted((column_index(col1), column_index(col2 or col1)))
                lines |= {column_letter(i) for i in range(first, last + 1)}
            else:
                if row1 is None:
                    lines.add(WHOLE)
                    continue
                first, last = sorted((int(row1), int(row2 or row1)))
                lines |= {str(i) for i in range(first, last + 1)}
        except AddressError:
            continue
    return frozenset(lines)


def selection_matches(item: GuideItem, address: str | None) -> bool:
    """Vùng chọn phủ ĐÚNG các cột/dòng của bước chọn (thừa một cột là lệnh áp cả cột đó: sai)."""
    if address is None or item.axis is None:
        return False
    return selected_lines(address, item.axis) == set(item.lines)


def position(items: Sequence[GuideItem], selection_ok: bool, shown: Callable[[int], bool]) -> int:
    """Chỗ đang dẫn. Chưa chọn đúng vùng: bước chọn. Đã chọn: nút/mục menu sâu nhất đang hiện trên màn hình
    (mục trong menu chỉ hiện khi menu cha đang mở). `shown(i)` hỏi mục i có đang hiện không."""
    if items and items[0].action == "select" and not selection_ok:
        return 0
    clicks = [i for i, item in enumerate(items) if item.action == "click"]
    for index in reversed(clicks):
        if shown(index):
            return index
    return clicks[0] if clicks else 0
