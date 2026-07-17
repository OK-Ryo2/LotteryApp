from dataclasses import dataclass
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


@dataclass(frozen=True)
class HistoryEntry:
    rank: str
    prize_name: str
    winner_name: str
    won_at: datetime


class HistoryList(QFrame):
    """直近6件の当選履歴を表示するWidget。"""

    MAX_ENTRIES = 6

    def __init__(self):
        super().__init__()

        self.setObjectName("historyList")
        self.entries: list[HistoryEntry] = []

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(8, 8, 8, 8)
        self.layout.setSpacing(0)
        self.layout.setAlignment(Qt.AlignTop)

    def add_entry(
        self,
        rank: str,
        prize_name: str,
        winner_name: str,
        won_at: datetime,
    ):
        """履歴を先頭へ追加し、7件目以降は破棄する。"""
        self.entries.insert(0, HistoryEntry(rank, prize_name, winner_name, won_at))
        del self.entries[self.MAX_ENTRIES :]
        self._refresh()

    def _refresh(self):
        while self.layout.count():
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for entry in self.entries:
            self.layout.addWidget(self._create_card(entry))
        self.layout.addStretch()

    @staticmethod
    def _create_card(entry: HistoryEntry) -> QFrame:
        card = QFrame()
        card.setObjectName("historyCard")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(2)

        prize_label = QLabel(f"{entry.rank}　{entry.prize_name}")
        prize_label.setObjectName("historyPrize")

        winner_label = QLabel(f"{entry.winner_name} さん")
        winner_label.setObjectName("historyWinner")

        time_label = QLabel(entry.won_at.strftime("%H:%M"))
        time_label.setObjectName("historyTime")

        layout.addWidget(prize_label)
        layout.addWidget(winner_label)
        layout.addWidget(time_label)
        return card
