"""Application entry point for the KanBan desktop app."""

from __future__ import annotations


def main() -> int:
    """Create the Qt application, show the main window, and run the loop.

    Theme application is owned by :class:`MainWindow`, which applies the
    user's stored preference (system/light/dark) during construction.
    """
    from PySide6.QtWidgets import QApplication

    from kanban.main_window import MainWindow

    app = QApplication([])
    app.setApplicationName("KanBan")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
