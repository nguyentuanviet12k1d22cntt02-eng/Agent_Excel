"""Luồng giám sát Excel cho chế độ chạy thử: mở file, bắt sự kiện, đọc snapshot, tính vị trí khung chỉ dẫn.

Chạy trên QThread riêng (COM STA của luồng này), giao tiếp với giao diện chỉ qua signal (quy tắc code 2.3
mục 1, 5). Định dạng ô không phát sự kiện SheetChange, nên ngoài sự kiện còn đọc lại định kỳ (khi Excel không
bận).
"""

import gc
import logging
import os
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pythoncom
import pywintypes
import uiautomation as auto
import win32com.client
from PyQt6.QtCore import QThread, pyqtSignal

from excel_core.snapshot import ReadRequest
from tutor_desktop.agent.preview_session import Highlight
from tutor_desktop.monitor.excel_link import (
    ExcelBusyError,
    ExcelLink,
    Rect,
    WorkbookClosedError,
    attach_or_start_excel,
    pump_messages,
)

logger = logging.getLogger(__name__)

POLL_SECONDS = 1.5  # đọc lại định kỳ: đổi định dạng không phát sự kiện
RECT_SECONDS = 0.3  # khung chỉ dẫn bám theo cuộn, phóng to, di chuyển cửa sổ (NFR-02 ≤ 300 ms)
LOOP_SECONDS = 0.05


@dataclass(frozen=True)
class MarkRect:
    rect: Rect  # pixel vật lý
    label: str
    role: str  # target | source | location | tab


class _AppEvents:
    """Sự kiện của Excel.Application; chỉ quan tâm file đang chạy thử."""

    watcher: ExcelWatcher
    full_name: str

    def _ours(self, workbook: Any) -> bool:
        try:
            return str(workbook.FullName) == self.full_name
        except pywintypes.com_error:
            return False

    def OnSheetChange(self, sheet: Any, _target: Any) -> None:  # noqa: N802 — tên do COM quy định
        if self._ours(sheet.Parent):
            self.watcher.mark_changed()

    def OnSheetActivate(self, sheet: Any) -> None:  # noqa: N802
        if self._ours(sheet.Parent):
            self.watcher.request_read()

    def OnWorkbookBeforePrint(self, workbook: Any, _cancel: Any) -> None:  # noqa: N802
        if self._ours(workbook):
            self.watcher.printed.emit()


class ExcelWatcher(QThread):
    opened = pyqtSignal(str)  # tên file
    snapshot_ready = pyqtSignal(object)  # WorkbookSnapshot
    changed = pyqtSignal()  # người làm vừa sửa ô
    printed = pyqtSignal()
    marks_ready = pyqtSignal(list)  # list[MarkRect]
    closed = pyqtSignal()
    failed = pyqtSignal(str)

    def __init__(self, path: Path, excel_factory: Callable[[], Any] = attach_or_start_excel) -> None:
        super().__init__()
        self.path = path
        self._factory = excel_factory
        self._lock = threading.Lock()
        self._request = ReadRequest()
        self._highlights: list[Highlight] = []
        self._read_now = True
        self._stop = False
        self._events: Any = None

    # ------------------------------------------------------------ gọi từ luồng giao diện
    def set_request(self, request: ReadRequest) -> None:
        with self._lock:
            self._request = request
            self._read_now = True

    def set_highlights(self, highlights: list[Highlight]) -> None:
        with self._lock:
            self._highlights = list(highlights)

    def request_read(self) -> None:
        with self._lock:
            self._read_now = True

    def mark_changed(self) -> None:
        self.changed.emit()
        self.request_read()

    def stop(self) -> None:
        with self._lock:
            self._stop = True

    # ------------------------------------------------------------ luồng giám sát
    def run(self) -> None:
        pythoncom.CoInitialize()
        try:
            with auto.UIAutomationInitializerInThread():
                self._loop(self._open())
        except WorkbookClosedError:
            self.closed.emit()
        except (pywintypes.com_error, OSError) as exc:
            logger.exception("Luồng giám sát dừng")
            self.failed.emit(f"Không làm việc được với Excel: {exc}")
        finally:
            # Nhả mọi tham chiếu COM của luồng này trước khi CoUninitialize (giữ lại thì tiến trình Excel do
            # app mở không thoát được khi người dùng đóng Excel)
            if self._events is not None:
                self._events.close()  # ngắt kết nối sự kiện COM
                self._events = None
            gc.collect()
            pythoncom.CoUninitialize()

    def _open(self) -> ExcelLink:
        link = ExcelLink(self.path, self._factory)
        link.open()
        events = win32com.client.WithEvents(link.excel, _AppEvents)
        events.watcher, events.full_name = self, str(link.workbook.FullName)
        self._events = events  # giữ tham chiếu: mất thì không nhận sự kiện nữa
        self.opened.emit(str(link.workbook.Name))
        return link

    def _take(self) -> tuple[bool, ReadRequest, list[Highlight], bool]:
        with self._lock:
            read_now, self._read_now = self._read_now, False
            return read_now, self._request, list(self._highlights), self._stop

    def _loop(self, link: ExcelLink) -> None:
        last_read = last_marks = 0.0
        previous_marks: list[MarkRect] | None = None
        while True:
            pump_messages()
            read_now, request, highlights, stop = self._take()
            if stop:
                return
            link.ensure_open()
            now = time.monotonic()
            if (read_now or now - last_read >= POLL_SECONDS) and not link.is_busy():
                try:
                    self.snapshot_ready.emit(link.snapshot(request))
                    last_read = now
                except ExcelBusyError:
                    self.request_read()
            if now - last_marks >= RECT_SECONDS:
                marks = self._marks(link, highlights)
                if marks != previous_marks:
                    self.marks_ready.emit(marks)
                    previous_marks = marks
                last_marks = now
            time.sleep(LOOP_SECONDS)

    def _marks(self, link: ExcelLink, highlights: list[Highlight]) -> list[MarkRect]:
        if not highlights:
            return []
        try:
            if link.is_busy() or not link.is_foreground(os.getpid()):
                return []
            marks = []
            for item in highlights:
                if item.range:
                    rect = link.cell_rect(item.range, item.sheet)
                    role = {"source": "source", "hint": "location"}.get(item.role, "target")
                    if rect:
                        marks.append(MarkRect(rect, item.label, role))
                elif item.control:
                    found = link.ribbon_rect(item.control, item.tab)
                    if found:
                        rect, kind = found
                        label = item.label if kind == "control" else f"Mở thẻ chứa nút {item.label}"
                        marks.append(MarkRect(rect, label, "location" if kind == "control" else "tab"))
            return marks
        except pywintypes.com_error, AttributeError, ExcelBusyError, LookupError:
            return []
