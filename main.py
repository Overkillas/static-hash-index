import sys

from PyQt6.QtWidgets import QApplication

from ui.main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)

    app.setApplicationName("Indice Hash Estatico")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("UNIFOR — Universidade de Fortaleza")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
