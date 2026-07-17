import secrets

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout


class Roulette(QFrame):
    """中央の候補者と前後2名ずつを表示する抽選ルーレット。"""

    _SAMPLE_PARTICIPANTS = [
        {"id": "sample-1", "name": "佐藤 健二", "department": "営業部"},
        {"id": "sample-2", "name": "鈴木 花子", "department": "人事部"},
        {"id": "sample-3", "name": "山田 太郎", "department": "開発部"},
        {"id": "sample-4", "name": "田中 美咲", "department": "総務部"},
        {"id": "sample-5", "name": "伊藤 輔", "department": "経理部"},
        {"id": "sample-6", "name": "中村 陽介", "department": "企画部"},
        {"id": "sample-7", "name": "高橋 恒一", "department": "営業部"},
    ]

    def __init__(self, participants: list[dict[str, str]] | None = None):
        super().__init__()

        self.setObjectName("roulette")
        self.setMinimumHeight(250)

        self.participants = participants or self._SAMPLE_PARTICIPANTS
        self.current_index = 0
        self.is_spinning = False
        self._candidate_cards: list[QFrame] = []

        self.timer = QTimer(self)
        self.timer.setInterval(90)
        self.timer.timeout.connect(self._advance)

        self.cards_layout = QHBoxLayout(self)
        self.cards_layout.setContentsMargins(18, 18, 18, 18)
        self.cards_layout.setSpacing(10)
        self._refresh_candidates()

    def start(self):
        """候補の切り替えを開始する。"""
        if self.is_spinning:
            return

        self.is_spinning = True
        self.timer.start()

    def stop(self) -> dict[str, str]:
        """候補の切り替えを停止し、中央の参加者を返す。"""
        self.timer.stop()
        self.is_spinning = False
        return self.current_participant

    def reset(self):
        """次の抽選用に先頭の候補へ戻す。"""
        self.timer.stop()
        self.is_spinning = False
        self.current_index = 0
        self._refresh_candidates()

    def set_participants(self, participants: list[dict[str, str]]):
        """抽選対象を差し替え、ランダムな候補位置から表示し直す。"""
        if not participants:
            raise ValueError("抽選対象の参加者がいません。")

        self.participants = participants
        self.timer.stop()
        self.is_spinning = False
        self.current_index = secrets.randbelow(len(self.participants))
        self._refresh_candidates()

    @property
    def current_participant(self) -> dict[str, str]:
        return self.participants[self.current_index]

    def _advance(self):
        self.current_index = (self.current_index + 1) % len(self.participants)
        self._refresh_candidates()

    def _refresh_candidates(self):
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._candidate_cards.clear()
        for offset in (-2, -1, 0, 1, 2):
            participant = self.participants[
                (self.current_index + offset) % len(self.participants)
            ]
            is_current = offset == 0
            card = self._create_candidate_card(participant, is_current)
            self._candidate_cards.append(card)
            self.cards_layout.addWidget(card, 2 if is_current else 1)

    def _create_candidate_card(
        self, participant: dict[str, str], is_current: bool
    ) -> QFrame:
        card = QFrame()
        card.setObjectName("rouletteCurrentCandidate" if is_current else "rouletteCandidate")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 12, 8, 10)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignCenter)

        name_label = QLabel("\n".join(participant["name"].replace(" ", "")))
        name_label.setObjectName("rouletteCurrentName" if is_current else "rouletteName")
        name_label.setAlignment(Qt.AlignCenter)

        department_label = QLabel(participant["department"])
        department_label.setObjectName(
            "rouletteCurrentDepartment" if is_current else "rouletteDepartment"
        )
        department_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(name_label, 1)
        layout.addWidget(department_label)
        return card
