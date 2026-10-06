import sys

from PySide6.QtWidgets import QApplication
from pathlib import Path
from ui.operator_window import OperatorWindow


def main():
    app = QApplication(sys.argv)

    qss_path = Path(__file__).parent / "styles" / "theme.qss"

    with open(qss_path, "r", encoding="utf-8") as f:
        stylesheet = f.read()

    texture_path = (
        Path(__file__).resolve().parents[1]
        / "assets"
        / "images"
        / "backgrounds"
        / "background_texture.png"
    ).as_posix()
    app.setStyleSheet(stylesheet.replace("{{BACKGROUND_TEXTURE}}", texture_path))

    window = OperatorWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
