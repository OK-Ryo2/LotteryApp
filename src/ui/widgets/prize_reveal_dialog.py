from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout

from logic.prizes import Prize


class PrizeRevealDialog(QDialog):
    """次の賞品を紹介し、抽選開始を確認するポップアップ。"""

    def __init__(self, prize: Prize, parent=None):
        super().__init__(parent)
        self.setObjectName("prizeRevealDialog")
        self.setWindowTitle("次の賞品")
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        project_root = Path(__file__).resolve().parents[3]
        ribbon = QLabel()
        ribbon.setObjectName("prizeRevealRibbon")
        ribbon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ribbon.setFixedHeight(56)
        ribbon_pixmap = QPixmap(str(project_root / "assets" / "images" / "ui" / "ribbon.png"))
        if not ribbon_pixmap.isNull():
            ribbon.setPixmap(
                ribbon_pixmap.scaledToWidth(280, Qt.TransformationMode.SmoothTransformation)
            )
        else:
            ribbon.setText("◆")
        layout.addWidget(ribbon)

        title = QLabel("次の賞品")
        title.setObjectName("prizeRevealTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        rank = QLabel(f"{prize.rank}等")
        rank.setObjectName("prizeRevealRank")
        rank.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(rank)

        name = QLabel(prize.current_name)
        name.setObjectName("prizeRevealName")
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name.setWordWrap(True)
        layout.addWidget(name)

        image = QLabel()
        image.setObjectName("prizeRevealImage")
        image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image.setFixedHeight(210)
        pixmap = QPixmap(str(project_root / prize.image_path))
        if not pixmap.isNull():
            image.setPixmap(
                pixmap.scaled(330, 205, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            )
        else:
            image.setText("NO IMAGE")
        layout.addWidget(image)

        description = QLabel(prize.description)
        description.setObjectName("prizeRevealDescription")
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description.setWordWrap(True)
        layout.addWidget(description)

        start_button = QPushButton("この賞品で抽選開始")
        start_button.setObjectName("prizeRevealStartButton")
        start_button.clicked.connect(self.accept)
        layout.addWidget(start_button, alignment=Qt.AlignmentFlag.AlignCenter)

        cancel_button = QPushButton("賞品一覧に戻る")
        cancel_button.setObjectName("prizeRevealCancelButton")
        cancel_button.clicked.connect(self.reject)
        layout.addWidget(cancel_button, alignment=Qt.AlignmentFlag.AlignCenter)

        if parent:
            self.resize(
                max(420, min(680, round(parent.width() * 0.43))),
                max(500, min(620, round(parent.height() * 0.66))),
            )
