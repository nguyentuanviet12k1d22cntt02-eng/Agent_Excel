"""Kết nối Excel qua COM cho luồng giám sát: mở file, đọc snapshot, tọa độ vùng ô và nút Ribbon trên màn hình.

Mọi hàm ở đây chạy trên luồng giám sát (đã CoInitialize), không chạy trên luồng giao diện (quy tắc code 2.3
mục 1). Chỉ đọc: không ghi gì vào workbook (NFR-06), không bao giờ đóng Excel của người dùng (mục 4).

Kết quả spike GĐ2 dùng ở đây:
- Excel bận (đang sửa ô, mở hộp thoại) có hai dạng lỗi: com_error 0x80010001/0x8001010A (và 0x800AC472 khi
  Excel bỏ qua lệnh) và AttributeError khi gọi trễ; biết Excel bận bằng GetIDsOfNames thô lên CommandBars,
  không dùng Excel.Ready (T2.2).
- Tọa độ ô: COM PointsToScreenPixels chỉ đúng khi DPI cửa sổ Excel bằng DPI hệ thống; khác thì dùng UIA ô
  đầu, ô cuối của phần vùng đang hiện (T2.5). Nút Ribbon tìm theo AutomationId = idMso (T2.4).
- Tiêu đề cột/dòng là DataItem con trực tiếp của lưới "Grid", tên là chữ cột/số dòng ("D", "19").
- Mục trong menu thả xuống (Format, mũi tên Insert/Delete) KHÔNG có AutomationId, chỉ có tên hiển thị; chỉ
  hiện trong cây UIA khi menu cha đang mở (ExpandCollapseState = Expanded), nằm dưới nút mở menu hoặc dưới
  nút cha của nó (nút tách Insert/Delete). Popup menu là cửa sổ riêng của tiến trình Excel.
- Đọc vùng chọn (ActiveWindow.RangeSelection.Address) không làm đổi vùng chọn, đọc được cả khi menu đang mở.
"""

import _ctypes
import ctypes
import logging
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pythoncom
import pywintypes
import uiautomation as auto
import win32com.client
import win32gui
import win32process

from excel_core.readers.com_reader import read_workbook_com
from excel_core.snapshot import ReadRequest, WorkbookSnapshot

logger = logging.getLogger(__name__)

RPC_E_CALL_REJECTED = -2147418111  # 0x80010001
RPC_E_SERVERCALL_RETRYLATER = -2147417846  # 0x8001010A
# Excel bỏ qua lệnh vì đang bận việc khác: vừa mở file, đang kéo chuột chọn vùng… (gặp khi chạy thử bài 06)
VBA_E_IGNORE = -2146777998  # 0x800AC472
BUSY_CODES = {RPC_E_CALL_REJECTED, RPC_E_SERVERCALL_RETRYLATER, VBA_E_IGNORE}
BUSY_ATTEMPTS = 5
BUSY_DELAY_SECONDS = 0.1
OPEN_ATTEMPTS = 50  # mở file: Excel có thể bận vài giây (đang tải, đang vẽ)
UIA_SEARCH_DEPTH = 30
MENU_SEARCH_DEPTH = 8
EXPANDED = 1  # ExpandCollapseState.Expanded
# Lỗi khi đọc cây UIA: phần tử biến mất giữa chừng (menu vừa đóng, Ribbon vẽ lại) báo COMError
# 0x80040201 UIA_E_ELEMENTNOTAVAILABLE; không tìm thấy thì uiautomation báo LookupError
UIA_ERRORS = (LookupError, OSError, _ctypes.COMError)

type Com = Any
type Rect = tuple[int, int, int, int]  # pixel vật lý: trái, trên, phải, dưới


@dataclass(frozen=True)
class MenuItem:
    """Mục menu thả xuống: mở từ `parent` (idMso nút Ribbon hoặc mã mục menu cha), tìm theo tên hiển thị."""

    parent: str
    names: tuple[str, ...]  # Office tiếng Anh; thêm tên tiếng Việt khi có máy cài gói ngôn ngữ để kiểm


# Mã theo idMso của Office (backend ghi trong step.guide); tên đã dò bằng UIA trên Excel 365 tiếng Anh
MENU_ITEMS = {
    "HideUnhideMenu": MenuItem("FormatCellsMenu", ("Hide & Unhide",)),
    "ColumnsHide": MenuItem("HideUnhideMenu", ("Hide Columns",)),
    "ColumnsUnhide": MenuItem("HideUnhideMenu", ("Unhide Columns",)),
    "RowsHide": MenuItem("HideUnhideMenu", ("Hide Rows",)),
    "RowsUnhide": MenuItem("HideUnhideMenu", ("Unhide Rows",)),
    "ColumnWidth": MenuItem("FormatCellsMenu", ("Column Width",)),
    "RowHeight": MenuItem("FormatCellsMenu", ("Row Height",)),
    "SheetColumnsInsert": MenuItem("InsertCellstMenu_Dropdown", ("Insert Sheet Columns",)),
    "SheetRowsInsert": MenuItem("InsertCellstMenu_Dropdown", ("Insert Sheet Rows",)),
    "SheetColumnsDelete": MenuItem("TableDeleteRowsAndColumnsMenu_Dropdown", ("Delete Sheet Columns",)),
    "SheetRowsDelete": MenuItem("TableDeleteRowsAndColumnsMenu_Dropdown", ("Delete Sheet Rows",)),
}


def menu_name(text: str) -> str:
    """Tên mục menu để so: bỏ dấu ba chấm (Column Width...), khoảng trắng thừa, không phân biệt hoa thường."""
    return " ".join(text.replace("…", "").rstrip(".").split()).casefold()


class ExcelBusyError(RuntimeError):
    """Excel từ chối lệnh nhiều lần liền (học viên đang gõ trong ô hoặc đang mở hộp thoại)."""


class WorkbookClosedError(RuntimeError):
    """File chạy thử đã bị đóng trong Excel."""


def is_busy_error(exc: BaseException) -> bool:
    if isinstance(exc, pywintypes.com_error):
        return exc.hresult in BUSY_CODES
    return isinstance(exc, AttributeError)


def call_with_retry[T](
    fn: Callable[[], T], attempts: int = BUSY_ATTEMPTS, delay: float = BUSY_DELAY_SECONDS
) -> T:
    """Gọi COM; Excel bận thì thử lại có giới hạn rồi bỏ lượt này (không vòng lặp vô hạn)."""
    for _ in range(attempts):
        try:
            return fn()
        except (pywintypes.com_error, AttributeError) as exc:
            if not is_busy_error(exc):
                raise
            time.sleep(delay)
    raise ExcelBusyError("Excel đang bận")


def is_excel_busy(excel: Com) -> bool:
    """Excel đang sửa ô hoặc mở hộp thoại: lúc đó không chen đọc định dạng, không hiện gợi ý (T2.2)."""
    try:
        excel.CommandBars._oleobj_.GetIDsOfNames("GetPressedMso")
    except pywintypes.com_error as exc:
        return exc.hresult in BUSY_CODES
    except AttributeError:
        return True
    return False


def attach_or_start_excel() -> Com:
    """Excel đang chạy của người dùng; chưa chạy thì mở Excel (hiện ra như người dùng tự mở)."""
    try:
        return win32com.client.GetActiveObject("Excel.Application")
    except pywintypes.com_error:
        excel = win32com.client.Dispatch("Excel.Application")
        excel.Visible = True
        return excel


class ExcelLink:
    """Một file đang mở trong Excel để chạy thử. `excel_factory` cho test đưa phiên Excel riêng vào."""

    def __init__(self, path: Path, excel_factory: Callable[[], Com] = attach_or_start_excel) -> None:
        self.path = path.resolve()
        self._factory = excel_factory
        self.excel: Com = None
        self.workbook: Com = None
        self._window: auto.Control | None = None
        self._grid: auto.Control | None = None
        self._ribbon: dict[str, auto.Control] = {}  # nút Ribbon đã tìm thấy (tìm lại cả cây mất ~100 ms)

    # ------------------------------------------------------------ mở, kiểm còn mở
    def open(self) -> None:
        self.excel = self._factory()
        self.workbook = call_with_retry(self._find_open, OPEN_ATTEMPTS) or call_with_retry(
            lambda: self.excel.Workbooks.Open(str(self.path)), OPEN_ATTEMPTS
        )
        call_with_retry(self.workbook.Activate, OPEN_ATTEMPTS)

    def _find_open(self) -> Com:
        for index in range(1, self.excel.Workbooks.Count + 1):
            workbook = self.excel.Workbooks(index)
            if Path(str(workbook.FullName)).resolve() == self.path:
                return workbook
        return None

    def ensure_open(self) -> None:
        """Ném WorkbookClosedError nếu file đã bị đóng (hoặc Excel đã tắt). Excel bận thì coi như còn mở."""
        try:
            call_with_retry(lambda: self.workbook.Name)
        except ExcelBusyError:
            return
        except pywintypes.com_error as exc:
            raise WorkbookClosedError(str(self.path)) from exc

    def is_busy(self) -> bool:
        return is_excel_busy(self.excel)

    # ------------------------------------------------------------ đọc
    def snapshot(self, request: ReadRequest) -> WorkbookSnapshot:
        return call_with_retry(lambda: read_workbook_com(self.workbook, request))

    # ------------------------------------------------------------ tọa độ trên màn hình
    @property
    def hwnd(self) -> int:
        return int(self.excel.Hwnd)

    def is_foreground(self, own_pid: int) -> bool:
        """Excel (kể cả popup menu) hoặc ứng dụng gia sư đang ở trước: lúc đó mới vẽ khung chỉ dẫn."""
        foreground = win32gui.GetForegroundWindow()
        if not foreground:
            return False
        pid = win32process.GetWindowThreadProcessId(foreground)[1]
        excel_pid = win32process.GetWindowThreadProcessId(self.hwnd)[1]
        return pid in (excel_pid, own_pid)

    def selection(self, sheet: str | None) -> str | None:
        """Địa chỉ vùng đang chọn ("$D:$F", "$D:$E,$H:$H"); None nếu không ở file/sheet chạy thử."""
        excel = self.excel
        if excel.ActiveWorkbook is None or str(excel.ActiveWorkbook.FullName) != str(self.workbook.FullName):
            return None
        if sheet and str(excel.ActiveSheet.Name) != sheet:
            return None
        return str(excel.ActiveWindow.RangeSelection.Address)

    def _uia_grid(self) -> auto.Control | None:
        if self._grid is None:
            grid = self._uia_window().DataGridControl(searchDepth=UIA_SEARCH_DEPTH, AutomationId="Grid")
            if not grid.Exists(0, 0):
                return None
            self._grid = grid
        return self._grid

    def header_rect(self, names: Sequence[str]) -> Rect | None:
        """Khung bao các ô tiêu đề cột ("D", "F") hoặc dòng ("5") đang hiện; cột ẩn, cột khuất thì bỏ qua."""
        grid = self._uia_grid()
        if grid is None:
            return None
        rects = []
        try:
            for name in names:
                item = grid.DataItemControl(searchDepth=1, Name=name)
                if item.Exists(0, 0):
                    r = item.BoundingRectangle
                    if r.width() > 0 and r.height() > 0:
                        rects.append((r.left, r.top, r.right, r.bottom))
        except UIA_ERRORS:
            self._grid = None  # lưới vẽ lại (đổi sheet, cuộn): tìm lại lần sau
            return None
        if not rects:
            return None
        return (
            min(r[0] for r in rects),
            min(r[1] for r in rects),
            max(r[2] for r in rects),
            max(r[3] for r in rects),
        )

    def _ribbon_control(self, automation_id: str) -> auto.Control | None:
        control = self._ribbon.get(automation_id)
        if control is None:
            control = self._uia_window().Control(searchDepth=UIA_SEARCH_DEPTH, AutomationId=automation_id)
            if not control.Exists(0, 0):
                return None
            self._ribbon[automation_id] = control
        return control

    def _expanded(self, control: auto.Control) -> bool:
        pattern = control.GetPattern(auto.PatternId.ExpandCollapsePattern)
        return pattern is not None and pattern.ExpandCollapseState == EXPANDED

    def _menu_element(self, key: str) -> auto.Control | None:
        """Mục menu đang hiện (menu cha đang mở); chưa mở thì None."""
        item = MENU_ITEMS[key]
        parent = (
            self._menu_element(item.parent)
            if item.parent in MENU_ITEMS
            else self._ribbon_control(item.parent)
        )
        if parent is None or not self._expanded(parent):
            return None
        wanted = {menu_name(n) for n in item.names}

        def compare(control: auto.Control, _depth: int) -> bool:
            return control.ControlTypeName == "MenuItemControl" and menu_name(control.Name) in wanted

        # Menu của nút Format nằm ngay dưới nút; menu của mũi tên Insert/Delete nằm dưới nút tách cha
        for root in (parent, parent.GetParentControl()):
            if root is None:
                continue
            found = root.Control(searchDepth=MENU_SEARCH_DEPTH, Compare=compare)
            if found.Exists(0, 0):
                return found
        return None

    def ui_target(self, control: str, tab: str | None) -> tuple[Rect, str] | None:
        """Nút Ribbon hoặc mục menu thả xuống: (vùng, "control" | "tab"). Mục menu chỉ có khi menu đang mở."""
        try:
            if control in MENU_ITEMS:
                element = self._menu_element(control)
                if element is None:
                    return None
                r = element.BoundingRectangle
                return ((r.left, r.top, r.right, r.bottom), "control") if r.width() > 0 else None
            return self.ribbon_rect(control, tab)
        except UIA_ERRORS:
            self._ribbon.clear()  # Ribbon vẽ lại (đổi thẻ, đổi cỡ cửa sổ): tìm lại lần sau
            return None

    def _uia_window(self) -> auto.Control:
        if self._window is None:
            self._window = auto.ControlFromHandle(self.hwnd)
        return self._window

    def cell_rect(self, address: str, sheet: str | None) -> Rect | None:
        """Vùng ô trên màn hình; None nếu không ở sheet đang mở hoặc không hiện trong cửa sổ."""
        excel = self.excel
        if self.excel.ActiveWorkbook is None or str(excel.ActiveWorkbook.FullName) != str(
            self.workbook.FullName
        ):
            return None
        if sheet and str(excel.ActiveSheet.Name) != sheet:
            return None
        visible = excel.Intersect(excel.ActiveSheet.Range(address), excel.ActiveWindow.VisibleRange)
        if visible is None:
            return None
        if ctypes.windll.user32.GetDpiForWindow(self.hwnd) == ctypes.windll.user32.GetDpiForSystem():
            pane = excel.ActiveWindow.ActivePane
            return (
                int(pane.PointsToScreenPixelsX(visible.Left)),
                int(pane.PointsToScreenPixelsY(visible.Top)),
                int(pane.PointsToScreenPixelsX(visible.Left + visible.Width)),
                int(pane.PointsToScreenPixelsY(visible.Top + visible.Height)),
            )
        # Màn hình khác DPI hệ thống: COM lệch không theo tỉ lệ (T2.5) → UIA ô đầu và ô cuối đang hiện
        first = str(visible.Cells(1, 1).Address).replace("$", "")
        last = str(visible.Cells(visible.Rows.Count, visible.Columns.Count).Address).replace("$", "")
        r1, r2 = self._uia_cell(first), self._uia_cell(last)
        return (r1[0], r1[1], r2[2], r2[3]) if r1 and r2 else None

    def _uia_cell(self, address: str) -> Rect | None:
        item = self._uia_window().DataItemControl(searchDepth=UIA_SEARCH_DEPTH, Name=address)
        if not item.Exists(0, 0):
            return None
        r = item.BoundingRectangle
        return r.left, r.top, r.right, r.bottom

    def ribbon_rect(self, control: str, tab: str | None) -> tuple[Rect, str] | None:
        """(vùng, "control" | "tab"). Nút chưa hiện (đang chọn thẻ khác) thì chỉ vào thẻ (T2.7, QĐ 5)."""
        for automation_id, kind in ((control, "control"), (tab, "tab")):
            if not automation_id:
                continue
            try:
                found = self._ribbon_control(automation_id)
                r = found.BoundingRectangle if found is not None else None
            except UIA_ERRORS:
                self._ribbon.pop(automation_id, None)  # nút đã lưu bị Ribbon vẽ lại: tìm lại lần sau
                continue
            if r is not None and r.width() > 0 and r.height() > 0:
                return (r.left, r.top, r.right, r.bottom), kind
        return None


def pump_messages() -> None:
    """Cho sự kiện COM (SheetChange…) được giao tới luồng này."""
    pythoncom.PumpWaitingMessages()
