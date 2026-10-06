from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QStackedLayout,
    QVBoxLayout,
)


# ==========================================
# 賞品カードWidget
# （等級・賞品画像・賞品名・残り人数・抽選状態を表示）
# ==========================================
class PrizeCard(QFrame):
    def __init__(
        self,
        rank: str = "20等",
        prize_name: str = "Amaギフ 1000円分",
        remain: int = 7,
        status: str = "抽選中",
        image_path: str | Path | None = None,
    ):
        super().__init__()

        self.setObjectName("prizeCard")
        self._project_root = Path(__file__).resolve().parents[3]
        self._actual_name = prize_name
        self._actual_image_path = image_path
        self._revealed = True

        # ------------------------------------------
        # メインレイアウト（横並び）
        # ------------------------------------------
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(10)
        self.setLayout(main_layout)

        # プロジェクトルート
        # ==========================================
        # 左：等級エリア
        # ==========================================
        rank_layout = QVBoxLayout()
        rank_layout.setAlignment(Qt.AlignCenter)
        rank_layout.setSpacing(8)

        wing_label = QLabel()
        wing_pixmap = self._load_rank_pixmap(rank)
        # 等級文字が画像の内側に収まるよう、従来の約1.15倍で表示する。
        display_wing_pixmap = wing_pixmap.scaledToWidth(
            max(1, round(wing_pixmap.width() * 0.58)), Qt.SmoothTransformation
        )
        wing_label.setPixmap(display_wing_pixmap)
        wing_label.setAlignment(Qt.AlignCenter | Qt.AlignTop)

        rank_text = rank.removesuffix("等")
        try:
            rank_number = int("".join(char for char in rank if char.isdigit()))
        except ValueError:
            rank_number = 20
        rank_text_layout = QHBoxLayout()
        rank_text_layout.setContentsMargins(0, 0, 0, 0)
        rank_text_layout.setSpacing(1)
        rank_text_layout.setAlignment(Qt.AlignCenter)

        self.rank_number_label = QLabel(rank_text)
        self.rank_number_label.setObjectName("rankNumber")
        self.rank_number_label.setAlignment(Qt.AlignCenter)

        self.rank_suffix_label = QLabel("等")
        self.rank_suffix_label.setObjectName("rankSuffix")
        self.rank_suffix_label.setAlignment(Qt.AlignCenter | Qt.AlignBottom)

        rank_text_layout.addWidget(self.rank_number_label)
        rank_text_layout.addWidget(self.rank_suffix_label)

        rank_text_frame = QFrame()
        rank_text_frame.setLayout(rank_text_layout)
        if rank_number >= 4:
            # 4～20等の画像は上部の装飾が少ないため、文字を少し上へ補正する。
            shift = max(2, round(display_wing_pixmap.height() * 0.08))
            rank_text_frame.setContentsMargins(0, 0, 0, shift * 2)

        rank_frame = QFrame()
        rank_frame.setFixedSize(display_wing_pixmap.size())
        rank_stack = QStackedLayout(rank_frame)
        rank_stack.setStackingMode(QStackedLayout.StackAll)
        rank_stack.setContentsMargins(0, 0, 0, 0)
        rank_stack.addWidget(wing_label)
        rank_stack.addWidget(rank_text_frame)

        rank_layout.addWidget(rank_frame)

        # 等級ラベルをwing画像より前面へ固定する
        wing_label.lower()
        rank_text_frame.raise_()

        # ==========================================
        # 中央左：賞品画像エリア
        # ==========================================
        image_label = QLabel()
        image_label.setObjectName("prizeImage")
        image_label.setFixedSize(64, 64)
        image_label.setAlignment(Qt.AlignCenter)

        self.image_label = image_label
        self._set_image(image_path)

        # ==========================================
        # 右：賞品情報エリア
        # ==========================================
        info_layout = QVBoxLayout()
        info_layout.setAlignment(Qt.AlignVCenter)
        info_layout.setSpacing(8)

        self.prize_label = QLabel(prize_name)
        self.prize_label.setObjectName("prizeLabel")
        self.prize_label.setWordWrap(True)

        self.remain_label = QLabel(f"{remain}名様")
        self.remain_label.setObjectName("remainLabel")

        info_layout.addWidget(self.prize_label)
        info_layout.addWidget(self.remain_label)

        # ==========================================
        # 右：状態表示エリア
        # ==========================================
        status_layout = QVBoxLayout()
        status_layout.setAlignment(Qt.AlignCenter)

        self.status_label = QLabel(status)
        self.status_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        # バッジの上下余白は QSS の padding に依存させず、ラベルの高さで確保する。
        self.status_label.setMinimumHeight(16)
        self._set_status_style(status)

        status_layout.addWidget(self.status_label)
        status_layout.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # ==========================================
        # 各エリアを配置
        # ==========================================
        main_layout.addLayout(rank_layout)
        main_layout.addWidget(image_label)
        main_layout.addLayout(info_layout)
        main_layout.addStretch()
        main_layout.addLayout(status_layout)

    def update_prize(self, rank: str, prize_name: str, total_count: int, status: str):
        """景品の合計個数と抽選状態を更新する。"""
        self.rank_number_label.setText(rank.removesuffix("等"))
        self._actual_name = prize_name
        self.prize_label.setText(prize_name if self._revealed else "???")
        self.remain_label.setText(f"{total_count}名様")
        self._set_status(status if self._revealed else "公開前🔒")

    def set_revealed(self, revealed: bool, status: str = "未抽選"):
        """公開前は画像・景品名・状態をマスクし、公開時に実データへ戻す。"""
        self._revealed = revealed
        if revealed:
            self.prize_label.setText(self._actual_name)
            self._set_image(self._actual_image_path)
            self._set_status(status)
            return

        self.prize_label.setText("???")
        self._set_image(self._project_root / "assets" / "images" / "ui" / "lock.png")
        self._set_status("公開前🔒")
        self.set_active(False)

    def set_active(self, active: bool):
        """抽選中の賞品だけを金枠で強調表示する。"""
        self.setObjectName("prizeCardActive" if active else "prizeCard")
        self.style().unpolish(self)
        self.style().polish(self)

    def _set_status_style(self, status: str):
        """抽選済みだけを強調バッジとして表示する。"""
        object_name = "statusLabelCompleted" if status == "抽選済み" else "statusLabel"
        self.status_label.setObjectName(object_name)
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

    def _set_status(self, status: str):
        self.status_label.setText(status)
        self._set_status_style(status)

    def _set_image(self, image_path: str | Path | None):
        self.image_label.clear()
        if not image_path:
            return

        prize_pixmap = QPixmap(str(image_path))
        if not prize_pixmap.isNull():
            self.image_label.setPixmap(
                prize_pixmap.scaled(
                    self.image_label.size(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
            )

    def _load_rank_pixmap(self, rank: str) -> QPixmap:
        """等級に応じた背景画像を読み込み、画像の背景色を透明化する。"""
        try:
            rank_number = int("".join(char for char in rank if char.isdigit()))
        except ValueError:
            rank_number = 20

        if rank_number == 1:
            filename = "1tou.png"
        elif rank_number == 2:
            filename = "2tou.png"
        elif rank_number == 3:
            filename = "3tou.png"
        elif 4 <= rank_number <= 10:
            filename = "4-10.png"
        else:
            filename = "11-20.png"

        pixmap = QPixmap(
            str(self._project_root / "assets" / "images" / "ui" / "ranks" / filename)
        )
        if pixmap.isNull():
            return pixmap

        image = pixmap.toImage().convertToFormat(QImage.Format.Format_ARGB32)
        corner = image.pixelColor(0, 0)
        if corner.alpha() == 0:
            return pixmap

        # 四隅と同系色の背景だけを除去し、等級画像本体の色は残す。
        tolerance = 48
        for y in range(image.height()):
            for x in range(image.width()):
                color = image.pixelColor(x, y)
                if color.alpha() == 0:
                    continue
                distance = sum(
                    abs(channel - corner_channel)
                    for channel, corner_channel in zip(
                        (color.red(), color.green(), color.blue()),
                        (corner.red(), corner.green(), corner.blue()),
                    )
                )
                if distance <= tolerance:
                    color.setAlpha(0)
                    image.setPixelColor(x, y, color)

        return QPixmap.fromImage(image)
