"""Phiên chạy thử kịch bản trên Excel (chế độ giảng viên, GĐ7).

Giảng viên làm bài như học viên; phiên giữ bước hiện tại, chấm bằng `excel_core.checks` trên snapshot đọc từ
Excel đang mở (cùng điều kiện, cùng snapshot tham chiếu như Desktop của học viên), tự chuyển bước khi đạt.
Gợi ý do giảng viên bấm xin từng cấp (chưa tự đưa gợi ý theo tín hiệu: phần đó là Teaching Agent, T7.5),
để xem trước lời và vị trí khoanh của từng cấp.

Kịch bản theo quy trình (bước có `operation`): phiên biết trạng thái mong đợi trước/sau từng bước (làm lần
lượt các thao tác trên file đề). Bài làm khác cả hai (bấm nhầm lệnh: ẩn nhầm cột, chèn nhầm chỗ) thì báo
lệch kèm chỗ sai; học viên hoàn tác (Ctrl+Z) về trạng thái trước một bước đã qua thì quay lui về bước đó.

Chỉ là logic, không gọi COM hay giao diện: luồng giám sát đưa snapshot vào, cửa sổ gia sư đọc trạng thái ra.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from excel_core.address import CellRange, parse_range
from excel_core.checks import CheckContext, CheckResult, CheckStatus, read_requests, run_check
from excel_core.procedure import ProcedureError, deviation, structure_changes
from excel_core.script.self_check import is_procedure, step_states
from excel_core.snapshot import (
    PropertyGroup,
    RangeRequest,
    ReadRequest,
    WorkbookSnapshot,
    merge_requests,
    snapshot_from_dict,
)
from tutor_desktop.agent.guide import GuideItem, parse_guide

MAX_HINT_LEVEL = 4
LOCATION_LEVEL = 3  # cấp "chỉ vị trí": khoanh vùng ô, nút trên Excel

type Script = Mapping[str, Any]


@dataclass(frozen=True)
class CheckState:
    index: int
    check: Mapping[str, Any]
    result: CheckResult

    @property
    def status(self) -> CheckStatus:
        return self.result.status


@dataclass(frozen=True)
class Highlight:
    """Một vùng khoanh trên Excel: vùng ô (`range`) hoặc nút Ribbon (`control`, kèm `tab` chứa nút)."""

    label: str
    range: str | None = None
    sheet: str | None = None
    control: str | None = None
    tab: str | None = None
    role: str = "target"  # target | source (vùng của bước) | hint (khoanh theo gợi ý cấp 3)


@dataclass(frozen=True)
class Evaluation:
    step_index: int  # bước đã chấm (trước khi chuyển bước)
    checks: tuple[CheckState, ...]
    status: CheckStatus
    global_violations: tuple[CheckState, ...]  # điều kiện toàn bài không đạt: gia sư nhắc ngay
    feedback: Mapping[str, Any] | None  # phản hồi theo mã lỗi của điều kiện chưa đạt đầu tiên
    advanced: bool  # bước vừa đạt và đã chuyển sang bước sau
    finished: bool
    deviation: tuple[str, ...] = ()  # quy trình: chỗ bài làm khác cả trước lẫn sau bước (bấm nhầm lệnh)
    rewound_to: int | None = None  # quy trình: học viên hoàn tác về trước bước này, phiên đã lùi về đó


def _status(states: Sequence[CheckState]) -> CheckStatus:
    if any(s.status == CheckStatus.FAILED for s in states):
        return CheckStatus.FAILED
    if any(s.status == CheckStatus.NOT_EVALUABLE for s in states):
        return CheckStatus.NOT_EVALUABLE
    return CheckStatus.PASSED


class PreviewSession:
    """Trạng thái một lần chạy thử: bước hiện tại, cấp gợi ý đã xin, các bước đã đạt."""

    def __init__(
        self,
        script: Script,
        references: Mapping[str, Mapping[str, Any]],
        layout_starter: WorkbookSnapshot | None = None,
    ) -> None:
        """`layout_starter`: snapshot cả vùng đang dùng của file đề (giá trị + cấu trúc, từ A1), để dựng trạng
        thái mong đợi của kịch bản theo quy trình; không có thì không báo lệch, không quay lui."""
        self.script = script
        self.sheet: str = script["exercise"]["sheet"]
        self.starter = snapshot_from_dict(references["starter"]) if "starter" in references else None
        self.solution = snapshot_from_dict(references["solution"]) if "solution" in references else None
        self.states: dict[str, tuple[WorkbookSnapshot, WorkbookSnapshot]] = {}
        self.layout_box: CellRange | None = None
        if layout_starter is not None and is_procedure(script):
            try:
                self.states = step_states(script, layout_starter, self.solution or layout_starter)
            except ProcedureError:
                self.states = {}
            boxes = [
                parse_range(read.range)
                for before, after in self.states.values()
                for state in (before, after)
                for read in state.sheet(self.sheet).read_ranges
            ]
            if boxes:
                self.layout_box = CellRange(
                    1, 1, max(b.max_col for b in boxes), max(b.max_row for b in boxes)
                )
        self.index = 0
        self.hint_level = 0
        self.done: set[str] = set()
        self.changes_in_step = 0
        self.printed_to_pdf = False
        self.confirmed = False

    # ------------------------------------------------------------ bước
    @property
    def steps(self) -> Sequence[Mapping[str, Any]]:
        return self.script["steps"]

    @property
    def finished(self) -> bool:
        return self.index >= len(self.steps)

    @property
    def current_step(self) -> Mapping[str, Any] | None:
        return None if self.finished else self.steps[self.index]

    def go_to(self, index: int) -> None:
        self.index = max(0, min(index, len(self.steps)))
        self.hint_level = 0
        self.changes_in_step = 0
        self.confirmed = False

    def skip(self) -> None:
        self.go_to(self.index + 1)

    def back(self) -> None:
        self.go_to(self.index - 1)

    def restart(self) -> None:
        self.done.clear()
        self.printed_to_pdf = False
        self.go_to(0)

    # ------------------------------------------------------------ đọc và chấm
    def _checks(self) -> list[Mapping[str, Any]]:
        step = self.current_step
        return [*self.script.get("global_checks", []), *(step["checks"] if step else [])]

    def read_request(self) -> ReadRequest:
        """Phần cần đọc trên Excel đang mở: điều kiện toàn bài và điều kiện của bước hiện tại; bước quy trình
        đọc thêm giá trị và cấu trúc cả bảng để so với trạng thái mong đợi."""
        request = read_requests(self._checks(), self.sheet).get("current") or ReadRequest()
        if self.layout_box is not None and self._procedural(self.current_step):
            groups = frozenset({PropertyGroup.VALUES, PropertyGroup.STRUCTURE})
            request = merge_requests([request, RangeRequest(self.sheet, str(self.layout_box), groups)])
        return request

    def _procedural(self, step: Mapping[str, Any] | None) -> bool:
        return step is not None and "operation" in step and step["id"] in self.states

    # ------------------------------------------------------------ dẫn từng bước
    def guide(self) -> tuple[GuideItem, ...]:
        """Chuỗi thao tác của bước hiện tại (chọn vùng → nút → mục menu); bước không có thì rỗng."""
        return parse_guide(self.current_step)

    def guiding(self, show_targets: bool = False) -> bool:
        """Dẫn từng thao tác (thay cho khoanh mọi vùng một lúc) khi đã xin tới cấp 3 hoặc bật khoanh vùng."""
        return bool(self.guide()) and (show_targets or self.hint_level >= LOCATION_LEVEL)

    def note_change(self) -> None:
        """Người làm vừa sửa trang tính: từ đây mới hiện phản hồi theo lỗi (đầu bước mọi ô còn trống)."""
        self.changes_in_step += 1

    def note_printed(self) -> None:
        self.printed_to_pdf = True

    def confirm(self) -> None:
        """Bấm "Đã xong" cho bước quan sát/nhận xét (observation_only)."""
        self.confirmed = True

    def evaluate(self, current: WorkbookSnapshot) -> Evaluation:
        ctx = CheckContext(
            current=current,
            default_sheet=self.sheet,
            starter=self.starter,
            solution=self.solution,
            printed_to_pdf=self.printed_to_pdf,
            learner_confirmed=self.confirmed,
        )
        global_states = tuple(
            CheckState(i, c, run_check(c, ctx)) for i, c in enumerate(self.script.get("global_checks", []))
        )
        violations = tuple(s for s in global_states if s.status == CheckStatus.FAILED)
        step = self.current_step
        if step is None:
            return Evaluation(self.index, (), CheckStatus.PASSED, violations, None, False, True)
        states = tuple(CheckState(i, c, run_check(c, ctx)) for i, c in enumerate(step["checks"]))
        status = _status(states)
        feedback = self._feedback(step, states) if status == CheckStatus.FAILED else None
        index = self.index
        advanced = status == CheckStatus.PASSED
        if advanced:
            self.done.add(step["id"])
            self.go_to(index + 1)
            return Evaluation(index, states, status, violations, feedback, advanced, self.finished)
        if not self._procedural(step):
            return Evaluation(index, states, status, violations, feedback, advanced, self.finished)
        before, after = self.states[step["id"]]
        if not structure_changes(before, current, self.sheet):
            return Evaluation(index, states, status, violations, feedback, advanced, self.finished)
        target = self._rewind_target(current, ctx)
        if target is not None:
            for later in self.steps[target:]:
                self.done.discard(later["id"])
            self.go_to(target)
            return Evaluation(index, states, status, violations, None, False, False, rewound_to=target)
        off = tuple(deviation(before, after, current, self.sheet))
        return Evaluation(index, states, status, violations, None if off else feedback, False, False, off)

    def _rewind_target(self, current: WorkbookSnapshot, ctx: CheckContext) -> int | None:
        """Bước quy trình trước bước hiện tại mà bài làm khớp trạng thái lúc bắt đầu bước đó (đã hoàn tác).

        Không so độ rộng (COM lệch theo màn hình) nên "đã ẩn H" và "đã ẩn H, đã chỉnh độ rộng" giống nhau: chỉ
        nhận khi điều kiện của bước ngay trước bước đó vẫn đạt trên bài làm (như chấm thử, grade.py).
        """
        for target in range(self.index - 1, -1, -1):
            step = self.steps[target]
            if not self._procedural(step):
                continue
            if structure_changes(self.states[step["id"]][0], current, self.sheet):
                continue
            previous = self.steps[target - 1] if target > 0 else None
            if previous is None or all(run_check(c, ctx).passed for c in previous["checks"]):
                return target
        return None

    def _feedback(self, step: Mapping[str, Any], states: Sequence[CheckState]) -> Mapping[str, Any] | None:
        if self.changes_in_step == 0:
            return None
        by_code = {f["code"]: f for f in step.get("feedback", [])}
        for state in states:
            code = state.result.code
            if state.status == CheckStatus.FAILED and code in by_code:
                return by_code[code]
        return None

    # ------------------------------------------------------------ gợi ý
    def next_hint(self) -> Mapping[str, Any] | None:
        """Xin thêm một cấp gợi ý (như học viên bấm trợ giúp); hết cấp thì giữ cấp 4."""
        if self.finished:
            return None
        self.hint_level = min(MAX_HINT_LEVEL, self.hint_level + 1)
        return self.hint(self.hint_level)

    def hint(self, level: int) -> Mapping[str, Any] | None:
        step = self.current_step
        if step is None or not 1 <= level <= MAX_HINT_LEVEL:
            return None
        return step["hints"][level - 1]

    def highlights(self, show_targets: bool = False) -> list[Highlight]:
        """Vùng khoanh trên Excel: theo gợi ý cấp 3 khi đã xin tới cấp đó; `show_targets` để giảng viên xem
        luôn vùng mục tiêu, vùng nguồn của bước."""
        step = self.current_step
        if step is None:
            return []
        found: list[Highlight] = []
        # Nhãn của vùng lấy theo vùng mục tiêu cùng địa chỉ; không có thì ghi chung, không in địa chỉ ô
        labels = {(c.get("sheet"), c["range"]): c.get("label") for c in step["targets"]["cells"]}
        hinted = set()
        if self.hint_level >= LOCATION_LEVEL:
            hinted = {
                (i["cells"].get("sheet"), i["cells"]["range"])
                for i in step["hints"][LOCATION_LEVEL - 1].get("highlight", [])
                if "cells" in i
            }
        if show_targets:
            for cell in step["targets"]["cells"]:
                if (cell.get("sheet"), cell["range"]) in hinted:
                    continue  # cùng vùng với khung gợi ý cấp 3: chỉ vẽ một khung
                label = cell.get("label") or "Vùng của bước"
                found.append(Highlight(label, cell["range"], cell.get("sheet"), role=cell["role"]))
        if self.hint_level >= LOCATION_LEVEL:
            for item in step["hints"][LOCATION_LEVEL - 1].get("highlight", []):
                if "cells" in item:
                    cells = item["cells"]
                    label = cells.get("label") or labels.get((cells.get("sheet"), cells["range"]))
                    role = "source" if cells.get("role") == "source" else "hint"  # nguồn: xanh lá, nét đứt
                    found.append(
                        Highlight(label or "Vùng được khoanh", cells["range"], cells.get("sheet"), role=role)
                    )
                elif "ui" in item:
                    ui = item["ui"]
                    found.append(
                        Highlight(
                            ui.get("label") or ui["control"],
                            control=ui["control"],
                            tab=ui.get("tab"),
                            role="hint",
                        )
                    )
        return found
