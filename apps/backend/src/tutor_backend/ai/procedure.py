"""Kịch bản theo quy trình trong đề (T5.9): đề ghi từng bước thao tác cấu trúc (thường trong khối chữ của hình
vẽ, bài 06: "Hiển thị cột E → Chèn cột sau G → Ẩn cột H → … → Xóa các cột D, E, H").

So file đề với file đáp án chỉ thấy kết quả cuối (thao tác triệt tiêu nhau mất dấu), nên:
1. AI chép quy trình thành danh sách thao tác theo lược đồ đóng (5 loại, theo dòng/cột).
2. Code làm lần lượt các thao tác trên snapshot file đề (excel_core.procedure). Làm hết mà bố cục, dòng/cột
   ẩn chưa khớp đáp án thì gửi lại AI sửa: đây là chốt chặn AI đọc sai đề.
3. Mỗi thao tác thành một mục thay đổi p1, p2… với điều kiện kiểm theo trạng thái NGAY SAU thao tác; phần
   khác biệt còn lại (định dạng, nhập liệu…) phân tích như cũ trên trạng thái cuối → đáp án.
"""

import dataclasses
import json
import logging
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from excel_core.address import CellRange, cell_address, column_index
from excel_core.diff import LAYOUT_KINDS, ChangeKind, diff_workbooks
from excel_core.procedure import ACTIONS, Operation, ProcedureError, resolve_sizes, simulate
from excel_core.snapshot import SheetSnapshot, WorkbookSnapshot
from tutor_backend.ai.exercise_analysis import (
    KIND_NAMES,
    ChangeItem,
    ExerciseAnalysis,
    _used,
    analyze_snapshots,
)
from tutor_backend.ai.llm_client import LLMClient, LLMOutputError
from tutor_backend.ai.prompts import render

logger = logging.getLogger(__name__)

type Check = dict[str, Any]

SCHEMA_NAME = "tutor_procedure"
MAX_OPERATIONS = 30
MAX_ANCHORS = 10  # số cột (dòng) mốc kiểm sau khi chèn/xóa
MAX_PREVIOUS_CHARS = 6000
STRUCTURAL = frozenset(
    k.value
    for k in (
        *LAYOUT_KINDS,
        ChangeKind.COL_HIDDEN,
        ChangeKind.ROW_HIDDEN,
        ChangeKind.COL_WIDTH,
        ChangeKind.ROW_HEIGHT,
    )
)
_HIDDEN_KINDS = frozenset({ChangeKind.COL_HIDDEN, ChangeKind.ROW_HIDDEN})


@dataclass(frozen=True)
class ProcedureStep:
    operation: Operation
    instruction: str  # nguyên câu yêu cầu trong đề


@dataclass
class ProcedureOutcome:
    analysis: ExerciseAnalysis | None  # None: đề không có quy trình hoặc chưa dựng được
    issues: list[str] = field(default_factory=list)
    operations: int = 0
    attempts: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    llm_ms: int = 0


# ---------------------------------------------------------------- AI chép quy trình
def wants_procedure(analysis: ExerciseAnalysis, prompt_text: str | None) -> bool:
    """Bài có thay đổi cấu trúc (ẩn/hiện, chèn/xóa, kích thước) và có đề bài để đọc quy trình."""
    structural = any(c.sheet == analysis.sheet and c.kind in STRUCTURAL for c in analysis.changes)
    return structural and bool(analysis.workbook_text or (prompt_text or "").strip())


def procedure_schema() -> dict[str, Any]:
    item = {
        "type": "object",
        "additionalProperties": False,
        "required": ["instruction", "action", "axis", "lines", "side", "count", "size"],
        "properties": {
            "instruction": {"type": "string", "description": "Nguyên câu yêu cầu trong đề"},
            "action": {"type": "string", "enum": list(ACTIONS)},
            "axis": {"type": "string", "enum": ["cols", "rows"]},
            "lines": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Cột (chữ in hoa) hoặc dòng (số), đúng như đề ghi",
            },
            "side": {
                "type": "string",
                "enum": ["before", "after", "none"],
                "description": "insert: chèn trước hay sau dòng/cột đã ghi; thao tác khác: none",
            },
            "count": {"type": ["integer", "null"], "description": "insert: số dòng/cột chèn"},
            "size": {"type": ["number", "null"], "description": "resize: số đo đề ghi rõ, không có thì null"},
        },
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["operations"],
        "properties": {"operations": {"type": "array", "items": item}},
    }


def parse_procedure(data: Any) -> list[ProcedureStep]:
    """Danh sách thao tác AI trả về → thao tác của excel_core. Sai thì ném ProcedureError (gửi lại AI sửa)."""
    items = data.get("operations") if isinstance(data, dict) else None
    if not isinstance(items, list):
        raise ProcedureError("trả lời không có danh sách operations")
    if len(items) > MAX_OPERATIONS:
        raise ProcedureError(f"quá nhiều thao tác ({len(items)}), tối đa {MAX_OPERATIONS}")
    steps = []
    for number, item in enumerate(items, start=1):
        axis, action = item.get("axis"), item.get("action")
        names = [str(n).strip().upper() for n in item.get("lines", []) if str(n).strip()]
        try:
            lines = [column_index(n) if axis == "cols" else int(n) for n in names]
            if action == "insert":
                if len(lines) != 1:
                    raise ProcedureError("chèn: ghi đúng một cột/dòng mốc")
                at = lines[0] + 1 if item.get("side") == "after" else lines[0]
                op = Operation("insert", axis, (at,), int(item.get("count") or 1))
            else:
                size = item.get("size")
                sizes = (
                    {line: float(size) for line in lines} if action == "resize" and size is not None else {}
                )
                op = Operation(action, axis, tuple(sorted(set(lines))), 1, sizes)
        except (ProcedureError, ValueError) as exc:
            raise ProcedureError(f"thao tác {number} ({item.get('instruction', '')}): {exc}") from exc
        steps.append(ProcedureStep(op, " ".join(str(item.get("instruction", "")).split())))
    return steps


def run_procedure(
    analysis: ExerciseAnalysis, steps: Sequence[ProcedureStep]
) -> tuple[list[ProcedureStep], list[WorkbookSnapshot]]:
    """Làm lần lượt các thao tác trên file đề; làm hết phải ra bố cục, dòng/cột ẩn như đáp án."""
    sheet = analysis.sheet
    operations = resolve_sizes([s.operation for s in steps], analysis.solution.sheet(sheet))
    states = simulate(analysis.starter, sheet, operations)
    structural = LAYOUT_KINDS | _HIDDEN_KINDS
    left = [
        c
        for c in diff_workbooks(states[-1], analysis.solution).changes
        if c.sheet == sheet and c.kind in structural
    ]
    if left:
        described = "; ".join(f"{c.after} {c.range}" for c in left[:6])
        raise ProcedureError(f"làm hết các thao tác mà bảng vẫn khác đáp án (còn phải {described})")
    resolved = [dataclasses.replace(s, operation=op) for s, op in zip(steps, operations, strict=True)]
    return resolved, states


def _structural_lines(analysis: ExerciseAnalysis) -> str:
    lines = [
        f"- {KIND_NAMES.get(c.kind, c.kind)}: {c.label} ({c.description})"
        for c in analysis.changes
        if c.sheet == analysis.sheet and c.kind in STRUCTURAL
    ]
    return "\n".join(lines) or "(không có)"


def extract_procedure(
    analysis: ExerciseAnalysis,
    title: str,
    prompt_text: str | None,
    instructions: str | None,
    llm: LLMClient,
    max_attempts: int,
) -> ProcedureOutcome:
    """Nhờ AI chép quy trình, kiểm bằng cách làm thử; sai thì gửi lại kèm lỗi, tối đa `max_attempts` lần."""
    schema = procedure_schema()
    system = render("extract_procedure_system")
    request = render(
        "extract_procedure_user",
        title=title,
        sheet=analysis.sheet,
        prompt_text=prompt_text or "(không có, xem chữ trong file đề)",
        workbook_text="\n".join(analysis.workbook_text) or "(không có)",
        instructions=instructions or "(không có)",
        changes=_structural_lines(analysis),
    )
    user, outcome = request, ProcedureOutcome(None)
    for attempt in range(1, max_attempts + 1):
        outcome.attempts = attempt
        try:
            response = llm.complete_json(system, user, schema, SCHEMA_NAME)
        except LLMOutputError as exc:
            outcome.prompt_tokens += exc.prompt_tokens
            outcome.completion_tokens += exc.completion_tokens
            outcome.llm_ms += exc.duration_ms
            outcome.issues = [str(exc)]
            user = render(
                "repair_procedure_user",
                previous="(không dùng được)",
                issues=f"- {exc}",
                original_request=request,
            )
            continue
        outcome.prompt_tokens += response.prompt_tokens
        outcome.completion_tokens += response.completion_tokens
        outcome.llm_ms += response.duration_ms
        try:
            steps = parse_procedure(response.data)
            if not steps:
                outcome.issues = []
                return outcome
            steps, states = run_procedure(analysis, steps)
        except ProcedureError as exc:
            logger.info("Quy trình theo đề, lần %d: %s", attempt, exc)
            outcome.issues = [str(exc)]
            previous = json.dumps(response.data, ensure_ascii=False)[:MAX_PREVIOUS_CHARS]
            user = render(
                "repair_procedure_user", previous=previous, issues=f"- {exc}", original_request=request
            )
            continue
        outcome.analysis = with_procedure(analysis, steps, states)
        outcome.issues, outcome.operations = [], len(steps)
        return outcome
    return outcome


# ---------------------------------------------------------------- mục thay đổi p1, p2…
def _blocks(lines: Sequence[int]) -> list[tuple[int, int]]:
    blocks: list[tuple[int, int]] = []
    for line in sorted(lines):
        if blocks and blocks[-1][1] == line - 1:
            blocks[-1] = (blocks[-1][0], line)
        else:
            blocks.append((line, line))
    return blocks


def _name(op: Operation, first: int, last: int, sep: str = "–") -> str:
    return op.name(first) if first == last else f"{op.name(first)}{sep}{op.name(last)}"


def _names(op: Operation, lines: Sequence[int]) -> str:
    return ", ".join(op.name(n) for n in sorted(lines))


def _box(sheet: SheetSnapshot, op: Operation, first: int, last: int) -> CellRange:
    used = _used(sheet)
    if op.is_col:
        return CellRange(first, used.min_row, last, used.max_row)
    return CellRange(used.min_col, first, used.max_col, last)


def _targets(op: Operation, before: SheetSnapshot) -> list[CellRange]:
    """Vùng khoanh trên bố cục lúc làm bước: hiện thì khoanh hai cột (dòng) kẹp chỗ ẩn, chèn thì khoanh cột
    (dòng) nằm ở chỗ chèn (chọn nó rồi Insert, cột mới chèn vào trước nó)."""
    if op.action == "insert":
        return [_box(before, op, op.lines[0], op.lines[0])]
    blocks = _blocks(op.lines)
    if op.action == "unhide":
        blocks = [(max(first - 1, 1), last + 1) for first, last in blocks]
    return [_box(before, op, first, last) for first, last in blocks]


def _value_key(value: Any) -> str:
    return " ".join(str(value).split()).casefold()


def _anchor(sheet: SheetSnapshot, op: Operation, line: int, counts: Counter[str]) -> tuple[str, Any] | None:
    """Ô mốc của một cột (dòng): ưu tiên chữ không trùng chỗ khác trên trang tính, rồi giá trị không trùng."""
    used = _used(sheet)
    span = used.rows() if op.is_col else used.cols()
    found = []
    for other in span:
        address = cell_address(line, other) if op.is_col else cell_address(other, line)
        cell = sheet.cell(address)
        if isinstance(cell.value, str | int | float) and str(cell.value).strip():
            found.append((address, cell))
    for wanted in (
        lambda c: c.value_kind == "text" and counts[_value_key(c.value)] == 1,
        lambda c: counts[_value_key(c.value)] == 1,
    ):
        pick = next(((a, c.value) for a, c in found if wanted(c)), None)
        if pick:
            return pick
    return (found[0][0], found[0][1].value) if found else None


def _anchor_checks(op: Operation, after: SheetSnapshot, verb: str) -> list[Check]:
    """Chèn/xóa: các cột (dòng) từ ngay trước chỗ thay đổi trở đi phải có ô mốc đúng như trạng thái mong đợi.

    Kiểm cả cột ngay trước chỗ chèn: chèn nhầm chỗ (trước G thay vì sau G) thì các cột phía sau vẫn dời y hệt.
    """
    used = _used(after)
    start = op.lines[0]
    inserted = range(start, start + op.count) if op.action == "insert" else range(0)
    last = used.max_col if op.is_col else used.max_row
    counts = Counter(_value_key(c.value) for c in after.cells.values() if c.value not in (None, ""))
    checks: list[Check] = []
    for line in range(max(start - 1, 1), last + 1):
        if line in inserted:
            continue
        anchor = _anchor(after, op, line, counts)
        if anchor is None:
            continue
        address, value = anchor
        text = " ".join(str(value).split())
        short = text if len(text) <= 30 else text[:29] + "…"
        checks.append(
            {
                "type": "value_equals",
                "range": address,
                "expected": {"from": "literal", "value": value},
                "description": f"“{short}” nằm đúng chỗ sau khi {verb} ({address}).",
            }
        )
        if len(checks) >= MAX_ANCHORS:
            break
    return checks


def _checks(op: Operation, after: SheetSnapshot) -> list[Check]:
    unit = "Cột" if op.is_col else "Dòng"
    key = op.axis
    if op.action in ("hide", "unhide"):
        hidden = op.action == "hide"
        return [
            {
                "type": "row_col_hidden",
                key: _name(op, first, last, ":"),
                "hidden": hidden,
                "description": f"{unit} {_name(op, first, last)} đang {'ẩn' if hidden else 'hiện'}.",
            }
            for first, last in _blocks(op.lines)
        ]
    if op.action == "resize":
        what = "rộng" if op.is_col else "cao"
        return [
            {
                "type": "row_col_size",
                key: op.name(line),
                "equals": round(op.sizes[line], 2),
                "description": f"{unit} {op.name(line)} {what} {_number(op.sizes[line])} như mẫu.",
            }
            for line in op.lines
        ]
    verb = "chèn" if op.action == "insert" else "xóa"
    return _anchor_checks(op, after, verb)


def _kind(op: Operation) -> str:
    """Loại thay đổi như diff (để tra tên, nhóm kỹ năng): col_hidden, col_inserted, col_width…"""
    axis = "col" if op.is_col else "row"
    if op.action == "resize":
        return "col_width" if op.is_col else "row_height"
    suffix = {"hide": "hidden", "unhide": "hidden", "insert": "inserted", "delete": "deleted"}[op.action]
    return f"{axis}_{suffix}"


# Nút Ribbon (idMso, thẻ Home) rồi mục trong menu thả xuống (mã theo idMso, Desktop tra tên hiển thị)
_CLICKS = {
    ("hide", True): ("FormatCellsMenu", "HideUnhideMenu", "ColumnsHide"),
    ("hide", False): ("FormatCellsMenu", "HideUnhideMenu", "RowsHide"),
    ("unhide", True): ("FormatCellsMenu", "HideUnhideMenu", "ColumnsUnhide"),
    ("unhide", False): ("FormatCellsMenu", "HideUnhideMenu", "RowsUnhide"),
    ("resize", True): ("FormatCellsMenu", "ColumnWidth"),
    ("resize", False): ("FormatCellsMenu", "RowHeight"),
    ("insert", True): ("InsertCellstMenu_Dropdown", "SheetColumnsInsert"),
    ("insert", False): ("InsertCellstMenu_Dropdown", "SheetRowsInsert"),
    ("delete", True): ("TableDeleteRowsAndColumnsMenu_Dropdown", "SheetColumnsDelete"),
    ("delete", False): ("TableDeleteRowsAndColumnsMenu_Dropdown", "SheetRowsDelete"),
}
_CLICK_TEXTS = {
    "FormatCellsMenu": "Bấm nút Format (thẻ Home, nhóm Cells)",
    "HideUnhideMenu": "Trỏ vào Hide & Unhide",
    "ColumnsHide": "Chọn Hide Columns",
    "ColumnsUnhide": "Chọn Unhide Columns",
    "RowsHide": "Chọn Hide Rows",
    "RowsUnhide": "Chọn Unhide Rows",
    "ColumnWidth": "Chọn Column Width…",
    "RowHeight": "Chọn Row Height…",
    "InsertCellstMenu_Dropdown": "Bấm mũi tên ▾ của nút Insert (thẻ Home)",
    "SheetColumnsInsert": "Chọn Insert Sheet Columns",
    "SheetRowsInsert": "Chọn Insert Sheet Rows",
    "TableDeleteRowsAndColumnsMenu_Dropdown": "Bấm mũi tên ▾ của nút Delete (thẻ Home)",
    "SheetColumnsDelete": "Chọn Delete Sheet Columns",
    "SheetRowsDelete": "Chọn Delete Sheet Rows",
}
TOP_LEVEL_TAB = "TabHome"


def _select_text(op: Operation, lines: list[int]) -> str:
    unit = "cột" if op.is_col else "dòng"
    blocks = _blocks(lines)
    parts = [f"{unit} {op.name(a)}" if a == b else f"{unit} {op.name(a)} → {op.name(b)}" for a, b in blocks]
    if len(parts) > 1:
        return f"Chọn tiêu đề {parts[0]}, giữ Ctrl rồi chọn thêm " + ", ".join(parts[1:])
    verb = "Bấm" if blocks[0][0] == blocks[0][1] else "Kéo chọn"
    return f"{verb} tiêu đề {parts[0]}"


def guide(op: Operation, before: SheetSnapshot) -> tuple[dict[str, Any], ...]:
    """Chuỗi thao tác dẫn từng bước: chọn đúng cột/dòng (qua tiêu đề) rồi lần lượt nút và mục trong menu."""
    unit = "cột" if op.is_col else "dòng"
    if op.action == "unhide":
        lines = sorted({n for a, b in _blocks(op.lines) for n in range(max(a - 1, 1), b + 2)})
        text = f"{_select_text(op, lines)} (bao cả {unit} {_names(op, op.lines)} đang ẩn, không giữ Ctrl)"
    elif op.action == "insert":
        lines = list(range(op.lines[0], op.lines[0] + op.count))
        text = f"{_select_text(op, lines)} ({unit} mới sẽ chèn vào trước)"
    else:
        lines = list(op.lines)
        text = _select_text(op, lines)
    items: list[dict[str, Any]] = [
        {"action": "select", "axis": op.axis, "lines": [op.name(n) for n in lines], "text": text}
    ]
    clicks = _CLICKS[(op.action, op.is_col)]
    for number, control in enumerate(clicks):
        item: dict[str, Any] = {"action": "click", "control": control, "text": _CLICK_TEXTS[control]}
        if number == 0:
            item["tab"] = TOP_LEVEL_TAB
        items.append(item)
    if op.action == "resize":
        values = {_number(op.sizes[n]) for n in op.lines}
        size = (
            values.pop()
            if len(values) == 1
            else "; ".join(f"{op.name(n)}: {_number(op.sizes[n])}" for n in op.lines)
        )
        items[-1]["text"] += f", nhập {size} rồi bấm OK"
    return tuple(items)


def _number(value: float) -> str:
    return f"{value:g}".replace(".", ",")


def _describe(op: Operation, before: SheetSnapshot) -> tuple[str, str]:
    """(việc phải làm, nhãn vùng khoanh) cho AI viết lời; không có số liệu ngoài số đo của thao tác."""
    unit = "cột" if op.is_col else "dòng"
    names = _names(op, op.lines)
    if op.action == "hide":
        return f"ẩn {unit} {names}", f"{unit} {names}"
    if op.action == "unhide":
        blocks = [(max(first - 1, 1), last + 1) for first, last in _blocks(op.lines)]
        drags = "; ".join(f"từ {unit} {op.name(a)} sang {unit} {op.name(b)}" for a, b in blocks)
        sides = ", ".join(_name(op, a, b) for a, b in blocks)
        return (
            f"hiện {unit} {names} đang ẩn: KÉO chọn liền {drags} (vùng chọn phải bao cả {unit} đang ẩn; "
            f"giữ Ctrl bấm từng {unit} thì không bao được, Unhide không có tác dụng) rồi Unhide",
            f"{unit} {sides} (kẹp {unit} {names} đang ẩn)",
        )
    if op.action == "insert":
        at = op.lines[0]
        where = f"trước {unit} {op.name(at)}" + (f" (tức là sau {unit} {op.name(at - 1)})" if at > 1 else "")
        return f"chèn {op.count} {unit} trống {where}", f"{unit} {op.name(at)} (chèn vào trước {unit} này)"
    if op.action == "delete":
        note = " (không liền nhau: giữ Ctrl khi chọn từng nhóm)" if len(_blocks(op.lines)) > 1 else ""
        return f"xóa {unit} {names}{note}", f"{unit} {names}"
    what = "độ rộng" if op.is_col else "chiều cao"
    sizes = ", ".join(f"{op.name(n)} = {_number(op.sizes[n])}" for n in op.lines)
    return f"đổi {what} {unit} {names} như mẫu ({what} mong đợi: {sizes})", f"{unit} {names}"


def procedure_items(
    analysis: ExerciseAnalysis, steps: Sequence[ProcedureStep], states: Sequence[WorkbookSnapshot]
) -> list[ChangeItem]:
    sheet = analysis.sheet
    items, before = [], analysis.starter.sheet(sheet)
    for number, (step, state) in enumerate(zip(steps, states, strict=True), start=1):
        op, after = step.operation, state.sheet(sheet)
        description, label = _describe(op, before)
        hidden_now = before.hidden_cols if op.is_col else before.hidden_rows
        hidden = [op.name(n) for n in op.lines if (op.name(n) if op.is_col else n) in hidden_now]
        context = f"bước {number} của quy trình trong đề: “{step.instruction}”"
        if op.action in ("insert", "delete"):
            verb = "chèn" if op.action == "insert" else "xóa"
            context += (
                f"; điều kiện kiểm: tiêu đề các cột (dòng) nằm đúng chỗ sau khi {verb}, wrong_value/empty "
                f"nghĩa là chưa {verb} hoặc {verb} sai vị trí (phản hồi nói theo cột/dòng, không nói 'ô mốc')"
            )
        if hidden and op.action != "unhide":
            context += f"; {', '.join(hidden)} đang ẩn: chọn bằng cách gõ địa chỉ vào ô Name Box"
        targets = _targets(op, before)
        items.append(
            ChangeItem(
                id=f"p{number}",
                sheet=sheet,
                kind=_kind(op),
                range=str(targets[0]),
                description=description,
                label=label,
                checks=tuple(_checks(op, after)),
                context=context,
                operation=op.to_json(),
                more_ranges=tuple(str(t) for t in targets[1:]),
                feedback_codes=("wrong_value", "empty") if op.action in ("insert", "delete") else (),
                guide=guide(op, before),
            )
        )
        before = after
    return items


def with_procedure(
    analysis: ExerciseAnalysis, steps: Sequence[ProcedureStep], states: Sequence[WorkbookSnapshot]
) -> ExerciseAnalysis:
    """Phân tích mới: các bước quy trình p1…pN rồi phần khác biệt còn lại (trạng thái cuối → đáp án)."""
    residual = analyze_snapshots(states[-1], analysis.solution, analysis.sheet)
    # Có chèn/xóa: dữ liệu dời chỗ giữa chừng, điều kiện "giữ nguyên dữ liệu" theo địa chỉ sẽ báo nhầm
    moves = any(s.operation.action in ("insert", "delete") for s in steps)
    return dataclasses.replace(
        analysis,
        changes=(*procedure_items(analysis, steps, states), *residual.changes),
        global_checks=() if moves else analysis.global_checks,
        preserved=() if moves else analysis.preserved,
    )
