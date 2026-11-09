"""Đăng nhập và chọn bản kịch bản để chạy thử (chế độ giảng viên)."""

from collections.abc import Mapping
from typing import Any

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
)

from tutor_desktop.api_client.client import ApiClient, ApiError

DEFAULT_SERVER = "http://127.0.0.1:8000"
STATUS_NAMES = {
    "draft": "nháp",
    "pending_review": "chờ duyệt",
    "approved": "đã duyệt",
    "published": "đang phát hành",
    "archived": "lưu trữ",
}
ORIGIN_NAMES = {"ai": "AI sinh", "teacher": "giảng viên viết", "ai_edited": "AI sinh, giảng viên sửa"}


class LoginDialog(QDialog):
    """Đăng nhập bằng tài khoản giảng viên của trang quản trị (nhớ địa chỉ máy chủ và email)."""

    def __init__(self, settings: QSettings) -> None:
        super().__init__()
        self.settings = settings
        self.client: ApiClient | None = None
        self.setWindowTitle("Gia sư Excel — đăng nhập để chạy thử")
        self.server = QLineEdit(str(settings.value("server", DEFAULT_SERVER)))
        self.email = QLineEdit(str(settings.value("email", "")))
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.error = QLabel()
        self.error.setStyleSheet("color: #b42318")
        self.error.setWordWrap(True)
        form = QFormLayout()
        form.addRow("Máy chủ", self.server)
        form.addRow("Email", self.email)
        form.addRow("Mật khẩu", self.password)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._login)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.error)
        layout.addWidget(buttons)
        (self.password if self.email.text() else self.email).setFocus()

    def _login(self) -> None:
        client = ApiClient(self.server.text().strip() or DEFAULT_SERVER)
        try:
            user = client.login(self.email.text().strip(), self.password.text())
        except ApiError as exc:
            self.error.setText(str(exc))
            return
        if user.get("role") not in ("admin", "teacher"):
            self.error.setText("Chế độ chạy thử dành cho giảng viên và quản trị viên.")
            return
        self.settings.setValue("server", client.base_url)
        self.settings.setValue("email", self.email.text().strip())
        self.client = client
        self.accept()


class PickerDialog(QDialog):
    """Chọn bài và bản kịch bản (mọi trạng thái, kể cả nháp)."""

    def __init__(self, client: ApiClient) -> None:
        super().__init__()
        self.client = client
        self.version: Mapping[str, Any] | None = None
        self.setWindowTitle("Chọn kịch bản để chạy thử")
        self.resize(520, 420)
        self.exercises = QComboBox()
        self.versions = QListWidget()
        self.error = QLabel()
        self.error.setStyleSheet("color: #b42318")
        self.error.setWordWrap(True)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        ok = buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok is not None:
            ok.setText("Chạy thử trên Excel")
        buttons.accepted.connect(self._choose)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Bài tập"))
        layout.addWidget(self.exercises)
        layout.addWidget(QLabel("Bản kịch bản"))
        layout.addWidget(self.versions)
        layout.addWidget(self.error)
        layout.addWidget(buttons)
        self.versions.itemDoubleClicked.connect(lambda _: self._choose())
        self.exercises.currentIndexChanged.connect(self._load_versions)
        try:
            for exercise in client.exercises():
                self.exercises.addItem(f"{exercise['title']} ({exercise['code']})", exercise["id"])
        except ApiError as exc:
            self.error.setText(str(exc))

    def _load_versions(self) -> None:
        self.versions.clear()
        exercise_id = self.exercises.currentData()
        if not exercise_id:
            return
        try:
            versions = self.client.script_versions(exercise_id)
        except ApiError as exc:
            self.error.setText(str(exc))
            return
        if not versions:
            self.error.setText("Bài này chưa có kịch bản: sinh kịch bản trên trang quản trị trước.")
        for version in versions:
            status = STATUS_NAMES.get(version["status"], version["status"])
            origin = ORIGIN_NAMES.get(version["origin"], version["origin"])
            item = QListWidgetItem(f"Bản {version['revision']} · {status} · {origin}")
            item.setData(256, version)  # Qt.ItemDataRole.UserRole
            self.versions.addItem(item)
        if versions:
            self.versions.setCurrentRow(0)

    def _choose(self) -> None:
        item = self.versions.currentItem()
        if item is None:
            self.error.setText("Chọn một bản kịch bản.")
            return
        self.version = item.data(256)
        self.accept()
