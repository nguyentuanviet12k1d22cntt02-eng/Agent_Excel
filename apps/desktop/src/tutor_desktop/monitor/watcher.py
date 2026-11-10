"""Luồng giám sát Excel cho chế độ chạy thử: mở file, bắt sự kiện, đọc snapshot, tính vị trí khung chỉ dẫn.

Chạy trên QThread riêng (COM STA của luồng này), giao tiếp với giao diện chỉ qua signal (quy tắc code 2.3
mục 1, 5). Định dạng ô không phát sự kiện SheetChange, nên ngoài sự kiện còn đọc lại định kỳ (khi Excel không
bận).
"""

import contextlib
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
from tutor_desktop.agent.guide import Guide, line_blocks, position, selection_matches
from tutor_desktop.agent.preview_session import Highlight
from tutor_desktop.monitor.excel_link import (
    UIA_ERRORS,
    ExcelBusyError,
    ExcelLink,
    Rect,
    WorkbookClosedError,
    attach_or_start_excel,
    call_with_retry,
    pump_messages,
)

logger = logging.getLogger(__name__)

POLL_SECONDS = 1.5  # đọc lại định kỳ: đổi định dạng không phát sự kiện
RECT_SECONDS = 0.3  # khung chỉ dẫn bám theo cuộn, phóng to, di chuyển cửa sổ (NFR-02 ≤ 300 ms)
LOOP_SECONDS = 0.05
MAX_READ_FAILURES = 5  # lỗi COM lạ liên tiếp chừng này lượt đọc mới dừng giám sát (một lượt hỏng thì đọc lại)


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
    guide_moved = pyqtSignal(int)  # chỗ đang dẫn trong chuỗi thao tác của bước
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
        self._read_failures = 0
        self._guide: Guide | None = None
        self._guide_index = -1
        self._last_selection: str | None = None

    # ------------------------------------------------------------ gọi từ luồng giao diện
    def set_request(self, request: ReadRequest) -> None:
        with self._lock:
            self._request = request
            self._read_now = True

    def set_highlights(self, highlights: list[Highlight]) -> None:
        with self._lock:
            self._highlights = list(highlights)

    def set_guide(self, guide: Guide | None) -> None:
        """Dẫn từng bước theo chuỗi thao tác (thay cho khoanh mọi vùng một lúc); None để tắt."""
        with self._lock:
            if guide != self._guide:
                self._guide, self._guide_index = guide, -1

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
        except ExcelBusyError:
            logger.warning("Excel bận quá lâu khi mở file")
            self.failed.emit(
                "Excel đang bận (có hộp thoại đang mở?). Đóng hộp thoại rồi mở lại chế độ chạy thử."
            )
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
        events.watcher, events.full_name = self, str(call_with_retry(lambda: link.workbook.FullName))
        self._events = events  # giữ tham chiếu: mất thì không nhận sự kiện nữa
        self.opened.emit(str(call_with_retry(lambda: link.workbook.Name)))
        return link

    def _take(self) -> tuple[bool, ReadRequest, list[Highlight], Guide | None, bool]:
        with self._lock:
            read_now, self._read_now = self._read_now, False
            return read_now, self._request, list(self._highlights), self._guide, self._stop

    def _loop(self, link: ExcelLink) -> None:
        last_read = last_marks = 0.0
        previous_marks: list[MarkRect] | None = None
        while True:
            pump_messages()
            read_now, request, highlights, guide, stop = self._take()
            if stop:
                return
            link.ensure_open()
            now = time.monotonic()
            if (read_now or now - last_read >= POLL_SECONDS) and not link.is_busy():
                last_read = now
                self._read(link, request)
            if now - last_marks >= RECT_SECONDS:
                marks = self._marks(link, highlights, guide)
                if marks != previous_marks:
                    self.marks_ready.emit(marks)
                    previous_marks = marks
                last_marks = now
            time.sleep(LOOP_SECONDS)

    def _read(self, link: ExcelLink, request: ReadRequest) -> bool:
        """Một lượt đọc snapshot.

        Excel bận thì đọc lại ngay vòng sau. Lỗi COM lạ thì bỏ lượt, chờ lượt đọc định kỳ; chỉ dừng giám sát
        khi hỏng MAX_READ_FAILURES lượt liền (Excel lỡ trả lỗi lúc đang tải file thì không sao).
        """
        try:
            snapshot = link.snapshot(request)
        except ExcelBusyError:
            self.request_read()
            return False
        except pywintypes.com_error:
            self._read_failures += 1
            if self._read_failures >= MAX_READ_FAILURES:
                raise
            logger.warning("Đọc Excel lỗi (lần %d), đọc lại sau", self._read_failures, exc_info=True)
            return False
        self._read_failures = 0
        self.snapshot_ready.emit(snapshot)
        return True

    def _guide_marks(self, link: ExcelLink, guide: Guide, busy: bool) -> list[MarkRect]:
        """Khung cho đúng chỗ đang dẫn: chưa chọn đúng vùng thì khoanh tiêu đề cột/dòng cần chọn (nhãn nằm
        trên dải tiêu đề), chọn rồi thì khoanh nút, mở menu rồi thì khoanh mục trong menu."""
        items, total = guide.items, len(guide.items)
        if not busy:
            # Excel bận giữa chừng: dùng vùng chọn đọc lần trước
            with contextlib.suppress(pywintypes.com_error, AttributeError):
                self._last_selection = link.selection(guide.sheet)
        selected = selection_matches(items[0], self._last_selection)
        found: dict[int, tuple[Rect, str]] = {}

        def shown(index: int) -> bool:
            item = items[index]
            target = link.ui_target(item.control or "", item.tab)
            if target is not None:
                found[index] = target
            return target is not None and target[1] == "control"

        index = position(items, selected, shown)
        if index != self._guide_index:
            self._guide_index = index
            self.guide_moved.emit(index)
        item = items[index]
        label = f"{index + 1}/{total}. {item.text}"
        if item.action == "select":
            # Mỗi nhóm cột liền nhau một khung (D–E và H, không trùm F, G); khung sau ghi "+ giữ Ctrl"
            unit = "cột" if item.axis == "cols" else "dòng"
            marks = []
            for number, block in enumerate(line_blocks(item)):
                rect = link.header_rect(block)
                if rect is None:
                    continue
                name = block[0] if len(block) == 1 else f"{block[0]}–{block[-1]}"
                marks.append(
                    MarkRect(rect, label if number == 0 else f"+ giữ Ctrl: {unit} {name}", "location")
                )
            return marks
        target = found.get(index) or link.ui_target(item.control or "", item.tab)
        if target is None:
            return []
        rect, kind = target
        if kind == "tab":
            return [MarkRect(rect, f"{index + 1}/{total}. Mở thẻ chứa nút trước: {item.text}", "tab")]
        return [MarkRect(rect, label, "location")]

    def _marks(
        self, link: ExcelLink, highlights: list[Highlight], guide: Guide | None = None
    ) -> list[MarkRect]:
        if not highlights and guide is None:
            return []
        try:
            if not link.is_foreground(os.getpid()):
                return []
            busy = link.is_busy()
            if guide is not None and guide.items:
                return self._guide_marks(link, guide, busy)
            if busy:
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
        except (pywintypes.com_error, AttributeError, ExcelBusyError, *UIA_ERRORS):
            # Khung chỉ dẫn không bao giờ được làm dừng luồng giám sát: lỗi thì bỏ nhịp này
            logger.debug("Bỏ một nhịp tính khung chỉ dẫn", exc_info=True)
            return []
