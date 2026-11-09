"""Khớp cột, dòng giữa file đề và file đáp án khi bài có chèn/xóa cột, dòng.

So theo địa chỉ ô thì xóa hai cột làm mọi ô bên phải "đổi" phông, căn lề, gộp ô (bài 06 thao tác với cột:
102 thay đổi, phần lớn là giả, AI không chia bước được). Nên trước khi so, khớp từng cột của đáp án với
một cột của đề theo nội dung (dãy con chung dài nhất, difflib), rồi khớp dòng nếu cột không dịch. Chỉ dịch
một trục là trường hợp bài tập hay gặp; chèn cột và dòng cùng lúc thì vẫn so theo địa chỉ.
"""

from collections.abc import Hashable, Mapping, Sequence
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from excel_core.address import cell_address
from excel_core.snapshot import SheetSnapshot

type Signature = tuple[Hashable, ...]


@dataclass(frozen=True)
class AxisMap:
    """Vị trí tương ứng trên một trục (cột hoặc dòng). Chỉ số đánh từ 1."""

    to_starter: Mapping[int, int] = field(default_factory=dict)  # đáp án → đề, chỉ các vị trí khớp được
    deleted: tuple[int, ...] = ()  # vị trí trong đề bị xóa
    inserted: tuple[int, ...] = ()  # vị trí trong đáp án được chèn

    @property
    def shifted(self) -> bool:
        return bool(self.deleted or self.inserted)

    def starter(self, index: int) -> int | None:
        """Vị trí trong đề ứng với vị trí `index` của đáp án; không có (chèn mới) thì None."""
        if not self.shifted:
            return index
        return self.to_starter.get(index)

    def solution(self, index: int) -> int | None:
        """Vị trí trong đáp án ứng với vị trí `index` của đề; bị xóa thì None."""
        if not self.shifted:
            return index
        return self._to_solution.get(index)

    @property
    def _to_solution(self) -> dict[int, int]:
        return {s: a for a, s in self.to_starter.items()}


IDENTITY = AxisMap()


def _empty(signature: Signature) -> bool:
    return all(item is None for item in signature)


def _anchors(before: Sequence[Signature], after: Sequence[Signature]) -> list[tuple[int, int]]:
    """Cặp (vị trí đề, vị trí đáp án) có nội dung giống hệt, theo thứ tự (dãy con chung dài nhất).

    Chỉ khớp cột/dòng có nội dung: cột trống giống nhau ở mọi nơi, khớp cả chúng thì thuật toán dễ chọn nhầm.
    """
    full_before = [i for i, sig in enumerate(before) if not _empty(sig)]
    full_after = [j for j, sig in enumerate(after) if not _empty(sig)]
    matcher = SequenceMatcher(
        None, [before[i] for i in full_before], [after[j] for j in full_after], autojunk=False
    )
    return [
        (full_before[block.a + k], full_after[block.b + k])
        for block in matcher.get_matching_blocks()
        for k in range(block.size)
    ]


def _is_permutation(
    before: Sequence[Signature], after: Sequence[Signature], anchors: list[tuple[int, int]]
) -> bool:
    """Cột/dòng có nội dung không khớp được mà hai bên cùng có: đổi chỗ (sắp xếp), không phải chèn/xóa."""
    matched_before = {i for i, _ in anchors}
    matched_after = {j for _, j in anchors}
    loose_before = {sig for i, sig in enumerate(before) if i not in matched_before and not _empty(sig)}
    loose_after = {sig for j, sig in enumerate(after) if j not in matched_after and not _empty(sig)}
    return bool(loose_before & loose_after)


def _pick(gap: list[int], count: int, signatures: Sequence[Signature]) -> list[int]:
    """Chọn `count` vị trí trong khoảng giữa hai mốc là chỗ bị xóa/chèn: ưu tiên cột/dòng trống."""
    ordered = sorted(gap, key=lambda i: (not _empty(signatures[i]), i))
    return sorted(ordered[:count])


def align_axis(before: Sequence[Signature], after: Sequence[Signature]) -> AxisMap:
    """Khớp hai dãy chữ ký (cột hoặc dòng). Không thấy dịch chuyển thật thì trả về IDENTITY.

    Mốc là các cột có nội dung khớp hệt nhau; độ lệch vị trí giữa hai mốc liền nhau tăng thì có chèn, giảm thì
    có xóa ở khoảng giữa. Cột/dòng trống thêm, bớt ở đuôi vùng đọc (vùng đang dùng khác nhau) không tính.
    """
    anchors = _anchors(before, after)
    moved = sum(1 for i, j in anchors if i != j)
    in_place = sum(1 for a, b in zip(before, after, strict=False) if a == b and not _empty(a))
    # Chỉ nhận dịch chuyển khi nó khớp được nhiều nội dung hơn so theo địa chỉ (giá trị mới tình cờ trùng giá
    # trị có sẵn ở chỗ khác thì không phải dịch cột)
    if not moved or len(anchors) <= in_place or _is_permutation(before, after, anchors):
        return IDENTITY
    to_starter: dict[int, int] = {}
    deleted: list[int] = []
    inserted: list[int] = []
    previous = (-1, -1)
    for i, j in anchors:
        gap_before = list(range(previous[0] + 1, i))
        gap_after = list(range(previous[1] + 1, j))
        removed = _pick(gap_before, max(0, len(gap_before) - len(gap_after)), before)
        added = _pick(gap_after, max(0, len(gap_after) - len(gap_before)), after)
        deleted += removed
        inserted += added
        kept_before = [x for x in gap_before if x not in removed]
        kept_after = [y for y in gap_after if y not in added]
        to_starter.update(zip(kept_after, kept_before, strict=True))
        to_starter[j] = i
        previous = (i, j)
    # Sau mốc cuối: khớp theo cùng độ lệch, phần thừa ở đuôi bỏ qua
    tail = zip(range(previous[1] + 1, len(after)), range(previous[0] + 1, len(before)), strict=False)
    to_starter.update(tail)
    if not deleted and not inserted:
        return IDENTITY
    return AxisMap(
        to_starter={j + 1: i + 1 for j, i in to_starter.items()},
        deleted=tuple(i + 1 for i in deleted),
        inserted=tuple(j + 1 for j in inserted),
    )


def _value(sheet: SheetSnapshot, col: int, row: int) -> Hashable:
    cell = sheet.cell(cell_address(col, row))
    return None if cell.is_empty else (cell.value_kind, repr(cell.value))


def align_sheets(
    before: SheetSnapshot, after: SheetSnapshot, cols: range, rows: range
) -> tuple[AxisMap, AxisMap]:
    """(khớp cột, khớp dòng) cho vùng so sánh `cols` × `rows`."""
    col_map = align_axis(
        [tuple(_value(before, c, r) for r in rows) for c in cols],
        [tuple(_value(after, c, r) for r in rows) for c in cols],
    )
    col_map = _offset(col_map, cols.start)
    if col_map.shifted:
        return col_map, IDENTITY
    row_map = align_axis(
        [tuple(_value(before, c, r) for c in cols) for r in rows],
        [tuple(_value(after, c, r) for c in cols) for r in rows],
    )
    return IDENTITY, _offset(row_map, rows.start)


def _offset(axis: AxisMap, start: int) -> AxisMap:
    """align_axis đánh số từ 1 trong vùng; đổi về số cột/dòng thật của trang tính."""
    if not axis.shifted or start == 1:
        return axis
    delta = start - 1
    return AxisMap(
        to_starter={a + delta: s + delta for a, s in axis.to_starter.items()},
        deleted=tuple(i + delta for i in axis.deleted),
        inserted=tuple(j + delta for j in axis.inserted),
    )
