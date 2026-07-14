from PySide6.QtCore import Qt
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

        # ------------------------------------------
        # メインレイアウト
        # ------------------------------------------
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignRight)

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

        layout.addWidget(title_label)
        layout.addLayout(number_layout)

        # ------------------------------------------
        # サイズ固定
        # ------------------------------------------
        self.setFixedWidth(180)
        self.setFixedHeight(90)


    # ------------------------------------------
    # 人数更新
    # ------------------------------------------
    def update_count(self, count: int):
        self.count_label.setText(f"{count}")

