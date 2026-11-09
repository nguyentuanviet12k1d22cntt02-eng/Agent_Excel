"""Excel bận thì thử lại, một lượt đọc hỏng không làm dừng giám sát (chạy không cần Excel).

Lỗi gặp khi chạy thử bài 06: vừa mở file, Excel trả 0x800AC472 ("bỏ qua lệnh vì đang bận") cho UsedRange; app
coi là lỗi thật và dừng luồng giám sát.
"""

import os
from pathlib import Path
from typing import Any

import pytest
import pywintypes

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication  # noqa: E402

from excel_core.snapshot import ReadRequest  # noqa: E402
from tutor_desktop.monitor.excel_link import (  # noqa: E402
    VBA_E_IGNORE,
    ExcelBusyError,
    ExcelLink,
    WorkbookClosedError,
    call_with_retry,
    is_busy_error,
)
from tutor_desktop.monitor.watcher import MAX_READ_FAILURES, ExcelWatcher  # noqa: E402

IGNORED = pywintypes.com_error(VBA_E_IGNORE, "OLE error 0x800ac472", None, None)
CLOSED = pywintypes.com_error(
    -2147417848, "The object invoked has disconnected from its clients.", None, None
)
ODD = pywintypes.com_error(-2147352567, "Exception occurred.", None, None)  # lỗi COM không phải "bận"


@pytest.fixture(scope="module")
def app() -> QApplication:
    return QApplication.instance() or QApplication([])  # type: ignore[return-value]


def test_excel_ignoring_a_call_counts_as_busy():
    assert is_busy_error(IGNORED)
    assert not is_busy_error(CLOSED)


def test_call_with_retry_waits_out_a_busy_excel():
    answers: list[Any] = [IGNORED, IGNORED, "Bài tập"]

    def call() -> Any:
        answer = answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer

    assert call_with_retry(call, delay=0) == "Bài tập"
    with pytest.raises(ExcelBusyError):
        call_with_retry(lambda: (_ for _ in ()).throw(IGNORED), attempts=2, delay=0)


class _Workbook:
    def __init__(self, error: Exception) -> None:
        self.error = error

    @property
    def Name(self) -> str:  # noqa: N802 — tên thuộc tính COM
        raise self.error


def test_busy_excel_is_not_mistaken_for_a_closed_workbook():
    link = ExcelLink(Path("bai-06.xlsx"))
    link.workbook = _Workbook(IGNORED)
    link.ensure_open()  # bận: coi như còn mở, lượt sau kiểm lại

    link.workbook = _Workbook(CLOSED)
    with pytest.raises(WorkbookClosedError):
        link.ensure_open()


class _Link:
    def __init__(self, *errors: Exception) -> None:
        self.errors = list(errors)

    def snapshot(self, _request: ReadRequest) -> str:
        if self.errors:
            raise self.errors.pop(0)
        return "snapshot"


def test_a_failed_read_is_retried_instead_of_stopping_the_watcher(app: QApplication):
    watcher = ExcelWatcher(Path("bai-06.xlsx"))
    got: list[object] = []
    watcher.snapshot_ready.connect(got.append)
    link = _Link(ExcelBusyError("bận"), ODD, ODD)

    watcher._take()  # xóa cờ "đọc ngay" lúc mới mở
    assert watcher._read(link, ReadRequest()) is False  # type: ignore[arg-type]
    assert watcher._take()[0]  # bận: xin đọc lại ngay vòng sau
    for _ in range(2):
        assert watcher._read(link, ReadRequest()) is False  # type: ignore[arg-type]
        assert not watcher._take()[0]  # lỗi lạ: chờ lượt đọc định kỳ, không đọc dồn dập
    assert watcher._read(link, ReadRequest()) is True  # type: ignore[arg-type]
    assert got == ["snapshot"] and watcher._read_failures == 0


def test_the_watcher_stops_after_repeated_failures(app: QApplication):
    watcher = ExcelWatcher(Path("bai-06.xlsx"))
    link = _Link(*[ODD] * MAX_READ_FAILURES)

    for _ in range(MAX_READ_FAILURES - 1):
        assert watcher._read(link, ReadRequest()) is False  # type: ignore[arg-type]
    with pytest.raises(pywintypes.com_error):
        watcher._read(link, ReadRequest())  # type: ignore[arg-type]
