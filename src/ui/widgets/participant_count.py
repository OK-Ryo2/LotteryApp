from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QHBoxLayout,
    QVBoxLayout,
)


# ==========================================
# 参加人数表示Widget
#
# 右上に表示する参加人数
#
# ┌─────────────┐
# │ 参加人数    │
# │             │
# │   94 名     │
# └─────────────┘
#
# 将来的にはJSON読込後に
# 人数を更新する予定
# ==========================================
class ParticipantCount(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setObjectName("participantCount")
        self._base_size: tuple[int, int] | None = None

        # ------------------------------------------
        # メインレイアウト
        # ------------------------------------------
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        layout.setAlignment(Qt.AlignCenter)

        self.setLayout(layout)

        # ------------------------------------------
        # タイトル
        # ------------------------------------------
        title_label = QLabel("参加人数")
        title_label.setObjectName("participantTitle")
        title_label.setAlignment(Qt.AlignCenter)

        # ------------------------------------------
        # 人数（数のみ）
        # ------------------------------------------
        self.count_label = QLabel("94")
        self.count_label.setObjectName("participantNumber")
        self.count_label.setAlignment(Qt.AlignCenter)

        # ------------------------------------------
        # 人数単位（名）
        # ------------------------------------------
        self.unit_label = QLabel("名")
        self.unit_label.setObjectName("participantUnit")
        self.unit_label.setAlignment(Qt.AlignCenter)

        number_layout = QHBoxLayout()
        number_layout.setAlignment(Qt.AlignCenter)
        number_layout.setSpacing(5)

        number_layout.addWidget(self.count_label)
        number_layout.addWidget(self.unit_label)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(0)
        text_layout.addWidget(title_label)
        text_layout.addLayout(number_layout)

        self.icon_label = QLabel()
        self.icon_label.setObjectName("participantIcon")
        self.icon_label.setAlignment(Qt.AlignCenter)
        self._icon_pixmap = QPixmap(
            str(
                Path(__file__).resolve().parents[3]
                / "assets"
                / "images"
                / "icons"
                / "icon_people.png"
            )
        )

        layout.addWidget(self.icon_label)
        layout.addLayout(text_layout)

        # ------------------------------------------
        # サイズ固定
        # ------------------------------------------
        self.set_scale(1.0)


    # ------------------------------------------
    # 人数更新
    # ------------------------------------------
    def update_count(self, count: int):
        self.count_label.setText(f"{count}")

    def set_scale(self, scale: float):
        """画面の表示倍率に合わせて枠と人数アイコンを調整する。"""
        if self._base_size is None:
            self.ensurePolished()
            self._base_size = (self.minimumWidth(), self.minimumHeight())
        width = max(120, round(self._base_size[0] * scale))
        height = max(72, round(self._base_size[1] * scale))
        icon_size = max(26, round(36 * scale))
        self.setFixedSize(width, height)
        if not self._icon_pixmap.isNull():
            self.icon_label.setPixmap(
                self._icon_pixmap.scaled(
                    icon_size,
                    icon_size,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
            )
        self.icon_label.setFixedSize(icon_size, icon_size)

