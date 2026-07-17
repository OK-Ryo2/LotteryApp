from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QStackedLayout,
    QVBoxLayout,
)


class CurrentPrize(QFrame):
    """中央パネルに現在抽選中の賞品を表示するWidget。"""

    def __init__(
        self,
        rank: str = "20等",
        prize_name: str = "Amaギフ 1000円分",
        remain: int = 7,
    ):
        super().__init__()

        self.setObjectName("currentPrize")
        self.setMinimumHeight(220)

        project_root = Path(__file__).resolve().parents[3]
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 0, 24, 20)
        main_layout.setSpacing(8)

        # 参考デザインのリボン見出しに相当する表示
        title_label = QLabel("現在の賞品")
        title_label.setObjectName("currentPrizeTitle")
        title_label.setAlignment(Qt.AlignCenter)
        # レイアウトの余剰高さで背景が縦に伸びないよう、1行分に固定する
        title_label.setFixedHeight(38)

        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.addStretch()
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        main_layout.addLayout(title_layout)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(28)

        # 左：翼画像の中央に等級を重ねて表示
        rank_frame = QFrame()

        wing_label = QLabel()
        wing_label.setObjectName("currentPrizeWing")
        wing_pixmap = QPixmap(
            str(project_root / "assets" / "images" / "ui" / "wing.png")
        )
        display_wing_pixmap = wing_pixmap.scaledToWidth(
            max(1, wing_pixmap.width() // 2), Qt.SmoothTransformation
        )
        wing_label.setPixmap(display_wing_pixmap)
        wing_label.setAlignment(Qt.AlignCenter)

        self.rank_label = QLabel()
        self.rank_label.setObjectName("currentPrizeRank")
        self.rank_label.setAlignment(Qt.AlignCenter)

        rank_frame.setFixedSize(display_wing_pixmap.size())
        rank_layout = QStackedLayout(rank_frame)
        rank_layout.setStackingMode(QStackedLayout.StackAll)
        rank_layout.setContentsMargins(0, 0, 0, 0)
        rank_layout.addWidget(wing_label)
        rank_layout.addWidget(self.rank_label)

        # 右：賞品名と残数
        info_layout = QVBoxLayout()
        info_layout.setAlignment(Qt.AlignCenter)
        info_layout.setSpacing(12)

        self.prize_name_label = QLabel()
        self.prize_name_label.setObjectName("currentPrizeName")
        self.prize_name_label.setAlignment(Qt.AlignCenter)
        self.prize_name_label.setWordWrap(True)

        self.remain_label = QLabel()
        self.remain_label.setObjectName("currentPrizeRemain")
        self.remain_label.setAlignment(Qt.AlignCenter)

        info_layout.addWidget(self.prize_name_label)
        info_layout.addWidget(self.remain_label)

        content_layout.addStretch()
        content_layout.addWidget(rank_frame)
        content_layout.addSpacing(28)
        content_layout.addLayout(info_layout)
        content_layout.addStretch()
        main_layout.addLayout(content_layout)

        self.update_prize(rank, prize_name, remain)

    def update_prize(
        self,
        rank: str,
        prize_name: str,
        remain: int,
    ):
        """現在の賞品表示を更新する。"""
        self.rank_label.setText(rank)
        self.prize_name_label.setText(prize_name)
        self.remain_label.setText(f"残り {remain}名")
