from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QLabel,
    QFrame,
    QHBoxLayout,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

# 賞品カードWidget
from ui.widgets.prize_card import PrizeCard

# 参加人数Widget
from ui.widgets.participant_count import ParticipantCount

# ==========================================================
# オペレーター画面（メイン画面）
# ==========================================================
class OperatorWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # ------------------------------------------
        # ウィンドウ設定
        # ------------------------------------------
        self.setWindowTitle("LotteryApp")
        self.resize(1600, 900)

        # ------------------------------------------
        # メイン画面（背景）
        # ------------------------------------------
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)

        # ------------------------------------------
        # 画面全体のレイアウト
        #
        # ┌────────────────────────────┐
        # │ タイトル画像                │
        # │                            │
        # │ ┌────┬────────┬────┐       │
        # │ │左  │ 中央   │右  │       │
        # │ └────┴────────┴────┘       │
        # └────────────────────────────┘
        # ------------------------------------------
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        central.setLayout(main_layout)

        # ------------------------------------------
        # タイトル画像の表示位置
        #
        # 画像自体は絶対配置(move)で表示するため、
        # パネルと重ならないよう余白だけ確保する
        # ------------------------------------------
        TITLE_HEIGHT = 165

        # 左上座標
        TITLE_X = 20
        TITLE_Y = 0

        # パネルと重ねる高さ
        TITLE_OVERLAP = 40

        main_layout.addSpacing(TITLE_HEIGHT - TITLE_OVERLAP)


        # ------------------------------------------
        # メインエリア
        #
        # 左：賞品一覧
        # 中央：抽選画面
        # 右：当選履歴
        # ------------------------------------------
        center_layout = QHBoxLayout()
        center_layout.setSpacing(20)


        # ------------------------------------------
        # タイトル画像
        #
        # Layoutには載せず、
        # QLabelを絶対配置して表示する
        # ------------------------------------------
        self.title_label = QLabel(central)

        # プロジェクトルート取得
        project_root = Path(__file__).resolve().parents[2]

        # タイトル画像読込
        title_pixmap = QPixmap(
            str(project_root / "assets" / "images" / "ui" / "title.png")
        )

        self.title_label.setPixmap(title_pixmap)

        # QLabelサイズを画像サイズに合わせる
        self.title_label.resize(title_pixmap.size())

        # 他Widgetより前面へ表示
        self.title_label.raise_()

        # タイトル画像表示位置
        self.title_label.move(TITLE_X, TITLE_Y)


        # ------------------------------------------
        # 参加人数Widget（絶対配置）
        # ------------------------------------------
        self.participant_count = ParticipantCount(central)

        # サイズは後でQSSに合わせて調整
        self.participant_count.resize(180, 110)

        # 前面表示
        self.participant_count.raise_()

        # 右上へ配置
        def resizeEvent(self, event):
            super().resizeEvent(event)

            margin = 20

            self.participant_count.move(
            central.width() - self.participant_count.width() - 20,
            20,
            )

        # ------------------------------------------
        # 左パネル（賞品一覧）
        # ------------------------------------------
        self.left_panel = QFrame()
        self.left_panel.setObjectName("leftPanel")

        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(15, 15, 15, 15)
        left_layout.setSpacing(15)

        # パネルタイトル
        left_title = QLabel("賞品一覧")
        left_title.setObjectName("panelTitle")
        left_title.setAlignment(Qt.AlignHCenter | Qt.AlignTop)

        left_layout.addWidget(left_title)

        # 賞品カード（現在はサンプル1枚）
        left_layout.addWidget(PrizeCard())

        self.left_panel.setLayout(left_layout)

        # ------------------------------------------
        # 中央パネル（抽選画面）
        # ------------------------------------------
        center = QFrame()
        center.setObjectName("centerPanel")

        center_layout2 = QVBoxLayout()
        center_layout2.setContentsMargins(15, 15, 15, 15)
        center_layout2.setSpacing(15)

        # パネルタイトル
        center_title = QLabel("現在の賞品")
        center_title.setObjectName("panelTitle")
        center_title.setAlignment(Qt.AlignHCenter | Qt.AlignTop)

        center_layout2.addWidget(center_title)

        center_layout2.addWidget(QLabel("当選者表示"))
        center_layout2.addWidget(QLabel("ルーレット"))

        center.setLayout(center_layout2)


        # ------------------------------------------
        # 右パネル（当選履歴）
        # ------------------------------------------
        right = QFrame()
        right.setObjectName("rightPanel")

        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(15, 15, 15, 15)
        right_layout.setSpacing(15)


        # ------------------------------------------
        # パネルタイトル
        # ------------------------------------------
        right_title = QLabel("当選履歴")
        right_title.setObjectName("panelTitle")
        right_title.setAlignment(Qt.AlignHCenter)

        right_layout.addWidget(right_title)

        # 今後ここへ当選履歴カードを追加
        right_layout.addStretch()

        right.setLayout(right_layout)

        # ------------------------------------------
        # メインエリアへ追加
        #
        # stretch
        # 左 : 中央 : 右 = 2 : 5 : 2
        # ------------------------------------------
        center_layout.addWidget(self.left_panel, 2)
        center_layout.addWidget(center, 5)
        center_layout.addWidget(right, 2)

        main_layout.addLayout(center_layout)
        
    # ------------------------------------------
    # ウィンドウサイズ変更時
    # 参加人数Widgetを常に右上へ配置する
    # ------------------------------------------
    def resizeEvent(self, event):
        super().resizeEvent(event)

        margin = 20

        self.participant_count.move(
            self.centralWidget().width()
            - self.participant_count.width()
            - margin,
            20,
        )
        
