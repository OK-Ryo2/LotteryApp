from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QSizePolicy, QVBoxLayout


class DrawStatus(QFrame):
    """賞品とルーレットの間に表示する抽選状態。"""

    def __init__(self):
        super().__init__()
        self.setObjectName("drawStatus")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._base_minimum_height: int | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self.label = QLabel("抽選待機中")
        self.label.setObjectName("drawStatusLabel")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)

    def set_waiting(self):
        self.label.setText("抽選待機中")

    def set_spinning(self, participant: dict[str, str]):
        self.label.setText(f"抽選中・・・\n{participant['name']} さん")

    def set_completed(self):
        self.label.setText("この賞品は抽選済みです")

    def clear_status(self):
        self.label.clear()

    def set_scale(self, scale: float):
        if self._base_minimum_height is None:
            self.ensurePolished()
            self._base_minimum_height = self.minimumHeight()
        self.setMinimumHeight(max(56, round(self._base_minimum_height * scale)))
