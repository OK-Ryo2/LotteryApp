from dataclasses import dataclass
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout


@dataclass(frozen=True)
class HistoryEntry:
    rank: str
    prize_name: str
    department: str
    winner_name: str
    won_at: datetime


class HistoryList(QFrame):
    """当選履歴を新しい順に制限なく表示するWidget。"""

    def __init__(self):
        super().__init__()

        self.setObjectName("historyList")
        self.entries: list[HistoryEntry] = []
        self._scale = 1.0

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.layout.setAlignment(Qt.AlignTop)

    def add_entry(
        self,
        rank: str,
        prize_name: str,
        department: str,
        winner_name: str,
        won_at: datetime,
    ):
        """最新の履歴を先頭へ追加する。"""
        self.entries.insert(
            0,
            HistoryEntry(rank, prize_name, department, winner_name, won_at),
        )
        self._refresh()

    def clear(self):
        """表示中の当選履歴をすべて消去する。"""
        self.entries.clear()
        self._refresh()

    def restore_entries(self, entries: list[HistoryEntry]):
        """設定操作で保存済みの履歴表示へ戻す。"""
        self.entries = list(entries)
        self._refresh()

    def _refresh(self):
        while self.layout.count():
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for entry in self.entries:
            self.layout.addWidget(self._create_card(entry))
        self.layout.addStretch()

    def _create_card(self, entry: HistoryEntry) -> QFrame:
        card = QFrame()
        card.setObjectName("historyCard")
        if self._scale != 1.0:
            card.ensurePolished()
            card.setFixedHeight(round(card.minimumHeight() * self._scale))

        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        prize_label = QLabel(f"{entry.rank}　{entry.prize_name}")
        prize_label.setObjectName("historyPrize")

        winner_label = QLabel(f"{entry.winner_name} さん")
        winner_label.setObjectName("historyWinner")

        winner_row = QHBoxLayout()
        winner_row.setContentsMargins(0, 0, 0, 0)
        winner_row.setSpacing(8)

        department_label = QLabel(entry.department)
        department_label.setObjectName("historyDepartment")
        winner_row.addWidget(department_label)
        winner_row.addWidget(winner_label)
        winner_row.addStretch()

        time_label = QLabel(entry.won_at.strftime("%H:%M"))
        time_label.setObjectName("historyTime")

        layout.addWidget(prize_label)
        layout.addLayout(winner_row)
        layout.addWidget(time_label)
        return card

    def set_scale(self, scale: float):
        """画面の表示倍率に合わせて履歴カードの高さを更新する。"""
        if self._scale == scale:
            return
        self._scale = scale
        self._refresh()
