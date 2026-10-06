from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QTransform
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QStackedLayout,
    QSizePolicy,
    QVBoxLayout,
)


class CurrentPrize(QFrame):
    """中央パネルに現在選択中の賞品を表示するウィジェット。"""

    def __init__(
        self,
        rank: str = "20等",
        prize_name: str = "Amaギフ 1000円分",
        remain: int = 7,
    ):
        super().__init__()

        self.setObjectName("currentPrize")
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self._base_minimum_height: int | None = None

        project_root = Path(__file__).resolve().parents[3]
        main_layout = QVBoxLayout(self)
        # 子要素の配置間隔はQLayoutで管理し、見た目の余白・装飾はQSSで管理する。
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(2)

        # 中央パネル上端に重なるリボン見出し。
        self._ribbon_pixmap = QPixmap(
            str(project_root / "assets" / "images" / "ui" / "ribbon.png")
        )
        self._title_frame = QFrame()
        # 見出し文字とリボン端が重ならないよう、文字列より十分広く取る。
        self._title_frame.setFixedSize(270, 52)
        title_stack = QStackedLayout(self._title_frame)
        title_stack.setStackingMode(QStackedLayout.StackAll)
        title_stack.setContentsMargins(0, 0, 0, 0)

        self._ribbon_label = QLabel()
        self._ribbon_label.setObjectName("currentPrizeRibbon")
        self._ribbon_label.setAlignment(Qt.AlignCenter)

        self._title_label = QLabel("現在の賞品")
        self._title_label.setObjectName("currentPrizeTitle")
        # リボンの上端から文字列を描画する。
        self._title_label.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        title_stack.addWidget(self._ribbon_label)
        title_stack.addWidget(self._title_label)
        self._ribbon_label.lower()
        self._title_label.raise_()

        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.addStretch()
        title_layout.addWidget(self._title_frame)
        title_layout.addStretch()
        main_layout.addLayout(title_layout)

        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        content_layout.setAlignment(Qt.AlignCenter)

        # wing.png は使わず、等級と賞品情報を左右の金色の羽飾りで囲む。
        self._gold_wing_pixmap = QPixmap(
            str(project_root / "assets" / "images" / "ui" / "gold_wing.png")
        )
        self._gold_wing_flipped_pixmap = self._gold_wing_pixmap.transformed(
            QTransform().scale(-1, 1),
            Qt.SmoothTransformation,
        )
        self._left_gold_wing = self._create_gold_wing_label()
        self._right_gold_wing = self._create_gold_wing_label()

        self._rank_frame = QFrame()
        rank_layout = QHBoxLayout(self._rank_frame)
        rank_layout.setContentsMargins(0, 0, 0, 0)
        rank_layout.setSpacing(2)
        rank_layout.setAlignment(Qt.AlignCenter)

        self.rank_number_label = QLabel()
        self.rank_number_label.setObjectName("currentPrizeRankNumber")
        self.rank_number_label.setAlignment(Qt.AlignCenter)

        self.rank_suffix_label = QLabel("等")
        self.rank_suffix_label.setObjectName("currentPrizeRankSuffix")
        self.rank_suffix_label.setAlignment(Qt.AlignCenter | Qt.AlignBottom)
        rank_layout.addWidget(self.rank_number_label)
        rank_layout.addWidget(self.rank_suffix_label)

        info_layout = QVBoxLayout()
        info_layout.setAlignment(Qt.AlignCenter)
        info_layout.setSpacing(4)

        self.prize_name_label = QLabel()
        self.prize_name_label.setObjectName("currentPrizeName")
        self.prize_name_label.setAlignment(Qt.AlignCenter)
        self.prize_name_label.setWordWrap(False)
        self.prize_name_label.setMinimumWidth(0)
        self.prize_name_label.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)

        self.remain_label = QLabel()
        self.remain_label.setObjectName("currentPrizeRemain")
        self.remain_label.setAlignment(Qt.AlignCenter)
        info_layout.addWidget(self.prize_name_label)
        info_layout.addWidget(self.remain_label)

        content_layout.addStretch()
        content_layout.addWidget(self._left_gold_wing)
        content_layout.addSpacing(18)
        content_layout.addWidget(self._rank_frame)
        content_layout.addSpacing(6)
        content_layout.addLayout(info_layout)
        content_layout.addSpacing(18)
        content_layout.addWidget(self._right_gold_wing)
        content_layout.addStretch()
        main_layout.addLayout(content_layout)

        self._set_gold_wing_size(76)
        self._update_ribbon()
        self.update_prize(rank, prize_name, 0, remain)

    def _create_gold_wing_label(self) -> QLabel:
        label = QLabel()
        label.setObjectName("currentPrizeGoldWing")
        label.setAlignment(Qt.AlignCenter)
        return label

    def _set_gold_wing_size(self, height: int):
        """賞品名・抽選済み表示と同じ高さで左右の羽を描画する。"""
        height = max(42, height)
        for label, pixmap_source in (
            (self._left_gold_wing, self._gold_wing_pixmap),
            (self._right_gold_wing, self._gold_wing_flipped_pixmap),
        ):
            if pixmap_source.isNull():
                continue
            pixmap = pixmap_source.scaledToHeight(height, Qt.SmoothTransformation)
            label.setFixedSize(pixmap.size())
            label.setPixmap(pixmap)

    def _update_ribbon(self):
        if not self._ribbon_pixmap.isNull():
            self._ribbon_label.setPixmap(
                self._ribbon_pixmap.scaled(
                    self._title_frame.size(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
            )

    def set_scale(self, scale: float):
        """画面の表示倍率に合わせて賞品情報と装飾を調整する。"""
        if self._base_minimum_height is None:
            self.ensurePolished()
            self._base_minimum_height = self.minimumHeight()
        self._set_gold_wing_size(round(76 * scale))
        title_width = max(190, round(270 * scale))
        title_height = max(34, round(46 * scale))
        self._title_frame.setFixedSize(title_width, title_height)
        self._update_ribbon()
        self.setMinimumHeight(max(100, round(self._base_minimum_height * scale)))

    def update_prize(
        self,
        rank: str,
        prize_name: str,
        drawn_count: int,
        total_count: int,
    ):
        """現在の賞品表示を更新する。"""
        self.rank_number_label.setText(rank.removesuffix("等"))
        self.prize_name_label.setText(prize_name)
        self.remain_label.setText(f"{drawn_count}/{total_count}　抽選済")
