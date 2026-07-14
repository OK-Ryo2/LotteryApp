import sys

from PySide6.QtWidgets import QApplication
from pathlib import Path
from ui.operator_window import OperatorWindow


def main():
    app = QApplication(sys.argv)

    qss_path = Path(__file__).parent / "styles" / "theme.qss"

    with open(qss_path, "r", encoding="utf-8") as f:
        app.setStyleSheet(f.read())

    window = OperatorWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()