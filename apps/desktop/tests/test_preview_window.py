"""Cửa sổ gia sư ở chế độ chạy thử phản ánh đúng trạng thái phiên (chạy Qt không cửa sổ thật: offscreen)."""

import json
import os
from pathlib import Path
from typing import Any

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QObject, pyqtSignal  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

from excel_core.checks import reference_requests  # noqa: E402
from excel_core.readers import full_request, read_workbook  # noqa: E402
from excel_core.snapshot import snapshot_to_dict  # noqa: E402
from tutor_desktop.agent.preview_session import PreviewSession  # noqa: E402
from tutor_desktop.ui.preview_window import PreviewWindow  # noqa: E402

REPO = Path(__file__).resolve().parents[3]
B22 = REPO / "packages" / "excel_core" / "tests" / "fixtures" / "b22"
SCRIPT = json.loads(
    (REPO / "schemas/tutor-script/v1/examples/b22-ham-tinh-tong.json").read_text(encoding="utf-8")
)


class FakeWatcher(QObject):
    """Có cùng signal và phương thức như ExcelWatcher, không đụng tới Excel."""

    opened = pyqtSignal(str)
    snapshot_ready = pyqtSignal(object)
    changed = pyqtSignal()
    printed = pyqtSignal()
    marks_ready = pyqtSignal(list)
    closed = pyqtSignal()
    failed = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self.requests: list[Any] = []
        self.highlights: list[Any] = []
        self.reads = 0

    def set_request(self, request: Any) -> None:
        self.requests.append(request)

    def set_highlights(self, highlights: list[Any]) -> None:
        self.highlights = highlights

    def request_read(self) -> None:
        self.reads += 1

    def stop(self) -> None: ...

    def wait(self, _ms: int) -> bool:
        return True


@pytest.fixture(scope="module")
def app() -> QApplication:
    return QApplication.instance() or QApplication([])  # type: ignore[return-value]


def window() -> tuple[PreviewWindow, FakeWatcher]:
    checks = [*SCRIPT["global_checks"], *(c for s in SCRIPT["steps"] for c in s["checks"])]
    files = {"starter": B22 / "de.xlsx", "solution": B22 / "dap-an.xlsx"}
    references = {
        source: snapshot_to_dict(read_workbook(files[source], request))
        for source, request in reference_requests(checks, SCRIPT["exercise"]["sheet"]).items()
    }
    bundle = {"exercise_title": "Hàm tính tổng SUM", "revision": 1, "status": "draft"}
    watcher = FakeWatcher()
    return PreviewWindow(PreviewSession(SCRIPT, references), bundle, watcher, None), watcher  # type: ignore[arg-type]


def snapshot(name: str):
    path = B22 / name
    return read_workbook(path, full_request(path))


def test_window_shows_step_card_hints_and_progress(app: QApplication):
    view, watcher = window()
    assert view.step_title.text() == "Bước 1/3: Tổng tiền ngày đầu tiên"
    assert "Chưa" not in view.status.text()

    watcher.snapshot_ready.emit(snapshot("de.xlsx"))
    assert "Chưa đạt" in view.status.text()

    view.hint_button.click()
    view.hint_button.click()
    view.hint_button.click()
    assert "Cấp 3 — Chỉ vị trí" in view.hints.text()
    assert [h.range or h.control for h in watcher.highlights] == ["F9", "C9:E9", "AutoSum"]

    watcher.snapshot_ready.emit(snapshot("dap-an.xlsx"))  # làm xong bước 1
    assert view.step_title.text().startswith("Bước 2/3")
    assert "✓ Đạt bước 1" in view.status.text()
    assert view.session.hint_level == 0 and watcher.highlights == []
    assert len(watcher.requests) == 1  # đổi phần cần đọc theo bước mới


def test_window_reaches_completion_and_can_restart(app: QApplication):
    view, watcher = window()
    finished = snapshot("dap-an.xlsx")
    for _ in SCRIPT["steps"]:
        watcher.snapshot_ready.emit(finished)
    assert view.step_title.text() == "🎉 Hoàn thành bài"
    assert "Bạn đã hoàn thành bài hàm SUM!" in view.task.text()

    view.session.restart()
    view._navigate(lambda: None)
    assert view.step_title.text().startswith("Bước 1/3")
