from pathlib import Path
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QLabel,
    QPushButton,
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

# 現在抽選中の賞品表示Widget
from ui.widgets.current_prize import CurrentPrize

# 当選者表示Widget
from ui.widgets.winner_display import WinnerDisplay

# ルーレットWidget
from ui.widgets.roulette import Roulette
from ui.widgets.history_list import HistoryList
from logic.lottery import Lottery
from logic.participants import Participant, load_participants

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
        TITLE_X = 40
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

        self.participants = self._load_initial_participants()
        self.lottery = Lottery(self.participants)
        self.pending_history_entry = None
        self.participant_count.update_count(len(self.participants))

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

        # 賞品カード（現在はサンプル1枚・上揃え）
        self.prize_card = PrizeCard()
        left_layout.addWidget(self.prize_card, alignment=Qt.AlignTop)
        left_layout.addStretch()

        self.left_panel.setLayout(left_layout)

        # ------------------------------------------
        # 中央パネル（抽選画面）
        # ------------------------------------------
        center = QFrame()
        center.setObjectName("centerPanel")

        center_layout2 = QVBoxLayout()
        center_layout2.setContentsMargins(15, 15, 15, 15)
        center_layout2.setSpacing(15)

        # 現在抽選中の賞品（中央パネル最上部）
        self.current_prize = CurrentPrize()
        center_layout2.addWidget(self.current_prize)

        # 当選者表示（ルーレット停止後に当選者名へ更新）
        self.winner_display = WinnerDisplay()
        center_layout2.addWidget(self.winner_display)

        # ルーレット
        self.roulette = Roulette(
            [participant.to_dict() for participant in self.lottery.available_participants]
        )
        center_layout2.addWidget(self.roulette)

        # 抽選操作ボタン
        self.draw_button = QPushButton("🎉 抽選スタート")
        self.draw_button.setObjectName("drawButton")
        self.draw_button.setFixedWidth(250)
        self.draw_button.clicked.connect(self.toggle_draw)
        center_layout2.addWidget(self.draw_button, alignment=Qt.AlignHCenter)

        self.next_prize_button = QPushButton("次の賞品へ")
        self.next_prize_button.setObjectName("nextPrizeButton")
        self.next_prize_button.setFixedWidth(200)
        self.next_prize_button.clicked.connect(self.prepare_next_prize)
        center_layout2.addWidget(self.next_prize_button, alignment=Qt.AlignHCenter)

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

        self.history_list = HistoryList()
        right_layout.addWidget(self.history_list, 1)

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

    def toggle_draw(self):
        """抽選開始／停止ボタンの状態を切り替える。"""
        if self.roulette.is_spinning:
            selected_participant = self.roulette.stop()
            winner = self.lottery.confirm_winner(selected_participant["id"])
            self.winner_display.show_winner(winner.name, winner.department)
            self.pending_history_entry = (
                self.current_prize.rank_label.text(),
                self.current_prize.prize_name_label.text(),
                winner.name,
                datetime.now(),
            )
            self.draw_button.setText("🎉 抽選スタート")
            self.draw_button.setEnabled(False)
            self.next_prize_button.setEnabled(True)
            return

        self.roulette.start()
        self.winner_display.set_drawing()
        self.draw_button.setText("🎉 ストップ")
        self.next_prize_button.setEnabled(False)

    def prepare_next_prize(self):
        """次の賞品データの読み込み前に、抽選画面を初期状態へ戻す。"""
        if self.pending_history_entry:
            self.history_list.add_entry(*self.pending_history_entry)
            self.pending_history_entry = None

        self.winner_display.reset()
        if self.lottery.has_available_participant:
            self.roulette.set_participants(
                [
                    participant.to_dict()
                    for participant in self.lottery.available_participants
                ]
            )
            self.draw_button.setEnabled(True)
            return

        self.draw_button.setEnabled(False)
        self.next_prize_button.setEnabled(False)
        self.winner_display.status_label.setText("全員当選しました")

    @staticmethod
    def _load_initial_participants() -> list[Participant]:
        """participants.csv があれば読み込み、なければ画面確認用の候補を使う。"""
        project_root = Path(__file__).resolve().parents[2]
        csv_path = project_root / "data" / "participants.csv"
        if csv_path.exists():
            return load_participants(csv_path)

        return [
            Participant(item["id"], item["name"], item["department"])
            for item in Roulette._SAMPLE_PARTICIPANTS
        ]
        
