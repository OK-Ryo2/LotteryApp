from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


class WinnerDisplay(QFrame):
    """抽選の状態と現在の当選者を表示するWidget。"""

    def __init__(self):
        super().__init__()

        self.setObjectName("winnerDisplay")
        self.setMinimumHeight(190)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(8)

        self.status_label = QLabel("抽選中")
        self.status_label.setObjectName("winnerStatus")
        self.status_label.setAlignment(Qt.AlignCenter)

        self.department_label = QLabel("")
        self.department_label.setObjectName("winnerDepartment")
        self.department_label.setAlignment(Qt.AlignCenter)

        self.winner_name_label = QLabel("？？？")
        self.winner_name_label.setObjectName("winnerName")
        self.winner_name_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(self.status_label)
        layout.addStretch(1)
        layout.addWidget(self.department_label)
        layout.addWidget(self.winner_name_label)
        layout.addStretch(1)

    def set_drawing(self):
        """抽選開始時の表示へ切り替える。"""
        self.status_label.setText("抽選中")
        self.department_label.clear()
        self.winner_name_label.setText("？？？")

    def show_winner(self, winner_name: str, department: str):
        """抽選停止後、確定した当選者を表示する。"""
        self.status_label.setText("おめでとうございます！")
        self.department_label.setText(department)
        self.winner_name_label.setText(f"{winner_name} さん")

    def reset(self):
        """次の抽選を始める前の表示へ戻す。"""
        self.status_label.setText("抽選中")
        self.department_label.clear()
        self.winner_name_label.setText("？？？")
