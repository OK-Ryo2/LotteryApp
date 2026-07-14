from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
)


# ==========================================
# 賞品カードWidget
# （等級・賞品画像・賞品名・残り人数・抽選状態を表示）
# ==========================================
class PrizeCard(QFrame):
    def __init__(self):
        super().__init__()

        self.setObjectName("prizeCard")

        # ------------------------------------------
        # メインレイアウト（横並び）
        # ------------------------------------------
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(20)
        self.setLayout(main_layout)

        # プロジェクトルート
        project_root = Path(__file__).resolve().parents[3]

        # ==========================================
        # 左：等級エリア
        # ==========================================
        rank_layout = QVBoxLayout()
        rank_layout.setAlignment(Qt.AlignCenter)
        rank_layout.setSpacing(8)

        wing_label = QLabel()
        wing_pixmap = QPixmap(
            str(project_root / "assets" / "images" / "ui" / "wing.png")
        )
        wing_label.setPixmap(wing_pixmap)
        wing_label.setAlignment(Qt.AlignCenter | Qt.AlignTop)

        rank_label = QLabel("20等")
        rank_label.setObjectName("rankLabel")
        rank_label.setAlignment(Qt.AlignCenter)

        rank_layout.addWidget(wing_label)
        rank_layout.addWidget(rank_label)

        # 最後に文字を前面へ
        rank_label.raise_()

        # ==========================================
        # 中央左：商品画像エリア
        # ==========================================
        image_layout = QVBoxLayout()
        image_layout.setAlignment(Qt.AlignCenter)

        image_label = QLabel()

        prize_pixmap = QPixmap(
            str(
                project_root
                / "assets"
                / "images"
                / "prizes"
                / "amazongift.png"
            )
        )

        image_label.setPixmap(prize_pixmap)
        image_label.setAlignment(Qt.AlignCenter)

        image_layout.addWidget(image_label)

        # ==========================================
        # 中央右：賞品情報エリア
        # ==========================================
        info_layout = QVBoxLayout()
        info_layout.setAlignment(Qt.AlignVCenter)
        info_layout.setSpacing(8)

        prize_label = QLabel("Amaギフ 1000円分")
        prize_label.setObjectName("prizeLabel")
        prize_label.setWordWrap(True)

        remain_label = QLabel("残り 7名")
        remain_label.setObjectName("remainLabel")

        info_layout.addWidget(prize_label)
        info_layout.addWidget(remain_label)

        # ==========================================
        # 右：状態表示エリア
        # ==========================================
        status_layout = QVBoxLayout()
        status_layout.setAlignment(Qt.AlignCenter)

        status_label = QLabel("抽選済み")
        status_label.setObjectName("statusLabel")
        status_label.setAlignment(Qt.AlignCenter)

        status_layout.addWidget(status_label)

        # ==========================================
        # 各エリアを配置
        # ==========================================
        main_layout.addLayout(rank_layout)
        main_layout.addLayout(image_layout)
        main_layout.addLayout(info_layout, 1)
        main_layout.addLayout(status_layout)