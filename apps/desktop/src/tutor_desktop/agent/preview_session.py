"""Phiên chạy thử kịch bản trên Excel (chế độ giảng viên, GĐ7).

Giảng viên làm bài như học viên; phiên giữ bước hiện tại, chấm bằng `excel_core.checks` trên snapshot đọc từ
Excel đang mở (cùng điều kiện, cùng snapshot tham chiếu như Desktop của học viên), tự chuyển bước khi đạt.
Gợi ý do giảng viên bấm xin từng cấp (chưa tự đưa gợi ý theo tín hiệu: phần đó là Teaching Agent, T7.5),
để xem trước lời và vị trí khoanh của từng cấp.

Chỉ là logic, không gọi COM hay giao diện: luồng giám sát đưa snapshot vào, cửa sổ gia sư đọc trạng thái ra.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from excel_core.checks import CheckContext, CheckResult, CheckStatus, read_requests, run_check
from excel_core.snapshot import ReadRequest, WorkbookSnapshot, snapshot_from_dict

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


def _status(states: Sequence[CheckState]) -> CheckStatus:
    if any(s.status == CheckStatus.FAILED for s in states):
        return CheckStatus.FAILED
    if any(s.status == CheckStatus.NOT_EVALUABLE for s in states):
        return CheckStatus.NOT_EVALUABLE
    return CheckStatus.PASSED


class PreviewSession:
    """Trạng thái một lần chạy thử: bước hiện tại, cấp gợi ý đã xin, các bước đã đạt."""

    def __init__(self, script: Script, references: Mapping[str, Mapping[str, Any]]) -> None:
        self.script = script
        self.sheet: str = script["exercise"]["sheet"]
        self.starter = snapshot_from_dict(references["starter"]) if "starter" in references else None
        self.solution = snapshot_from_dict(references["solution"]) if "solution" in references else None
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
        """Phần cần đọc trên Excel đang mở: điều kiện toàn bài và điều kiện của bước hiện tại."""
        return read_requests(self._checks(), self.sheet).get("current") or ReadRequest()

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
        if show_targets:
            for cell in step["targets"]["cells"]:
                label = cell.get("label") or cell["range"]
                found.append(Highlight(label, cell["range"], cell.get("sheet"), role=cell["role"]))
        if self.hint_level >= LOCATION_LEVEL:
            for item in step["hints"][LOCATION_LEVEL - 1].get("highlight", []):
                if "cells" in item:
                    cells = item["cells"]
                    found.append(
                        Highlight(
                            cells.get("label") or cells["range"],
                            cells["range"],
                            cells.get("sheet"),
                            role="hint",
                        )
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
