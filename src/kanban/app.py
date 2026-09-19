"""Application entry point for the KanBan desktop app."""

from __future__ import annotations


def main() -> int:
    """Create the Qt application, show the main window, and run the loop."""
    from PySide6.QtWidgets import QApplication

    from kanban.main_window import MainWindow
    from kanban.ui.theme import apply_theme, detect_system_theme

    app = QApplication([])
    app.setApplicationName("KanBan")
    apply_theme(app, detect_system_theme())
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
