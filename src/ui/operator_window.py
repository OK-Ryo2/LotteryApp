from pathlib import Path
from datetime import datetime
import re
import sys

from PySide6.QtCore import QProcess, QTimer, Qt
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QGridLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QFrame,
    QHBoxLayout,
    QMainWindow,
    QSpacerItem,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

# 賞品カードWidget
from ui.widgets.prize_card import PrizeCard

# 参加人数Widget
from ui.widgets.participant_count import ParticipantCount

# 現在抽選中の賞品表示Widget
from ui.widgets.current_prize import CurrentPrize
from ui.widgets.draw_status import DrawStatus
from ui.widgets.prize_reveal_dialog import PrizeRevealDialog

# 当選者表示Widget
from ui.widgets.winner_dialog import WinnerDialog

# ルーレットWidget
from ui.widgets.roulette import Roulette
from ui.widgets.history_list import HistoryList
from logic.lottery import Lottery
from logic.participants import Participant, load_participants
from logic.prizes import load_prizes, sync_prize_json_from_csv
from logic.sound import SoundManager


class BackgroundWidget(QWidget):
    """画面サイズに合わせて背景テクスチャを全面描画する中央ウィジェット。"""

    def __init__(self, background_path: Path, parent=None):
        super().__init__(parent)
        self._background_pixmap = QPixmap(str(background_path))

    def paintEvent(self, event):  # noqa: N802 - Qt のオーバーライド名
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#071126"))

        if self._background_pixmap.isNull() or self.width() <= 0 or self.height() <= 0:
            return

        # 画面全体を覆うよう拡大し、余った部分は中央でトリミングする。
        scaled = self._background_pixmap.scaled(
            self.size(),
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation,
        )
        painter.drawPixmap(
            (self.width() - scaled.width()) // 2,
            (self.height() - scaled.height()) // 2,
            scaled,
        )


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
        project_root = Path(__file__).resolve().parents[2]
        central = BackgroundWidget(
            project_root / "assets" / "images" / "backgrounds" / "background_texture.png"
        )
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
        # 背景テクスチャを左右にも見せるため、メイン領域の外側余白を広げる。
        # パネルは残りの幅に収まるため、中央・右パネルも縮尺に合わせて自然に縮む。
        main_layout.setContentsMargins(52, 8, 52, 8)
        main_layout.setSpacing(2)
        central.setLayout(main_layout)
        self.main_layout = main_layout
        self._base_stylesheet = QApplication.instance().styleSheet()
        self._active_font_scale = None

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

        self.header_spacer = QSpacerItem(
            0,
            TITLE_HEIGHT - TITLE_OVERLAP,
            QSizePolicy.Minimum,
            QSizePolicy.Fixed,
        )
        main_layout.addItem(self.header_spacer)


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

        self.title_pixmap = title_pixmap
        self.sound_manager = SoundManager(project_root)
        self._last_candidate_id = None
        self._flash_sound_timer = QTimer(self)
        self._flash_sound_timer.setInterval(350)
        self._flash_sound_timer.timeout.connect(self._play_flash_sound)

        # QLabelサイズを画像サイズに合わせる

        # 他Widgetより前面へ表示
        self.title_label.raise_()

        # タイトル画像表示位置
        self.title_label.move(TITLE_X, TITLE_Y)


        # ------------------------------------------
        # 参加人数Widget（絶対配置）
        # ------------------------------------------
        self.participant_count = ParticipantCount(central)

        self.participants_csv_path = project_root / "data" / "participants.csv"
        self.prizes_csv_path = project_root / "data" / "prizes.csv"
        self.participants = self._load_initial_participants(self.participants_csv_path)
        self.lottery = Lottery(self.participants)
        prizes_json_path = project_root / "data" / "prizes.json"
        sync_prize_json_from_csv(self.prizes_csv_path, prizes_json_path)
        self.prizes = load_prizes(prizes_json_path)
        self.remaining_stocks = {prize.prize_id: prize.stock for prize in self.prizes}
        self.drawn_counts = {prize.prize_id: 0 for prize in self.prizes}
        # 景品は20等から1等へ向かって抽選する。
        self.current_prize_index = len(self.prizes) - 1
        self.current_prize_revealed = False
        self.revealed_prize_ids: set[str] = set()
        self.revealed_prize_order: list[str] = []
        self.prize_start_snapshots: dict[str, dict] = {}
        self.pending_history_entry = None
        self.pending_prize_id = None
        self._winner_popup_pending = False
        self._initial_prize_scroll_pending = True
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

        # 賞品カード（全20種類をスクロール表示）
        self.prize_scroll = QScrollArea()
        self.prize_scroll.setObjectName("prizeScroll")
        self.prize_scroll.setWidgetResizable(True)
        self.prize_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        prize_list_widget = QWidget()
        prize_list_widget.setObjectName("prizeListContent")
        prize_list_layout = QVBoxLayout(prize_list_widget)
        # 右端に余白を確保し、カード枠とスクロールバーを重ねない
        prize_list_layout.setContentsMargins(0, 0, 14, 0)
        prize_list_layout.setSpacing(4)

        self.prize_cards = []
        self.prize_cards_by_id = {}
        for prize in self.prizes:
            prize_card = PrizeCard(
                f"{prize.rank}等",
                prize.list_name,
                prize.stock,
                "公開前🔒",
                project_root / prize.image_path,
            )
            prize_card.set_revealed(False)
            self.prize_cards.append(prize_card)
            self.prize_cards_by_id[prize.prize_id] = prize_card
            prize_list_layout.addWidget(prize_card, alignment=Qt.AlignTop)

        prize_list_layout.addStretch()
        self.prize_scroll.setWidget(prize_list_widget)

        left_layout.addWidget(self.prize_scroll, 1)
        QTimer.singleShot(
            0,
            lambda: self.prize_scroll.verticalScrollBar().setValue(
                self.prize_scroll.verticalScrollBar().maximum()
            ),
        )

        self.left_panel.setLayout(left_layout)

        # ------------------------------------------
        # 中央パネル（抽選画面）
        # ------------------------------------------
        center = QFrame()
        center.setObjectName("centerPanel")

        center_layout2 = QVBoxLayout()
        center_layout2.setContentsMargins(12, 0, 12, 12)
        center_layout2.setSpacing(8)
        self.center_content_layout = center_layout2

        # 現在抽選中の賞品（中央パネル最上部）
        current_prize = self.prizes[self.current_prize_index]
        self.current_prize = CurrentPrize(
            f"{current_prize.rank}等",
            current_prize.current_name,
            self.remaining_stocks[current_prize.prize_id],
        )
        self.current_prize.hide()
        center_layout2.addWidget(self.current_prize, 1)

        self.draw_status = DrawStatus()
        center_layout2.addWidget(self.draw_status)

        # ルーレット
        self.roulette = Roulette(
            [participant.to_dict() for participant in self.lottery.available_participants]
        )
        self.roulette.stopped.connect(self._on_roulette_stopped)
        self.roulette.acceleration_completed.connect(
            self._enable_stop_button_after_acceleration
        )
        self.roulette.candidate_changed.connect(self._on_candidate_changed)
        center_layout2.addWidget(self.roulette, 7)

        # 抽選操作ボタン
        self.draw_button = QPushButton("🎉 抽選スタート")
        self.draw_button.setObjectName("drawButton")
        self.draw_button.setMinimumWidth(160)
        self.draw_button.setMaximumWidth(250)
        self.draw_button.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.draw_button.clicked.connect(self.toggle_draw)
        self.draw_button.setEnabled(False)
        self.draw_button.hide()

        self.next_prize_button = QPushButton("抽選会スタート")
        self.next_prize_button.setObjectName("nextPrizeButton")
        self.next_prize_button.setMinimumWidth(150)
        self.next_prize_button.setMaximumWidth(220)
        self.next_prize_button.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.next_prize_button.setEnabled(True)
        self.next_prize_button.clicked.connect(self.prepare_next_prize)

        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(24)
        button_layout.addStretch()
        button_layout.addWidget(self.draw_button)
        button_layout.addWidget(self.next_prize_button)
        button_layout.addStretch()
        center_layout2.addLayout(button_layout)

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
        self.history_scroll = QScrollArea()
        self.history_scroll.setObjectName("historyScroll")
        self.history_scroll.setWidgetResizable(True)
        self.history_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.history_scroll.setWidget(self.history_list)
        right_layout.addWidget(self.history_scroll, 1)

        right.setLayout(right_layout)

        self.winner_dialog = WinnerDialog(self)

        # ------------------------------------------
        # メインエリアへ追加
        #
        # stretch
        # 左 : 中央 : 右 = 2 : 5 : 2
        # 短い一覧表示名に合わせて左パネルを絞り、中央の表示幅を広げる
        # ------------------------------------------
        center_layout.addWidget(self.left_panel, 5)
        center_layout.addWidget(center, 9)
        center_layout.addWidget(right, 4)

        main_layout.addLayout(center_layout, 1)

        self.footer = QFrame()
        self.footer.setObjectName("footerBar")
        footer_layout = QGridLayout(self.footer)
        footer_layout.setContentsMargins(12, 4, 12, 4)
        footer_layout.setColumnStretch(0, 1)
        footer_layout.setColumnStretch(1, 1)
        footer_layout.setColumnStretch(2, 1)

        # 起動時は誤って音が鳴らないよう、音量OFFから開始する。
        self.volume_enabled = False
        self.sound_manager.set_enabled(False)
        self.volume_button = QPushButton()
        self.volume_button.setObjectName("volumeButton")
        self.volume_button.clicked.connect(self._toggle_volume)
        footer_layout.addWidget(self.volume_button, 0, 0, alignment=Qt.AlignLeft)

        footer_message = QLabel("I hope you win a prize!")
        footer_message.setObjectName("footerMessage")
        footer_message.setAlignment(Qt.AlignCenter)
        footer_layout.addWidget(footer_message, 0, 1, alignment=Qt.AlignCenter)

        self.settings_button = QPushButton("⚙ 設定")
        self.settings_button.setObjectName("settingsButton")
        self.settings_button.clicked.connect(self._show_settings_dialog)
        footer_layout.addWidget(self.settings_button, 0, 2, alignment=Qt.AlignRight)

        self._update_volume_button()
        main_layout.addWidget(self.footer)
        QTimer.singleShot(0, self._apply_responsive_layout)
        
    # ------------------------------------------
    # ウィンドウサイズ変更時
    # 参加人数Widgetを常に右上へ配置する
    # ------------------------------------------
    def resizeEvent(self, event):
        super().resizeEvent(event)

        if not hasattr(self, "participant_count"):
            return
        self._apply_responsive_layout()

    def _apply_responsive_layout(self):
        """画面の論理サイズに合わせてヘッダーと中央パネルを安全に収める。"""
        central = self.centralWidget()
        if (
            central is None
            or not hasattr(self, "title_pixmap")
            or not hasattr(self, "history_list")
        ):
            return

        font_scale = max(
            0.75,
            min(1.10, min(central.width() / 1600, central.height() / 900)),
        )
        if font_scale != self._active_font_scale:
            def scale_font(match):
                size = max(9, round(int(match.group(1)) * font_scale))
                return f"font-size: {size}px;"

            stylesheet = re.sub(
                r"font-size:\s*(\d+)px;",
                scale_font,
                self._base_stylesheet,
            )
            QApplication.instance().setStyleSheet(stylesheet)
            self._active_font_scale = font_scale

        self.participant_count.set_scale(font_scale)
        self.current_prize.set_scale(font_scale)
        self.draw_status.set_scale(font_scale)
        self.roulette.set_scale(font_scale)
        self.history_list.set_scale(font_scale)
        self.footer.setFixedHeight(max(36, round(50 * font_scale)))

        available_height = max(1, central.height())
        header_height = max(
            self.participant_count.height() + 4,
            min(110, int(available_height * 0.10)),
        )
        self.header_spacer.changeSize(
            0,
            header_height,
            QSizePolicy.Minimum,
            QSizePolicy.Fixed,
        )

        title_scale = min(
            0.67,
            (central.width() * 0.24) / max(1, self.title_pixmap.width()),
            header_height / max(1, self.title_pixmap.height()),
        )
        scaled_title = self.title_pixmap.scaled(
            max(1, int(self.title_pixmap.width() * title_scale)),
            max(1, int(self.title_pixmap.height() * title_scale)),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.title_label.setPixmap(scaled_title)
        self.title_label.resize(scaled_title.size())
        self.title_label.move(max(16, int(central.width() * 0.02)), 0)
        self.participant_count.move(
            central.width() - self.participant_count.width() - 8,
            max(4, header_height - self.participant_count.height()),
        )
        self.main_layout.invalidate()

        if self._initial_prize_scroll_pending:
            self._initial_prize_scroll_pending = False
            current_prize = self.prizes[self.current_prize_index]
            QTimer.singleShot(
                0,
                lambda: self._scroll_current_prize_card_into_view(
                    current_prize.prize_id
                ),
            )

    def _toggle_volume(self):
        """音量のON/OFF表示を切り替える。"""
        self.volume_enabled = not self.volume_enabled
        self.sound_manager.set_enabled(self.volume_enabled)
        if self.volume_enabled:
            self.sound_manager.play("test")
        else:
            self._flash_sound_timer.stop()
        self._update_volume_button()

    def _update_volume_button(self):
        """環境依存文字で音量ON/OFF状態を表示する。"""
        self.volume_button.setText(
            "🔊 音量 ON" if self.volume_enabled else "🔇 音量 OFF"
        )

    def _show_settings_dialog(self):
        """抽選状態を操作する設定ポップアップを開く。"""
        dialog = QDialog(self)
        dialog.setObjectName("settingsDialog")
        dialog.setWindowTitle("設定")
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(28, 24, 28, 20)
        layout.setSpacing(10)
        message = QLabel("設定")
        message.setObjectName("settingsDialogMessage")
        message.setAlignment(Qt.AlignCenter)

        reset_button = QPushButton("抽選状態初期化")
        reset_button.setObjectName("settingsDialogClose")
        reset_button.clicked.connect(
            lambda: self._confirm_lottery_reset(dialog)
        )

        redraw_button = QPushButton("1つ前の賞品を再抽選")
        redraw_button.setObjectName("settingsDialogClose")
        redraw_button.clicked.connect(
            lambda: self._confirm_prize_redraw(dialog)
        )

        reload_button = QPushButton("ソースを再読み込み")
        reload_button.setObjectName("settingsDialogReload")
        reload_button.clicked.connect(
            lambda: self._confirm_source_reload(dialog)
        )

        st_button = QPushButton("抽選（等級指定）")
        st_button.setObjectName("settingsDialogST")
        st_button.setEnabled(True)
        st_button.clicked.connect(lambda: self._start_from_rank(dialog))

        close_button = QPushButton("閉じる")
        close_button.setObjectName("settingsDialogClose")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(message)
        layout.addWidget(st_button, alignment=Qt.AlignCenter)
        layout.addWidget(reset_button, alignment=Qt.AlignCenter)
        layout.addWidget(redraw_button, alignment=Qt.AlignCenter)
        layout.addWidget(reload_button, alignment=Qt.AlignCenter)
        layout.addWidget(close_button, alignment=Qt.AlignCenter)
        dialog.resize(
            max(260, min(420, round(self.width() * 0.25))),
            max(500, min(620, round(self.height() * 0.60))),
        )
        dialog.setMinimumHeight(500)
        dialog.adjustSize()
        dialog.raise_()
        dialog.activateWindow()
        dialog.exec()

    def _start_from_rank(self, settings_dialog: QDialog):
        """指定した等級を初期抽選対象としてSTを開始する。"""
        input_dialog = QInputDialog(settings_dialog)
        input_dialog.setInputMode(QInputDialog.InputMode.IntInput)
        input_dialog.setWindowTitle("ST開始")
        input_dialog.setLabelText("抽選を開始する等級を入力してください：")
        input_dialog.setIntValue(self.prizes[self.current_prize_index].rank)
        input_dialog.setIntRange(
            min(prize.rank for prize in self.prizes),
            max(prize.rank for prize in self.prizes),
        )
        input_dialog.setIntStep(1)
        input_dialog.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint
        )
        input_dialog.raise_()
        input_dialog.activateWindow()
        accepted = input_dialog.exec() == QDialog.DialogCode.Accepted
        rank = input_dialog.intValue()
        if not accepted:
            return

        target_index = next(
            (index for index, prize in enumerate(self.prizes) if prize.rank == rank),
            None,
        )
        if target_index is None:
            QMessageBox.warning(
                self,
                "ST開始",
                f"{rank}等の賞品が見つかりません。",
            )
            settings_dialog.show()
            settings_dialog.raise_()
            settings_dialog.activateWindow()
            return

        # STは抽選状態を初期化し、指定等級の商品紹介から開始する。
        self._reset_lottery_state()
        self.current_prize_index = target_index
        self._refresh_after_state_restore()
        settings_dialog.accept()
        self._show_next_prize_dialog()

    def _confirm_source_reload(self, settings_dialog: QDialog):
        """確認後、現在のPythonプロセスを再起動して修正済みソースを反映する。"""
        choice = QMessageBox.question(
            settings_dialog,
            "ソースを再読み込み",
            "現在の画面を閉じて、修正済みのソースでアプリを再起動します。よろしいですか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if choice != QMessageBox.StandardButton.Yes:
            return

        settings_dialog.accept()
        script_path = Path(__file__).resolve().parents[1] / "main.py"
        working_directory = str(script_path.parent)
        QProcess.startDetached(
            sys.executable,
            [str(script_path)],
            working_directory,
        )
        QApplication.instance().quit()

    def _confirm_lottery_reset(self, settings_dialog: QDialog):
        """確認でYesが選ばれた場合のみ、抽選状態を初期化する。"""
        choice = QMessageBox.question(
            settings_dialog,
            "抽選初期化",
            "当選履歴・参加者・賞品公開状態をすべて初期化します。よろしいですか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if choice != QMessageBox.StandardButton.Yes:
            return

        self._reset_lottery_state()
        settings_dialog.accept()

    def _confirm_prize_redraw(self, settings_dialog: QDialog):
        """確認でYesが選ばれた場合のみ、直前の賞品の抽選前状態へ戻す。"""
        if not self.revealed_prize_order:
            QMessageBox.information(settings_dialog, "賞品再抽選", "再抽選できる賞品がありません。")
            return

        choice = QMessageBox.question(
            settings_dialog,
            "賞品再抽選",
            "直前に紹介した賞品を、抽選前の状態へ戻します。よろしいですか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if choice != QMessageBox.StandardButton.Yes:
            return

        self._restore_previous_prize_state()
        settings_dialog.accept()

    def toggle_draw(self):
        """抽選開始／停止ボタンの状態を切り替える。"""
        if self._winner_popup_pending:
            return

        if self.roulette.is_spinning:
            self.sound_manager.play("stop")
            self.roulette.request_stop()
            self.draw_button.setText("🎉 停止中...")
            self.draw_button.setEnabled(False)
            return

        self.roulette.start()
        self._last_candidate_id = None
        self.draw_button.setText("🎉 ストップ")
        # 最高速へ加速する2秒間はストップ操作を受け付けない。
        self.draw_button.setEnabled(False)
        self.next_prize_button.setEnabled(False)
        self.draw_status.set_spinning(self.roulette.current_participant)

    def _enable_stop_button_after_acceleration(self):
        """ルーレットが最高速へ到達した瞬間にストップ操作を有効化する。"""
        if (
            self.roulette.is_spinning
            and not self.roulette.is_stopping
            and not self._winner_popup_pending
        ):
            self.draw_button.setEnabled(True)

    def _on_candidate_changed(self, participant: dict[str, str]):
        """候補者表示を更新し、カード切り替わり時に短い音を鳴らす。"""
        self.draw_status.set_spinning(participant)
        participant_id = participant.get("id")
        if self.roulette.is_spinning and participant_id != self._last_candidate_id:
            self.sound_manager.play("candidate")
            self._last_candidate_id = participant_id

    def _play_flash_sound(self):
        """当選カード点滅中の短い音を再生する。"""
        self.sound_manager.play("flash")

    def _on_roulette_stopped(self, selected_participant: dict[str, str]):
        """慣性で停止した候補者を当選者として確定する。"""
        winner = self.lottery.confirm_winner(selected_participant["id"])
        self.participant_count.update_count(len(self.lottery.available_participants))

        current_prize = self.prizes[self.current_prize_index]
        self.pending_history_entry = (
            f"{current_prize.rank}等",
            current_prize.current_name,
            winner.department,
            winner.name,
            datetime.now(),
        )
        self.pending_prize_id = current_prize.prize_id
        self.draw_button.setText("🎉 抽選スタート")
        self.draw_button.setEnabled(False)
        # 停止演出と当選者ポップアップが終わるまでは次の賞品へ進めない。
        self.next_prize_button.setEnabled(False)
        # ポップアップを閉じるまでは、停止中の見た目を維持して操作だけをロックする。
        self._winner_popup_pending = True
        self.draw_button.setText("🎉 停止中...")
        self.draw_button.setEnabled(False)
        self.roulette.start_winner_flash()
        self._play_flash_sound()
        self._flash_sound_timer.start()
        # 当選者ポップアップの表示中は、中央の状態文字列を消す。
        self.draw_status.clear_status()
        # ルーレット停止の余韻を見せてから当選者を発表する。
        QTimer.singleShot(
            2000,
            lambda: self._show_winner_popup(winner, current_prize),
        )

    def _show_winner_popup(self, winner, current_prize):
        """停止後の演出待機を経て当選者ポップアップを表示する。"""
        self._flash_sound_timer.stop()
        self.roulette.stop_winner_flash()
        self.sound_manager.play("winner")
        self.winner_dialog.show_winner(winner.name, winner.department)
        # 履歴は当選者を確認してポップアップを閉じた時点で反映する。
        self.history_list.add_entry(*self.pending_history_entry)
        self.pending_history_entry = None
        self.drawn_counts[current_prize.prize_id] += 1
        self._update_current_prize_display()
        if self.remaining_stocks[current_prize.prize_id] <= 1:
            self.draw_status.set_completed()
        else:
            self.draw_status.set_waiting()
        # 当選者ポップアップを閉じたタイミングで、次の操作用のボタン状態へ切り替える。
        self.draw_button.setText("🎉 抽選スタート")
        self.draw_button.setEnabled(False)
        self._winner_popup_pending = False
        self._update_next_action_label()
        self.next_prize_button.setEnabled(True)

    def prepare_next_prize(self):
        """当選結果を確定し、必要なら次の賞品の紹介ポップアップを開く。"""
        if self._winner_popup_pending:
            return

        missing_csv_messages = self._missing_required_csv_messages()
        if missing_csv_messages:
            QMessageBox.warning(
                self,
                "CSVファイルを確認してください",
                "\n".join(missing_csv_messages),
            )
            return

        self.next_prize_button.setEnabled(False)
        if self.pending_prize_id:
            # 残数は結果を確認して「次の賞品へ」を押した時点で減らす。
            self.remaining_stocks[self.pending_prize_id] -= 1
            if self.remaining_stocks[self.pending_prize_id] > 0:
                self._update_current_prize_display()
                self.pending_prize_id = None
                self._prepare_same_prize_draw()
                return

            self._mark_current_prize_completed()
            self.pending_prize_id = None

        self._show_next_prize_dialog()

    def _update_current_prize_display(self):
        """現在抽選中の景品と、その左側カードを残数に合わせて更新する。"""
        current_prize = self.prizes[self.current_prize_index]
        remain = self.remaining_stocks[current_prize.prize_id]
        drawn_count = self.drawn_counts[current_prize.prize_id]
        self.current_prize.update_prize(
            f"{current_prize.rank}等",
            current_prize.current_name,
            drawn_count,
            current_prize.stock,
        )
        self.prize_cards_by_id[current_prize.prize_id].update_prize(
            f"{current_prize.rank}等", current_prize.list_name, current_prize.stock, "抽選中"
        )
        self.prize_cards_by_id[current_prize.prize_id].set_active(True)
        self._scroll_current_prize_card_into_view(current_prize.prize_id)

    def _scroll_current_prize_card_into_view(self, prize_id: str):
        """抽選中カードが切り替わったら、カード全体が見える位置まで一覧を自動スクロールする。"""
        prize_card = self.prize_cards_by_id[prize_id]
        QTimer.singleShot(
            0,
            lambda: self.prize_scroll.ensureWidgetVisible(prize_card, 8, 8),
        )

    def _prepare_same_prize_draw(self):
        """残数がある同一賞品の次回抽選を準備する。"""
        if not self.lottery.has_available_participant:
            self.draw_button.setEnabled(False)
            self.next_prize_button.setEnabled(False)
            return

        if self.lottery.has_available_participant:
            self.roulette.set_participants(
                [participant.to_dict() for participant in self.lottery.available_participants]
            )
        else:
            self.roulette.reset()
        self.draw_status.set_waiting()
        self.draw_button.show()
        self.next_prize_button.show()
        self._update_next_action_label()
        self.draw_button.setEnabled(True)
        self.next_prize_button.setEnabled(False)

    def _update_next_action_label(self):
        """次の操作が同一賞品の再抽選か、次等級への移動かを表示する。"""
        if not self.current_prize_revealed:
            self.next_prize_button.setText("抽選会スタート")
            return

        current_prize = self.prizes[self.current_prize_index]
        remaining = self.remaining_stocks[current_prize.prize_id]
        drawn = self.drawn_counts[current_prize.prize_id]
        if drawn > 0 and remaining > 1:
            self.next_prize_button.setText("次の抽選へ")
        else:
            self.next_prize_button.setText("次の賞品へ")

    def _mark_current_prize_completed(self):
        """引き終えた賞品を抽選済みにし、次の紹介を待つ状態へする。"""
        current_prize = self.prizes[self.current_prize_index]
        card = self.prize_cards_by_id[current_prize.prize_id]
        card.update_prize(
            f"{current_prize.rank}等",
            current_prize.list_name,
            current_prize.stock,
            "抽選済み",
        )
        card.set_active(False)
        self.draw_status.set_completed()
        self.draw_button.setEnabled(False)
        if current_prize.rank == 1:
            self.draw_status.clear_status()
            self.draw_button.hide()
            self.next_prize_button.setEnabled(False)
            self.roulette.show_completion()

    def _show_next_prize_dialog(self):
        """まだ公開していない、次に低い等級の賞品を紹介する。"""
        next_index = next(
            (
                index
                for index in range(self.current_prize_index, -1, -1)
                if self.prizes[index].prize_id not in self.revealed_prize_ids
            ),
            None,
        )
        if next_index is None:
            self.draw_button.setEnabled(False)
            self.next_prize_button.setEnabled(False)
            return

        dialog = PrizeRevealDialog(self.prizes[next_index], self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            self.next_prize_button.setEnabled(True)
            return

        next_prize = self.prizes[next_index]
        self.prize_start_snapshots[next_prize.prize_id] = self._capture_lottery_state()
        self.current_prize_index = next_index
        self.current_prize_revealed = True
        current_prize = self.prizes[self.current_prize_index]
        self.revealed_prize_ids.add(current_prize.prize_id)
        self.revealed_prize_order.append(current_prize.prize_id)
        self.current_prize.show()
        self.roulette.show_roulette()
        self._update_current_prize_display()
        self.prize_cards_by_id[current_prize.prize_id].set_revealed(True, "抽選中")
        self.next_prize_button.setText("次の賞品へ")
        self._prepare_same_prize_draw()

    def _capture_lottery_state(self) -> dict:
        """賞品紹介の直前に、再抽選用の状態スナップショットを保存する。"""
        return {
            "winner_ids": self.lottery.winner_ids(),
            "remaining_stocks": dict(self.remaining_stocks),
            "drawn_counts": dict(self.drawn_counts),
            "revealed_prize_ids": set(self.revealed_prize_ids),
            "revealed_prize_order": list(self.revealed_prize_order),
            "current_prize_index": self.current_prize_index,
            "current_prize_revealed": self.current_prize_revealed,
            "history_entries": list(self.history_list.entries),
            "pending_history_entry": self.pending_history_entry,
            "pending_prize_id": self.pending_prize_id,
        }

    def _restore_previous_prize_state(self):
        """最後に紹介した賞品を、紹介・抽選前の状態へ戻す。"""
        prize_id = self.revealed_prize_order[-1]
        snapshot = self.prize_start_snapshots.get(prize_id)
        if not snapshot:
            return

        self.lottery.restore_winner_ids(snapshot["winner_ids"])
        self.remaining_stocks = dict(snapshot["remaining_stocks"])
        self.drawn_counts = dict(snapshot["drawn_counts"])
        self.revealed_prize_ids = set(snapshot["revealed_prize_ids"])
        self.revealed_prize_order = list(snapshot["revealed_prize_order"])
        self.current_prize_index = snapshot["current_prize_index"]
        self.current_prize_revealed = snapshot["current_prize_revealed"]
        self.pending_history_entry = snapshot["pending_history_entry"]
        self.pending_prize_id = snapshot["pending_prize_id"]
        self.history_list.restore_entries(snapshot["history_entries"])
        self.prize_start_snapshots.pop(prize_id, None)
        self.participant_count.update_count(len(self.lottery.available_participants))
        self._refresh_after_state_restore()

    def _reset_lottery_state(self):
        """アプリ起動直後と同じ抽選状態へ戻す。"""
        self.lottery.reset()
        self.remaining_stocks = {
            prize.prize_id: prize.stock for prize in self.prizes
        }
        self.drawn_counts = {prize.prize_id: 0 for prize in self.prizes}
        self.revealed_prize_ids.clear()
        self.revealed_prize_order.clear()
        self.prize_start_snapshots.clear()
        self.current_prize_index = len(self.prizes) - 1
        self.current_prize_revealed = False
        self.pending_history_entry = None
        self.pending_prize_id = None
        self.history_list.clear()
        self.participant_count.update_count(len(self.participants))
        self._refresh_after_state_restore()

    def _refresh_after_state_restore(self):
        """保存状態に合わせ、賞品一覧・中央パネル・ルーレットを再描画する。"""
        current_prize = self.prizes[self.current_prize_index]
        current_remain = self.remaining_stocks[current_prize.prize_id]

        for prize in self.prizes:
            card = self.prize_cards_by_id[prize.prize_id]
            remain = self.remaining_stocks[prize.prize_id]
            if prize.prize_id not in self.revealed_prize_ids:
                card.update_prize(
                    f"{prize.rank}等", prize.list_name, prize.stock, "公開前🔒"
                )
                card.set_revealed(False)
                continue

            is_current = (
                self.current_prize_revealed
                and prize.prize_id == current_prize.prize_id
                and remain > 0
            )
            status = "抽選中" if is_current else "抽選済み" if remain == 0 else "未抽選"
            card.update_prize(f"{prize.rank}等", prize.list_name, prize.stock, status)
            card.set_revealed(True, status)
            card.set_active(is_current)

        if self.lottery.has_available_participant:
            self.roulette.set_participants(
                [participant.to_dict() for participant in self.lottery.available_participants]
            )
        else:
            self.roulette.reset()
        self.next_prize_button.show()
        self.next_prize_button.setEnabled(True)

        if not self.current_prize_revealed:
            self.roulette.show_title_placeholder()
            self.current_prize.hide()
            self.draw_button.hide()
            self.next_prize_button.setText("抽選会スタート")
            self.draw_status.set_waiting()
            return

        self.current_prize.show()
        self.current_prize.update_prize(
            f"{current_prize.rank}等",
            current_prize.current_name,
            self.drawn_counts[current_prize.prize_id],
            current_prize.stock,
        )
        self._scroll_current_prize_card_into_view(current_prize.prize_id)
        if current_remain > 0 and self.lottery.has_available_participant:
            self._prepare_same_prize_draw()
            return

        self.draw_button.hide()
        self.next_prize_button.setText("次の賞品へ")
        self.draw_status.set_completed()

    def _missing_required_csv_messages(self) -> list[str]:
        """紹介・抽選を始める前に必須CSVが配置済みか確認する。"""
        messages = []
        if not self.participants_csv_path.exists():
            messages.append("【！】参加者CSVが配置されていません")
        if not self.prizes_csv_path.exists():
            messages.append("【！】景品用CSVが配置されていません")
        return messages

    @staticmethod
    def _load_initial_participants(csv_path: Path) -> list[Participant]:
        """participants.csv を読み込み、未配置時は空の参加者リストを返す。"""
        if csv_path.exists():
            return load_participants(csv_path)

        return []

    def closeEvent(self, event):  # noqa: N802 - Qt override
        """ウィンドウ右上の閉じる操作時に終了確認を表示する。"""
        choice = QMessageBox.question(
            self,
            "アプリ終了の確認",
            "アプリを終了しますか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if choice == QMessageBox.StandardButton.Yes:
            event.accept()
        else:
            event.ignore()
        
