from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QImage, QMovie, QPainter, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QFrame,
    QPushButton,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)


class _ConfettiCanvas(QWidget):
    """金色部分を繰り返し描画し、上から下へ連続スクロールさせる背景。"""

    def __init__(self, pixmap: QPixmap, gif_path: str | None = None, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setObjectName("winnerDialogConfetti")
        self._pixmap = pixmap
        self._movie = QMovie(gif_path, parent=self) if gif_path else None
        if self._movie is not None:
            self._movie.setCacheMode(QMovie.CacheMode.CacheAll)
            self._movie.frameChanged.connect(self.update)
        self._offset = 0
        self._timer = QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._advance)

    def _advance(self):
        # confetti.gifは先頭フレームを固定表示するため、更新しない。
        return

    def start(self):
        self._timer.stop()
        if self._movie is not None:
            self._movie.start()

    def stop(self):
        self._timer.stop()
        if self._movie is not None:
            self._movie.stop()

    def paintEvent(self, event):  # noqa: N802 - Qt override
        frame = self._movie.currentPixmap() if self._movie is not None else self._pixmap
        if frame.isNull() or self.width() <= 0 or self.height() <= 0:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        tile = frame.scaled(
            self.size(),
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        y = self._offset - tile.height()
        while y < self.height():
            painter.drawPixmap(0, y, tile)
            y += tile.height()


class WinnerDialog(QDialog):
    """当選者をモーダル表示するポップアップ。"""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setObjectName("winnerDialog")
        self.setWindowTitle("")
        self.setModal(True)

        # 紙吹雪はダイアログの最背面に薄く表示し、内容の可読性を保つ。
        confetti_path = (
            Path(__file__).resolve().parents[3]
            / "assets"
            / "images"
            / "effects"
            / "confetti.gif"
        )
        # QPixmapはGIFの先頭フレームだけを読み込み、アニメーションさせずに表示する。
        self._confetti_pixmap = QPixmap(str(confetti_path))
        self._confetti_canvas = _ConfettiCanvas(
            self._confetti_pixmap, str(confetti_path), self
        )
        self._confetti_canvas.show()

        self._content_frame = QFrame(self)
        self._content_frame.setObjectName("winnerDialogContent")
        layout = QVBoxLayout(self._content_frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.status_label = QLabel("🎉おめでとうございます！🎉")
        self.status_label.setObjectName("winnerDialogStatus")
        self.status_label.setAlignment(Qt.AlignCenter)

        self.department_label = QLabel()
        self.department_label.setObjectName("winnerDialogDepartment")
        self.department_label.setAlignment(Qt.AlignCenter)

        self.winner_name_label = QLabel()
        self.winner_name_label.setObjectName("winnerDialogName")
        self.winner_name_label.setAlignment(Qt.AlignCenter)

        close_button = QPushButton("閉じる")
        close_button.setObjectName("winnerDialogClose")
        close_button.clicked.connect(self.accept)

        #layout.addWidget(self.status_label)
        #layout.addStretch(1)
        #layout.addWidget(self.department_label)
        #layout.addWidget(self.winner_name_label)
        #layout.addStretch(1)
        #layout.addWidget(close_button, alignment=Qt.AlignCenter)
        
        # 1. 一番上にStretchを入れて、要素全体を押し下げる
        layout.addStretch(1)
        layout.addWidget(self.status_label)
        
        # 2. ①と②の間の幅を指定（20pxなど、お好みで調整してください）
        layout.addSpacing(20) 
        layout.addWidget(self.department_label)
        layout.addWidget(self.winner_name_label)
        
        # 3. ②と③の間の幅を指定（30pxなど、お好みで調整してください）
        layout.addSpacing(30)
        layout.addWidget(close_button, alignment=Qt.AlignCenter)
        # 4. 一番下にStretchを入れて、要素全体を押し上げる（上下のStretchで中央配置になる）
        layout.addStretch(1)
        
        
        # QDialog本体の背景に隠れないよう紙吹雪を前面へ置き、内容をその上に重ねる。
        for content_widget in (
            self.status_label,
            self.department_label,
            self.winner_name_label,
            close_button,
        ):
            content_widget.raise_()

        stacked_layout = QStackedLayout(self)
        stacked_layout.setContentsMargins(0, 0, 0, 0)
        stacked_layout.setStackingMode(QStackedLayout.StackingMode.StackAll)
        stacked_layout.addWidget(self._confetti_canvas)
        stacked_layout.addWidget(self._content_frame)
        # StackAllでは追加順が環境により異なるため、表示順を明示する。
        self._confetti_canvas.lower()
        self._content_frame.raise_()

    def _update_confetti_background(self):
        """ダイアログ全体に合わせて紙吹雪画像を拡大表示する。"""
        if self._confetti_pixmap.isNull() or self.width() <= 0 or self.height() <= 0:
            return
        self._confetti_canvas.setGeometry(self.rect())
        self._confetti_canvas.update()

    @staticmethod
    def _extract_gold_pixmap(source: QPixmap) -> QPixmap:
        """画像から金色の画素だけを残し、その他を完全透明にする。"""
        if source.isNull():
            return source

        image = source.toImage().convertToFormat(QImage.Format.Format_ARGB32)
        result = QImage(image.size(), QImage.Format.Format_ARGB32)
        result.fill(Qt.GlobalColor.transparent)

        for y in range(image.height()):
            for x in range(image.width()):
                color = image.pixelColor(x, y)
                hue, saturation, value, alpha = color.getHsvF()
                source_alpha = round(alpha * 255)
                # 金色（黄～橙）の色相だけを対象にし、白・黒・灰色は除外する。
                is_gold = (
                    source_alpha > 0
                    and 0.035 <= hue <= 0.20
                    and saturation >= 0.16
                    and value >= 0.22
                )
                if not is_gold:
                    continue

                # 金色のアンチエイリアスを残しつつ、彩度の低い背景を透明化する。
                preserved_alpha = min(
                    255,
                    round(source_alpha * min(1.0, saturation / 0.42)),
                )
                color.setAlpha(preserved_alpha)
                result.setPixelColor(x, y, color)

        return QPixmap.fromImage(result)

    def resizeEvent(self, event):  # noqa: N802 - Qtのオーバーライド
        super().resizeEvent(event)
        self._update_confetti_background()

    def showEvent(self, event):  # noqa: N802 - Qtのオーバーライド
        super().showEvent(event)
        self._update_confetti_background()
        self._confetti_canvas.lower()
        self._content_frame.raise_()
        self._confetti_canvas.start()

    def hideEvent(self, event):  # noqa: N802 - Qt override
        self._confetti_canvas.stop()
        super().hideEvent(event)

    def show_winner(self, winner_name: str, department: str):
        """当選者の内容をセットして親ウィンドウに合わせた大きさで表示する。"""
        self.department_label.setText(department)
        self.winner_name_label.setText(f"{winner_name} さん")

        if self.parentWidget():
            parent_size = self.parentWidget().size()
            # 当選演出を目立たせるため、従来のポップアップ面積を1.5倍にする。
            # 小さい画面では親ウィンドウを超えないように上限を設ける。
            dialog_width = max(480, min(840, round(parent_size.width() * 0.51)))
            dialog_height = max(330, min(510, round(parent_size.height() * 0.48)))
            self.resize(
                min(dialog_width, round(parent_size.width() * 0.9)),
                min(dialog_height, round(parent_size.height() * 0.9)),
            )
        self.exec()
