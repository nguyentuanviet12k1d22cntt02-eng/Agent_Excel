"""Phần chung của các điều kiện kiểm chứng (T4.4).

Mỗi loại điều kiện là một module trong `checks/` khai báo:
- `TYPE`: tên loại, trùng `type` trong lược đồ kịch bản;
- `CODES`: các mã lỗi có thể trả về (tầng 2 dùng để kiểm `feedback[].code`);
- `reads(check, sheet) -> list[Read]`: cần đọc gì, trên snapshot nào;
- `evaluate(check, ctx) -> CheckResult`.

Tham số điều kiện là dict JSON đã qua kiểm lược đồ (tầng 1), nên đọc thẳng theo khóa.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Literal

from excel_core.address import CellRange, parse_range
from excel_core.snapshot import (
    PropertyGroup,
    RangeRequest,
    SheetRequest,
    SheetSnapshot,
    WorkbookSnapshot,
)

type CheckSpec = Mapping[str, Any]
type Source = Literal["current", "starter", "solution"]


class CheckSpecError(ValueError):
    """Tham số điều kiện sai mà lược đồ không bắt được (ví dụ vùng kỳ vọng khác kích thước)."""


class CheckStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    NOT_EVALUABLE = "not_evaluable"  # không chấm được trong ngữ cảnh này (ví dụ in PDF khi chỉ có file)


@dataclass(frozen=True)
class CheckResult:
    status: CheckStatus
    code: str | None = None  # mã lỗi để chọn phản hồi (feedback[].code)
    cells: tuple[str, ...] = ()  # các ô không đạt ứng với mã lỗi này
    detail: str = ""  # giải thích cho giảng viên/nhật ký, không hiện cho học viên

    @property
    def passed(self) -> bool:
        return self.status == CheckStatus.PASSED

    @classmethod
    def ok(cls) -> CheckResult:
        return cls(CheckStatus.PASSED)

    @classmethod
    def fail(cls, code: str, cells: Iterable[str] = (), detail: str = "") -> CheckResult:
        return cls(CheckStatus.FAILED, code, tuple(cells), detail)

    @classmethod
    def not_evaluable(cls, detail: str) -> CheckResult:
        return cls(CheckStatus.NOT_EVALUABLE, detail=detail)


@dataclass(frozen=True)
class CheckContext:
    """Dữ liệu để chấm: bài đang làm, file đề, file đáp án (có thể chỉ là snapshot tham chiếu)."""

    current: WorkbookSnapshot
    default_sheet: str  # exercise.sheet của kịch bản
    starter: WorkbookSnapshot | None = None
    solution: WorkbookSnapshot | None = None
    printed_to_pdf: bool | None = None  # None: không có sự kiện trực tiếp (đang chấm trên file)
    learner_confirmed: bool | None = None  # học viên đã bấm "Đã xong" (observation_only)

    def sheet_name(self, check: CheckSpec) -> str:
        return check.get("sheet") or self.default_sheet

    def snapshot(self, source: Source) -> WorkbookSnapshot | None:
        return {"current": self.current, "starter": self.starter, "solution": self.solution}[source]

    def sheet(self, check: CheckSpec, source: Source = "current", name: str | None = None) -> SheetSnapshot:
        snapshot = self.snapshot(source)
        if snapshot is None:
            raise MissingReferenceError(source)
        return snapshot.sheet(name or self.sheet_name(check))


class MissingReferenceError(LookupError):
    """Điều kiện cần file đề/đáp án mà ngữ cảnh không có: trả về NOT_EVALUABLE."""

    def __init__(self, source: str) -> None:
        super().__init__(f"Ngữ cảnh chấm không có snapshot {source}")
        self.source = source


@dataclass(frozen=True)
class Read:
    """Một nhu cầu đọc của điều kiện: trên snapshot nào, đọc gì."""

    source: Source
    request: RangeRequest | SheetRequest


def cell_read(source: Source, sheet: str, rng: str | CellRange, *groups: PropertyGroup) -> Read:
    return Read(source, RangeRequest(sheet, str(rng), frozenset(groups)))


def sheet_read(source: Source, sheet: str, *groups: PropertyGroup) -> Read:
    return Read(source, SheetRequest(sheet, frozenset(groups)))


def check_range(check: CheckSpec) -> CellRange:
    return parse_range(check["range"])


@dataclass
class Failures:
    """Gom ô không đạt theo mã lỗi; khi trả kết quả chọn mã theo thứ tự ưu tiên của điều kiện."""

    priority: tuple[str, ...]
    by_code: dict[str, list[str]] = field(default_factory=dict)

    def add(self, code: str, cell: str = "") -> None:
        if code not in self.priority:
            raise ValueError(f"Mã lỗi {code!r} không khai báo trong thứ tự ưu tiên")
        cells = self.by_code.setdefault(code, [])
        if cell:
            cells.append(cell)

    def __bool__(self) -> bool:
        return bool(self.by_code)

    def result(self) -> CheckResult:
        if not self.by_code:
            return CheckResult.ok()
        code = next(c for c in self.priority if c in self.by_code)
        detail = "; ".join(
            f"{c}: {', '.join(self.by_code[c][:5]) or '-'}" for c in self.priority if c in self.by_code
        )
        return CheckResult.fail(code, self.by_code[code], detail)
