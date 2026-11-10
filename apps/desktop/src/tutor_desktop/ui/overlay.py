"""Khung chỉ vị trí vẽ đè lên Excel (T7.7, theo spike T2.5).

Mỗi màn hình một cửa sổ trong suốt, luôn trên cùng, chuột bấm xuyên qua, không giành focus của Excel.

Popup menu của Office (Format, Hide & Unhide…) cũng là cửa sổ luôn trên cùng, mở sau nên nằm trên
overlay và che khung chỉ mục trong menu. Vì vậy overlay đang hiện được đẩy lên đầu lớp luôn-trên-cùng mỗi khi
khung đổi và đều đặn mỗi RAISE_MS (SetWindowPos HWND_TOPMOST, không kích hoạt: menu không đóng, focus không
đổi).

Tọa độ nhận vào là pixel vật lý (từ COM/UIA); Qt vẽ theo pixel logic của TỪNG màn hình: logic = (vật lý - gốc
vật lý của màn hình) / devicePixelRatio của màn hình đó (quy tắc code 2.3 mục 12).
"""

import ctypes
import logging
from dataclasses import dataclass

import win32api
import win32con
import win32gui
from PyQt6.QtCore import QRect, Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QPainter, QPaintEvent, QPen, QScreen
from PyQt6.QtWidgets import QApplication, QWidget

from tutor_desktop.monitor.watcher import MarkRect

logger = logging.getLogger(__name__)

COLORS = {
    "target": QColor("#1f5fa8"),  # học viên làm ở đây
    "source": QColor("#1d6f42"),  # dữ liệu nguồn
    "location": QColor("#e8590c"),  # gợi ý cấp 3: chỉ vị trí
    "tab": QColor("#e8590c"),
}
PEN_WIDTH = 3
RAISE_MS = 250  # đẩy overlay lên trên popup menu vừa mở (nhanh hơn nhịp tính khung 300 ms)
_RAISE_FLAGS = (
    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE | win32con.SWP_NOOWNERZORDER
)
LABEL_HEIGHT = 20
LABEL_CHAR_PX = 7


@dataclass
class _Box:
    rect: QRect
    label: str
    color: QColor
    dashed: bool


class _Overlay(QWidget):
    def __init__(self, screen: QScreen) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setScreen(screen)
        self.setGeometry(screen.geometry())
        self.boxes: list[_Box] = []

    def raise_to_top(self) -> None:
        """Lên đầu lớp cửa sổ luôn-trên-cùng (trên popup menu của Excel), không kích hoạt."""
        try:
            win32gui.SetWindowPos(int(self.winId()), win32con.HWND_TOPMOST, 0, 0, 0, 0, _RAISE_FLAGS)
        except win32gui.error:
            logger.debug("Không đẩy được overlay lên trên", exc_info=True)

    def paintEvent(self, _event: QPaintEvent | None) -> None:  # noqa: N802 — tên do Qt quy định
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        for box in self.boxes:
            pen = QPen(box.color, PEN_WIDTH)
            if box.dashed:
                pen.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.drawRect(box.rect.adjusted(-2, -2, 2, 2))
            width = len(box.label) * LABEL_CHAR_PX + 12
            top = box.rect.top() - LABEL_HEIGHT - 4
            painter.fillRect(box.rect.left() - 2, top, width, LABEL_HEIGHT, box.color)
            painter.setPen(QColor("white"))
            painter.drawText(box.rect.left() + 4, top + LABEL_HEIGHT - 6, box.label)


@dataclass
class _Monitor:
    device: str
    origin: tuple[int, int]
    dpr: float
    overlay: _Overlay


def _monitor_dpi(handle: object) -> int:
    dpi_x, dpi_y = ctypes.c_uint(), ctypes.c_uint()
    ctypes.windll.shcore.GetDpiForMonitor(int(handle), 0, ctypes.byref(dpi_x), ctypes.byref(dpi_y))  # type: ignore[arg-type]
    return dpi_x.value


class OverlayManager:
    """Ghép màn hình Windows với QScreen của Qt (theo kích thước vật lý và tỉ lệ, không theo tên: T2.5)."""

    def __init__(self, app: QApplication) -> None:
        self.monitors: list[_Monitor] = []
        self._timer = QTimer()
        self._timer.setInterval(RAISE_MS)
        self._timer.timeout.connect(self.raise_to_top)
        screens = list(app.screens())
        for handle, _, _ in win32api.EnumDisplayMonitors():
            info = win32api.GetMonitorInfo(handle)
            x1, y1, x2, y2 = info["Monitor"]
            dpr = _monitor_dpi(handle) / 96

            def fits(screen: QScreen, w: int = x2 - x1, h: int = y2 - y1, dpr: float = dpr) -> bool:
                g = screen.geometry()
                ratio = screen.devicePixelRatio()
                return (
                    abs(ratio - dpr) < 0.01
                    and abs(g.width() * ratio - w) <= 2
                    and abs(g.height() * ratio - h) <= 2
                )  # noqa: PLR2004

            match = next((s for s in screens if fits(s)), None)
            if match is None:
                logger.warning("Không ghép được màn hình %s với QScreen nào", info["Device"])
                continue
            screens.remove(match)
            self.monitors.append(
                _Monitor(info["Device"], (x1, y1), match.devicePixelRatio(), _Overlay(match))
            )

    def _monitor_at(self, x: int, y: int) -> _Monitor | None:
        handle = win32api.MonitorFromPoint((x, y), win32con.MONITOR_DEFAULTTONEAREST)
        device = win32api.GetMonitorInfo(handle)["Device"]
        return next((m for m in self.monitors if m.device == device), None)

    def show(self, marks: list[MarkRect]) -> None:
        per_monitor: dict[str, list[_Box]] = {m.device: [] for m in self.monitors}
        for mark in marks:
            x1, y1, x2, y2 = mark.rect
            monitor = self._monitor_at((x1 + x2) // 2, (y1 + y2) // 2)
            if monitor is None:
                continue
            ox, oy = monitor.origin
            d = monitor.dpr
            rect = QRect(
                round((x1 - ox) / d), round((y1 - oy) / d), round((x2 - x1) / d), round((y2 - y1) / d)
            )
            color = COLORS.get(mark.role, COLORS["target"])
            per_monitor[monitor.device].append(_Box(rect, mark.label, color, mark.role == "source"))
        for monitor in self.monitors:
            monitor.overlay.boxes = per_monitor[monitor.device]
            if monitor.overlay.boxes:
                monitor.overlay.show()
                monitor.overlay.raise_to_top()
                monitor.overlay.update()
            else:
                monitor.overlay.hide()
        if any(m.overlay.boxes for m in self.monitors):
            self._timer.start()
        else:
            self._timer.stop()

    def raise_to_top(self) -> None:
        for monitor in self.monitors:
            if monitor.overlay.isVisible():
                monitor.overlay.raise_to_top()

    def hide(self) -> None:
        self.show([])
