"""扇形ホイールで候補者を表示するルーレットウィジェット。"""

from __future__ import annotations

import math
import random
from pathlib import Path
from time import monotonic

from PySide6.QtCore import QPointF, QTimer, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import QFrame, QSizePolicy


class Roulette(QFrame):
    """参加者を回転する扇形ホイールとして描画する。

    ``current_participant`` はホイール上部のポインターが指す候補者です。
    描画だけをこのウィジェットで担い、当選者の確定・除外は既存の Lottery
    ロジック側に委ねます。
    """

    _VISIBLE_SECTORS = 9
    _INITIAL_ROTATION_SPEED = 0.08
    _MAX_ROTATION_SPEED = 0.36
    _ACCELERATION_DURATION = 2.0
    _STOP_INITIAL_DECELERATION = 0.002
    _STOP_DECELERATION_STEP = 0.000025
    _STOP_MAX_DECELERATION = 0.012
    _STOP_SPEED_THRESHOLD = 0.001
    stopped = Signal(dict)
    acceleration_completed = Signal()
    candidate_changed = Signal(dict)

    def __init__(self, participants: list[dict[str, str]] | None = None):
        super().__init__()

        self.setObjectName("roulette")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._base_minimum_height: int | None = None

        # 初回表示だけはCSVの行順ではなく、ランダムな並びで扇形に配置する。
        # 次回以降の並びは set_participants の既存処理に任せる。
        self.participants = list(participants or [])
        random.SystemRandom().shuffle(self.participants)
        self._last_selected_id: str | None = None
        self.current_index = 0
        self.rotation_position = 0.0
        self.is_spinning = False
        self.is_stopping = False
        self.is_accelerating = False
        self._rotation_speed = 0.0
        self._last_tick_at: float | None = None
        self._stop_deceleration = 0.0
        self._acceleration_elapsed = 0.0
        self._stop_requested = False
        self._scale = 1.0
        project_root = Path(__file__).resolve().parents[3]
        self._title_pixmap = QPixmap(
            str(project_root / "assets" / "images" / "ui" / "title.png")
        )
        self._show_title_placeholder = True
        self._winner_flash_active = False
        self._winner_flash_white = False
        # 停止後、当選ポップアップが閉じるまで中央カードを強調サイズで維持する。
        self._winner_pending = False
        self._winner_flash_timer = QTimer(self)
        self._winner_flash_timer.setInterval(55)
        self._winner_flash_timer.timeout.connect(self._toggle_winner_flash)
        self._show_completion = False
        self._completion_offset = 0
        confetti_path = project_root / "assets" / "images" / "effects" / "kamifubuki.png"
        self._completion_confetti = self._extract_gold_confetti(
            QPixmap(str(confetti_path))
        )
        self._completion_timer = QTimer(self)
        self._completion_timer.setInterval(33)
        self._completion_timer.timeout.connect(self._advance_completion_confetti)

        # 景品切替時に、旧ルーレットから新しい参加者列へ横方向にスライドさせる状態。
        self._transition_old_pixmap = QPixmap()
        self._transition_progress = 1.0
        self._transition_duration_ms = 480
        self._transition_elapsed_ms = 0
        self._transition_timer = QTimer(self)
        self._transition_timer.setInterval(16)
        self._transition_timer.timeout.connect(self._advance_transition)
        self._transition_rendering = False
        self._roulette_initialized = False
        self._suppress_next_transition = False

        self.timer = QTimer(self)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self._advance)

    def show_title_placeholder(self):
        """起動直後用に、ルーレットの代わりとなるタイトル画像を表示する。"""
        self.timer.stop()
        self.stop_winner_flash()
        self._completion_timer.stop()
        self._stop_transition()
        self._show_completion = False
        self._show_title_placeholder = True
        self.update()

    def show_roulette(self):
        """賞品の抽選開始が確定した後に、ルーレットの描画を表示する。"""
        self._show_title_placeholder = False
        # 初回の賞品紹介後だけは、タイトル画像からの切替なので退場演出を出さない。
        if not self._roulette_initialized:
            self._suppress_next_transition = True
            self._roulette_initialized = True
        self.stop_winner_flash()
        self._show_completion = False
        self._completion_timer.stop()
        self._stop_transition()
        self.update()

    def start_winner_flash(self):
        """停止後の選択中カード点滅を開始する。"""
        self._winner_flash_active = True
        self._winner_flash_white = False
        self._winner_flash_timer.start()
        self.update()

    def stop_winner_flash(self):
        """選択中カードの点滅を停止する。"""
        self._winner_flash_timer.stop()
        self._winner_flash_active = False
        self._winner_flash_white = False
        self.update()

    def _toggle_winner_flash(self):
        self._winner_flash_white = not self._winner_flash_white
        self.update()

    def show_completion(self):
        """抽選完了メッセージと紙吹雪を表示し、ルーレットを隠す。"""
        self.timer.stop()
        self.is_spinning = False
        self.is_stopping = False
        self._show_title_placeholder = False
        self._show_completion = True
        self._completion_offset = 0
        self._completion_timer.start()
        self.update()

    def _advance_completion_confetti(self):
        if self.height() <= 0:
            return
        self._completion_offset = (
            self._completion_offset + max(1, round(self.height() / 180))
        ) % self.height()
        self.update()

    def start(self):
        """ホイールの回転を開始する。"""
        if self.is_spinning or not self.participants:
            return

        self.rotation_position = float(self.current_index)
        # 開始後2秒で最高速に達する加速演出を行う。
        self._rotation_speed = self._INITIAL_ROTATION_SPEED
        self._last_tick_at = monotonic()
        self.is_spinning = True
        self.is_stopping = False
        self.is_accelerating = True
        self._stop_deceleration = 0.0
        self._acceleration_elapsed = 0.0
        self._stop_requested = False
        self.timer.start()
        self.update()

    def stop(self) -> dict[str, str]:
        """即時停止する互換用メソッド。通常の操作では request_stop を使う。"""
        self.timer.stop()
        self.is_spinning = False
        self.is_stopping = False
        self.is_accelerating = False
        self._rotation_speed = 0.0
        self._stop_deceleration = 0.0
        self._acceleration_elapsed = 0.0
        self._stop_requested = False
        self._last_tick_at = None
        self.current_index = int(math.floor(self.rotation_position + 0.5)) % len(
            self.participants
        )
        self._last_selected_id = self.participants[self.current_index]["id"]
        self._winner_pending = True
        # 描画位置を整数へ丸めると最後に逆方向へ戻ったように見えるため、
        # 停止直前の位置をそのまま保つ。
        self.update()
        return self.current_participant

    def request_stop(self):
        """慣性を残して減速停止を開始し、停止完了時に ``stopped`` を通知する。"""
        if not self.is_spinning or self.is_stopping:
            return

        self._stop_requested = True
        # 加速中にストップされた場合も、最高速に達してから減速を始める。
        if not self.is_accelerating:
            self._begin_deceleration()

    def _begin_deceleration(self):
        """最高速から慣性減速へ切り替える。"""
        self.is_stopping = True
        self._stop_deceleration = self._STOP_INITIAL_DECELERATION

    def reset(self):
        """次の抽選用に停止状態へ戻す。"""
        self.timer.stop()
        self.is_spinning = False
        self.is_stopping = False
        self.is_accelerating = False
        self._rotation_speed = 0.0
        self._stop_deceleration = 0.0
        self._acceleration_elapsed = 0.0
        self._stop_requested = False
        self._last_tick_at = None
        self._last_selected_id = None
        self._winner_pending = False
        self._stop_transition()
        self._roulette_initialized = False
        self._suppress_next_transition = False
        self.current_index = 0
        self.rotation_position = 0.0
        self.update()

    def set_participants(self, participants: list[dict[str, str]], *, animate: bool = True):
        """候補者を更新し、前回当選者の隣接位置を初期位置にする。"""
        if not participants:
            raise ValueError("抽選対象者の候補がいません。")

        # 現在画面を保存してから参加者を差し替え、新しい列を右から滑り込ませる。
        # 初回（タイトル表示中）は保存せず、通常どおり即時反映する。
        old_pixmap = QPixmap()
        if (
            animate
            and not self._suppress_next_transition
            and not self._show_title_placeholder
            and self.isVisible()
            and self.width() > 0
        ):
            old_pixmap = self.grab()
        self._suppress_next_transition = False

        incoming_by_id = {participant["id"]: participant for participant in participants}
        previous_order = list(self.participants)
        anchor_index = next(
            (
                index
                for index, participant in enumerate(previous_order)
                if participant.get("id") == self._last_selected_id
            ),
            None,
        )
        # 現在の並び順を維持したまま当選者だけを除外し、新規候補を末尾へ追加する。
        preserved = [
            participant
            for participant in previous_order
            if participant.get("id") in incoming_by_id
        ]
        preserved_ids = {participant["id"] for participant in preserved}
        self.participants = preserved + [
            participant
            for participant in participants
            if participant["id"] not in preserved_ids
        ]
        self.timer.stop()
        self.is_spinning = False
        self.is_stopping = False
        self.is_accelerating = False
        self._rotation_speed = 0.0
        self._stop_deceleration = 0.0
        self._acceleration_elapsed = 0.0
        self._stop_requested = False
        self._last_tick_at = None
        self.current_index = (anchor_index or 0) % len(self.participants)
        self.rotation_position = float(self.current_index)
        # 当選者を除外して新しい中央カードへ移ったため、初期選択サイズに戻す。
        self._winner_pending = False
        if not old_pixmap.isNull():
            self._transition_old_pixmap = old_pixmap
            self._transition_progress = 0.0
            self._transition_elapsed_ms = 0
            self._transition_timer.start()
        self.update()

    def _advance_transition(self):
        self._transition_elapsed_ms += self._transition_timer.interval()
        self._transition_progress = min(
            1.0, self._transition_elapsed_ms / self._transition_duration_ms
        )
        if self._transition_progress >= 1.0:
            self._stop_transition()
        self.update()

    def _stop_transition(self):
        self._transition_timer.stop()
        self._transition_old_pixmap = QPixmap()
        self._transition_progress = 1.0
        self._transition_elapsed_ms = 0
        self._transition_rendering = False

    def set_scale(self, scale: float):
        """画面サイズに合わせてホイールと文字の最小表示領域を調整する。"""
        self._scale = max(0.7, min(scale, 1.15))
        if self._base_minimum_height is None:
            self.ensurePolished()
            self._base_minimum_height = self.minimumHeight()
        self.setMinimumHeight(max(150, round(self._base_minimum_height * self._scale)))
        self.update()

    @property
    def current_participant(self) -> dict[str, str]:
        index = int(math.floor(self.rotation_position + 0.5)) % len(self.participants)
        return self.participants[index]

    def _advance(self):
        # 描画負荷でタイマー間隔が変わっても、実時間に対して一定の速さで回す。
        now = monotonic()
        elapsed = min(0.08, max(0.0, now - (self._last_tick_at or now)))
        self._last_tick_at = now

        if self.is_accelerating:
            self._acceleration_elapsed += elapsed
            progress = min(1.0, self._acceleration_elapsed / self._ACCELERATION_DURATION)
            # 始めは緩やかに、最高速へ向けて自然に加速する。
            eased_progress = 1.0 - math.pow(1.0 - progress, 2)
            self._rotation_speed = self._INITIAL_ROTATION_SPEED + (
                self._MAX_ROTATION_SPEED - self._INITIAL_ROTATION_SPEED
            ) * eased_progress
            if progress >= 1.0:
                self.is_accelerating = False
                self._rotation_speed = self._MAX_ROTATION_SPEED
                if self._stop_requested:
                    self._begin_deceleration()
                self.acceleration_completed.emit()

        # 停止要求後は、フレームごとに減速率を徐々に強める。
        # 経過秒数は停止判定に使わず、十分に低い速度になった時点で止める。
        if self.is_stopping:
            tick_scale = elapsed / 0.016
            self._rotation_speed *= math.pow(
                1.0 - self._stop_deceleration,
                tick_scale,
            )
            self._stop_deceleration = min(
                self._STOP_MAX_DECELERATION,
                self._stop_deceleration + self._STOP_DECELERATION_STEP * tick_scale,
            )

        # 加速・減速を問わず、最高速を超えないようにする。
        self._rotation_speed = min(self._rotation_speed, self._MAX_ROTATION_SPEED)

        self.rotation_position += self._rotation_speed * elapsed / 0.016
        self.update()
        self.candidate_changed.emit(self.current_participant)

        if self.is_stopping and self._rotation_speed <= self._STOP_SPEED_THRESHOLD:
            selected_participant = self.stop()
            self.stopped.emit(selected_participant)

    def paintEvent(self, event):  # noqa: N802 - Qt のオーバーライド名
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.contentsRect()
        if rect.width() < 80 or rect.height() < 80:
            return

        # 切替中は新しいルーレットを通常描画し、切替前の画面を中央へ
        # 縮小・透明化させながら重ねる。これにより当選者除外が視覚的に伝わる。
        transition_active = (
            not self._transition_old_pixmap.isNull()
            and not self._transition_rendering
        )

        if self._show_completion:
            self._paint_completion(painter, rect)
            if transition_active:
                self._paint_transition_overlay(painter, rect)
            return

        if not self.participants:
            return

        if self._show_title_placeholder:
            self._paint_title_placeholder(painter, rect)
            return

        center_x = rect.center().x()
        center_y = rect.bottom() + rect.height() * 0.16
        radius = min(rect.width() * 0.66, rect.height() * 1.12)
        inner_radius = max(46 * self._scale, radius * 0.31)
        sector_angle = 17.0
        center_angle = -90.0

        # 扇形を囲む弧。背景パネルの上に輪郭だけを重ね、透過テクスチャを生かす。
        # ルーレット扇形全体の外周弧の線色。
        painter.setPen(QPen(QColor("#b58c38"), max(1.0, 1.6 * self._scale)))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawArc(
            rect.adjusted(
                int(rect.width() * 0.04),
                int(-radius * 0.68),
                int(-rect.width() * 0.04),
                int(radius * 0.30),
            ),
            200 * 16,
            140 * 16,
        )

        base_index = math.floor(self.rotation_position)
        fraction = self.rotation_position - base_index
        selected_index = int(math.floor(self.rotation_position + 0.5)) % len(
            self.participants
        )
        visible_half = self._VISIBLE_SECTORS // 2

        for offset in range(-visible_half, visible_half + 1):
            participant_index = (base_index + offset) % len(self.participants)
            relative = offset - fraction
            angle = center_angle + relative * sector_angle
            selected = participant_index == selected_index and abs(relative) < 0.52
            self._paint_sector(
                painter,
                center_x,
                center_y,
                radius,
                inner_radius,
                angle,
                sector_angle,
                self.participants[participant_index],
                selected,
            )

        # ホイールの中心を覆って、扇形の下端を自然に整える。
        # ルーレット根本の半円（中央円）の輪郭線色。
        painter.setPen(QPen(QColor("#c49a42"), max(1.0, 1.5 * self._scale)))
        # ルーレット根本の半円（中央円）の塗りつぶし色。
        painter.setBrush(QColor("#0a1525"))
        painter.drawEllipse(
            QPointF(center_x, center_y), inner_radius * 0.72, inner_radius * 0.72
        )

        # 中央上部のポインター。停止時は金色のカードがこの位置に揃う。
        # 先端を下向きの逆三角形として描画する。従来の先端位置の約3倍まで延長する。
        pointer_width = max(8.0, 13.0 * self._scale)
        pointer_length = pointer_width * 7.35
        pointer_top = rect.top() + 7
        pointer_bottom = pointer_top + pointer_length
        pointer_gradient = QLinearGradient(0, pointer_top, 0, pointer_bottom)
        # 中央上部ポインターの光沢グラデーション（上から下）。
        pointer_gradient.setColorAt(0.0, QColor("#fff4b0"))
        pointer_gradient.setColorAt(0.22, QColor("#ffffff"))
        pointer_gradient.setColorAt(0.42, QColor("#f4c94f"))
        pointer_gradient.setColorAt(1.0, QColor("#9b6514"))
        # 中央上部ポインターの外枠線色。
        painter.setPen(QPen(QColor("#0F0F0F"), 1))
        painter.setBrush(pointer_gradient)
        painter.drawPolygon(
            [
                QPointF(center_x - pointer_width, pointer_top),
                QPointF(center_x + pointer_width, pointer_top),
                QPointF(center_x, pointer_bottom),
            ]
        )
        if transition_active:
            self._paint_transition_overlay(painter, rect)

    def _paint_transition_overlay(self, painter: QPainter, rect):
        """中央の当選者カードだけを発光させ、拡大後に縮小・透明化する。"""
        if self._transition_old_pixmap.isNull():
            return

        progress = self._transition_progress
        # ルーレット中央付近だけを切り出す。扇形カードの周辺を含めた
        # 狭い帯にすることで、ルーレット全体ではなく対象者だけが退場して見える。
        source_rect = self._transition_old_pixmap.rect()
        crop_x = round(source_rect.width() * 0.34)
        crop_y = round(source_rect.height() * 0.18)
        crop_w = round(source_rect.width() * 0.32)
        crop_h = max(1, source_rect.height() - crop_y)
        old_card = self._transition_old_pixmap.copy(crop_x, crop_y, crop_w, crop_h)
        center_x = rect.x() + round(rect.width() * 0.50)
        center_y = rect.y() + crop_y + crop_h // 2
        # 前半で少し拡大して注目させ、後半で一気に縮小する。
        if progress < 0.24:
            scale = 1.0 + 0.18 * (progress / 0.24)
        else:
            scale = 1.18 * max(0.04, 1.0 - (progress - 0.24) / 0.76)
        width = max(1, round(crop_w * scale))
        height = max(1, round(crop_h * scale))
        old_scaled = old_card.scaled(
            width,
            height,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        target_x = center_x - width // 2
        target_y = center_y - height // 2
        painter.save()
        # 発光は冒頭で強くし、縮小とともに消す。
        glow = max(0.0, 1.0 - progress / 0.7)
        painter.setPen(
            QPen(QColor(255, 220, 94, round(210 * glow)), max(3.0, 7.0 * glow))
        )
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(
            target_x - round(8 * glow),
            target_y - round(8 * glow),
            width + round(16 * glow),
            height + round(16 * glow),
            12,
            12,
        )
        painter.setOpacity(max(0.0, 1.0 - progress))
        painter.drawPixmap(target_x, target_y, old_scaled)
        painter.restore()

    def _paint_completion(self, painter: QPainter, rect):
        """ルーレット部分に抽選完了メッセージと循環紙吹雪を描画する。"""
        if not self._completion_confetti.isNull():
            tile = self._completion_confetti.scaled(
                rect.size(),
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            y = self._completion_offset - tile.height()
            while y < rect.height():
                painter.drawPixmap(rect.left(), rect.top() + y, tile)
                y += tile.height()

        font = painter.font()
        font.setPointSize(max(18, round(30 * self._scale)))
        font.setBold(True)
        painter.setFont(font)
        # 抽選完了メッセージの文字色。
        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(
            rect,
            Qt.AlignmentFlag.AlignCenter,
            "抽選会は以上になります\nご参加ありがとうございました！",
        )

    @staticmethod
    def _extract_gold_confetti(source: QPixmap) -> QPixmap:
        """紙吹雪画像から金色部分だけを抽出して透明背景にする。"""
        if source.isNull():
            return source

        image = source.toImage().convertToFormat(QImage.Format.Format_ARGB32)
        result = QImage(image.size(), QImage.Format.Format_ARGB32)
        result.fill(Qt.GlobalColor.transparent)
        for y in range(image.height()):
            for x in range(image.width()):
                color = image.pixelColor(x, y)
                hue, saturation, value, alpha = color.getHsvF()
                if (
                    alpha > 0
                    and 0.035 <= hue <= 0.20
                    and saturation >= 0.16
                    and value >= 0.22
                ):
                    color.setAlpha(round(alpha * 255))
                    result.setPixelColor(x, y, color)
        return QPixmap.fromImage(result)

    def _paint_title_placeholder(self, painter: QPainter, rect):
        """領域内でタイトル画像を最大表示し、起動直後の案内画面にする。"""
        if self._title_pixmap.isNull():
            return

        scaled = self._title_pixmap.scaled(
            rect.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        painter.drawPixmap(
            rect.x() + (rect.width() - scaled.width()) // 2,
            rect.y() + (rect.height() - scaled.height()) // 2,
            scaled,
        )

    def _paint_sector(
        self,
        painter: QPainter,
        center_x: float,
        center_y: float,
        radius: float,
        inner_radius: float,
        angle: float,
        sector_angle: float,
        participant: dict[str, str],
        selected: bool,
    ):
        """1 人分の扇形カードと、縦書きの氏名・部署名を描く。"""
        half_angle = math.radians(sector_angle * 0.49)
        outer_width = 2 * radius * math.sin(half_angle)
        inner_width = 2 * inner_radius * math.sin(half_angle)

        painter.save()
        painter.translate(center_x, center_y)
        painter.rotate(angle + 90)

        path = QPainterPath()
        path.moveTo(-outer_width / 2, -radius)
        path.lineTo(outer_width / 2, -radius)
        path.lineTo(inner_width / 2, -inner_radius)
        path.lineTo(-inner_width / 2, -inner_radius)
        path.closeSubpath()

        gradient = QLinearGradient(0, -radius, 0, -inner_radius)
        if selected:
            if self._winner_flash_active and self._winner_flash_white:
                # 当選確定待ちの点滅中は白背景・黒文字に切り替える。
                gradient.setColorAt(0.0, QColor("#FFFFFF"))
                gradient.setColorAt(1.0, QColor("#FFFFFF"))
                border = QColor("#FFFFFF")
                text_color = QColor("#15243a")
            else:
                # 選択中（中央）の扇形カードの塗りつぶしグラデーション。
                gradient.setColorAt(0.0, QColor("#f6d870"))
                gradient.setColorAt(0.52, QColor("#d4a62d"))
                gradient.setColorAt(1.0, QColor("#8c6320"))
                # 選択中カードの境界線色・文字色。
                border = QColor("#ffe69a")
                text_color = QColor("#15243a")
        else:
            # 通常の扇形カードの塗りつぶしグラデーション。
            gradient.setColorAt(0.0, QColor("#25446e"))
            gradient.setColorAt(1.0, QColor("#0c1a2d"))
            # 通常カードの境界線色・文字色。
            border = QColor("#09E4E9")
            text_color = QColor("#f5f1e7")

        painter.setPen(QPen(border, max(1.0, 1.4 * self._scale)))
        painter.setBrush(gradient)
        painter.drawPath(path)

        name = "".join(char for char in participant["name"] if not char.isspace())[:7]
        middle_radius = (radius + inner_radius) / 2
        text_width = max(42.0, (outer_width + inner_width) / 2 - 10)
        if selected:
            # 初期停止中は通常より控えめ、回転中～当選確定までは大きく表示する。
            selected_size = (
                32
                if (
                    self.is_spinning
                    or self.is_stopping
                    or self._winner_flash_active
                    or self._winner_pending
                )
                else 21
            )
            name_size = max(9, round(selected_size * self._scale))
        else:
            name_size = max(9, round(21 * self._scale))
        char_height = max(29, round(name_size * 1.35))
        painter.setPen(text_color)
        painter.setFont(QFont("Yu Mincho", name_size, QFont.Weight.Bold))
        name_start = -middle_radius - len(name) * char_height / 2
        for number, char in enumerate(name):
            painter.drawText(
                -text_width / 2,
                name_start + number * char_height,
                text_width,
                char_height,
                Qt.AlignmentFlag.AlignCenter,
                char,
            )

        department_base_size = (
            10 if selected and (self.is_spinning or self.is_stopping) else 9 if selected else 8
        )
        department_size = max(7, round(department_base_size * self._scale))
        painter.setFont(QFont("Meiryo", department_size))
        department_y = min(-inner_radius - 2, name_start + len(name) * char_height + 5)
        painter.drawText(
            -text_width / 2,
            department_y,
            text_width,
            max(12, round(16 * self._scale)),
            Qt.AlignmentFlag.AlignCenter,
            participant["department"],
        )
        painter.restore()
