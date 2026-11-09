"""Cửa sổ gia sư ở chế độ chạy thử (T7.6): thẻ yêu cầu, tiến độ, gợi ý từng cấp, phản hồi, chi tiết điều kiện.

Nhận dữ liệu qua signal của luồng giám sát (quy tắc code 2.3 mục 5); không gọi COM, không gọi API.
"""

from collections.abc import Mapping
from html import escape
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from excel_core.checks import CheckStatus
from excel_core.snapshot import WorkbookSnapshot
from tutor_desktop.agent.preview_session import Evaluation, PreviewSession
from tutor_desktop.monitor.watcher import ExcelWatcher, MarkRect
from tutor_desktop.ui.overlay import OverlayManager

WINDOW_WIDTH = 400
MARGIN = 12
LEVEL_NAMES = ("Định hướng", "Gợi ý công cụ", "Chỉ vị trí", "Hướng dẫn chi tiết")
STATUS_NAMES = {
    "draft": "nháp",
    "pending_review": "chờ duyệt",
    "approved": "đã duyệt",
    "published": "đang phát hành",
}
MARKS = {CheckStatus.PASSED: "✓", CheckStatus.FAILED: "✗", CheckStatus.NOT_EVALUABLE: "?"}


def _label(text: str = "", *, bold: bool = False, size: int = 0, color: str = "") -> QLabel:
    label = QLabel(text)
    label.setWordWrap(True)
    label.setTextFormat(Qt.TextFormat.RichText)
    style = []
    if bold:
        style.append("font-weight: 600")
    if size:
        style.append(f"font-size: {size}pt")
    if color:
        style.append(f"color: {color}")
    label.setStyleSheet("; ".join(style))
    return label


class PreviewWindow(QWidget):
    def __init__(
        self,
        session: PreviewSession,
        bundle: Mapping[str, Any],
        watcher: ExcelWatcher,
        overlay: OverlayManager | None,
    ) -> None:
        super().__init__()
        self.session, self.bundle, self.watcher, self.overlay = session, bundle, watcher, overlay
        self.last: Evaluation | None = None
        self.message = ""
        self.setWindowTitle("Gia sư Excel — chạy thử")
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self._build()
        watcher.opened.connect(self._on_opened)
        watcher.snapshot_ready.connect(self._on_snapshot)
        watcher.changed.connect(self.session.note_change)
        watcher.printed.connect(self._on_printed)
        watcher.marks_ready.connect(self._on_marks)
        watcher.closed.connect(
            lambda: self._fatal("File chạy thử đã bị đóng trong Excel. Mở lại để chạy tiếp.")
        )
        watcher.failed.connect(self._fatal)
        self._sync()

    # ------------------------------------------------------------ dựng giao diện
    def _build(self) -> None:
        status = STATUS_NAMES.get(str(self.bundle["status"]), str(self.bundle["status"]))
        self.header = _label(f"{escape(str(self.bundle['exercise_title']))}", bold=True, size=11)
        self.subheader = _label(
            f"Bản {self.bundle['revision']} ({status}) · đang mở file trong Excel…", color="#5d6a63"
        )
        self.steps = QListWidget()
        self.steps.setMaximumHeight(130)
        self.steps.itemClicked.connect(lambda item: self._go(self.steps.row(item)))
        self.step_title = _label(bold=True, size=12)
        self.task = _label()
        self.status = _label(bold=True)
        self.violation = _label(color="#b42318")
        self.feedback = _label(color="#1f5fa8")
        self.hint_button = QPushButton("Xin gợi ý")
        self.hint_button.clicked.connect(self._next_hint)
        self.hints = _label()
        self.show_targets = QCheckBox("Khoanh vùng của bước trên Excel")
        self.show_targets.toggled.connect(lambda _: self._sync_highlights())
        self.show_checks = QCheckBox("Xem chi tiết điều kiện kiểm")
        self.show_checks.toggled.connect(lambda _: self._render_checks())
        self.checks = _label(color="#5d6a63")
        self.confirm = QPushButton("Đã xong")
        self.confirm.clicked.connect(self._confirm)

        buttons = QHBoxLayout()
        for text, action in (
            ("← Bước trước", self.session.back),
            ("Bỏ qua bước →", self.session.skip),
            ("Làm lại từ đầu", self.session.restart),
        ):
            button = QPushButton(text)
            button.clicked.connect(lambda _, act=action: self._navigate(act))
            buttons.addWidget(button)
        recheck = QPushButton("Chấm lại")
        recheck.clicked.connect(self.watcher.request_read)
        buttons.addWidget(recheck)

        body = QWidget()
        layout = QVBoxLayout(body)
        for widget in (
            self.header,
            self.subheader,
            self.steps,
            self.step_title,
            self.task,
            self.status,
            self.violation,
            self.feedback,
            self.confirm,
            self.hint_button,
            self.hints,
            self.show_targets,
            self.show_checks,
            self.checks,
        ):
            layout.addWidget(widget)
        layout.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(body)
        outer = QVBoxLayout(self)
        outer.addWidget(scroll)
        outer.addLayout(buttons)
        self.resize(WINDOW_WIDTH, 720)
        screen = QApplication.primaryScreen()
        if screen is not None:
            area = screen.availableGeometry()
            self.move(area.right() - WINDOW_WIDTH - MARGIN, area.top() + MARGIN)

    # ------------------------------------------------------------ nhận từ luồng giám sát
    def _on_opened(self, name: str) -> None:
        status = STATUS_NAMES.get(str(self.bundle["status"]), str(self.bundle["status"]))
        self.subheader.setText(f"Bản {self.bundle['revision']} ({status}) · file <b>{escape(name)}</b>")

    def _on_snapshot(self, snapshot: WorkbookSnapshot) -> None:
        evaluation = self.session.evaluate(snapshot)
        self.last = evaluation
        if evaluation.advanced:
            done = self.session.steps[evaluation.step_index]["title"]
            self.message = f"✓ Đạt bước {evaluation.step_index + 1}: {done}"
            self.watcher.set_request(self.session.read_request())
            self._sync()
        else:
            self._render_status()

    def _on_printed(self) -> None:
        self.session.note_printed()
        self.watcher.request_read()

    def _on_marks(self, marks: list[MarkRect]) -> None:
        if self.overlay is not None:
            self.overlay.show(marks)

    def _fatal(self, message: str) -> None:
        self.status.setText(f"<span style='color:#b42318'>{escape(message)}</span>")
        if self.overlay is not None:
            self.overlay.hide()

    # ------------------------------------------------------------ thao tác của giảng viên
    def _navigate(self, action: Any) -> None:
        action()
        self.message = ""
        self.last = None
        self.watcher.set_request(self.session.read_request())
        self._sync()

    def _go(self, index: int) -> None:
        self._navigate(lambda: self.session.go_to(index))

    def _next_hint(self) -> None:
        self.session.next_hint()
        self._render_hints()
        self._sync_highlights()

    def _confirm(self) -> None:
        self.session.confirm()
        self.watcher.request_read()

    # ------------------------------------------------------------ hiển thị
    def _sync(self) -> None:
        self.steps.clear()
        for number, step in enumerate(self.session.steps, start=1):
            mark = (
                "✓" if step["id"] in self.session.done else "▶" if number - 1 == self.session.index else " "
            )
            item = QListWidgetItem(f"{mark}  {number}. {step['title']}")
            self.steps.addItem(item)
        if not self.session.finished:
            self.steps.setCurrentRow(self.session.index)
        step = self.session.current_step
        if step is None:
            completion = self.session.script.get("completion", {})
            self.step_title.setText("🎉 Hoàn thành bài")
            criteria = "".join(f"<li>{escape(c['text'])}</li>" for c in completion.get("criteria", []))
            self.task.setText(
                escape(completion.get("message", "Bạn đã làm xong mọi bước."))
                + (f"<ul>{criteria}</ul>" if criteria else "")
            )
        else:
            total = len(self.session.steps)
            self.step_title.setText(f"Bước {self.session.index + 1}/{total}: {escape(step['title'])}")
            self.task.setText(escape(step["task"]))
        observation = step is not None and any(c["type"] == "observation_only" for c in step["checks"])
        self.confirm.setVisible(observation)
        self.hint_button.setEnabled(step is not None)
        self._render_hints()
        self._render_status()
        self._sync_highlights()

    def _render_status(self) -> None:
        evaluation = self.last
        lines = [self.message] if self.message else []
        if self.session.finished:
            lines.append("Đã xong cả bài.")
        elif evaluation is None or evaluation.advanced:
            lines.append("Đang chờ chấm…")
        elif evaluation.status == CheckStatus.FAILED:
            lines.append("Chưa đạt: gia sư chờ bạn làm tiếp.")
        elif evaluation.status == CheckStatus.NOT_EVALUABLE:
            lines.append("Có điều kiện không chấm được trên Excel đang mở (xem chi tiết).")
        self.status.setText("<br>".join(escape(line) for line in lines))
        violations = evaluation.global_violations if evaluation else ()
        self.violation.setVisible(bool(violations))
        if violations:
            text = "; ".join(v.check.get("description") or v.check["type"] for v in violations)
            self.violation.setText(f"⚠ Gia sư nhắc ngay: {escape(text)} Bấm Ctrl+Z để hoàn tác.")
        feedback = evaluation.feedback if evaluation and not evaluation.advanced else None
        self.feedback.setVisible(feedback is not None)
        if feedback:
            self.feedback.setText(f"💬 Gia sư: “{escape(feedback['message'])}”")
        self._render_checks()

    def _render_hints(self) -> None:
        parts = []
        for level in range(1, self.session.hint_level + 1):
            hint = self.session.hint(level)
            if hint is None:
                continue
            text = f"<b>Cấp {level} — {LEVEL_NAMES[level - 1]}:</b> {escape(hint['text'])}"
            if level == 4:  # noqa: PLR2004 — cấp hướng dẫn chi tiết
                text += "<ol>" + "".join(f"<li>{escape(a)}</li>" for a in hint.get("actions", [])) + "</ol>"
                if hint.get("alternative"):
                    text += f"<i>Cách khác: {escape(hint['alternative'])}</i>"
            parts.append(text)
        self.hints.setText("<br><br>".join(parts))
        level = self.session.hint_level
        self.hint_button.setText("Đã hiện đủ 4 cấp gợi ý" if level >= 4 else f"Xin gợi ý (cấp {level + 1})")  # noqa: PLR2004
        self.hint_button.setEnabled(not self.session.finished and level < 4)  # noqa: PLR2004

    def _render_checks(self) -> None:
        evaluation = self.last
        self.checks.setVisible(self.show_checks.isChecked())
        if not self.show_checks.isChecked() or evaluation is None:
            self.checks.setText("")
            return
        rows = []
        for state in evaluation.checks:
            result = state.result
            cells = ", ".join(result.cells[:6])
            extra = f" — {escape(result.code or '')}{(' ở ' + cells) if cells else ''}" if result.code else ""
            rows.append(f"{MARKS[result.status]} {escape(state.check['type'])}{extra}")
        self.checks.setText("<br>".join(rows))

    def _sync_highlights(self) -> None:
        self.watcher.set_highlights(self.session.highlights(self.show_targets.isChecked()))

    def closeEvent(self, event: QCloseEvent | None) -> None:  # noqa: N802 — tên do Qt quy định
        self.watcher.stop()
        self.watcher.wait(3000)
        if self.overlay is not None:
            self.overlay.hide()
        super().closeEvent(event)
