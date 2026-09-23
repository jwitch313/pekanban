"""A distinct top-level window that displays the PeKanBan user manual.

The manual (``docs/user_manual.md``) is rendered to HTML by the small,
dependency-free converter in :mod:`kanban.ui.markdown` and shown in a
:class:`QTextBrowser`. The window is a normal top-level window (``Qt.Window``)
so it appears as its own display window, separate from the main window.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QTextBrowser, QVBoxLayout, QWidget

from kanban.assets import doc_path
from kanban.ui.markdown import markdown_to_html

#: The manual file bundled with the application.
MANUAL_NAME = "user_manual.md"


def load_manual_text() -> str:
    """Return the raw Markdown text of the bundled user manual.

    Returns an empty string if the manual cannot be found (for example, if it
    was not bundled into a frozen build).
    """
    path: Path = doc_path(MANUAL_NAME)
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


class HelpWindow(QWidget):
    """A top-level window showing the rendered user manual."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("helpWindow")
        self.setWindowTitle("PeKanBan — Help")
        self.setWindowFlag(Qt.WindowType.Window, True)
        self.resize(720, 640)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._browser = QTextBrowser()
        self._browser.setObjectName("helpBrowser")
        self._browser.setOpenExternalLinks(True)
        self._browser.setFrameShape(QFrame.Shape.NoFrame)
        layout.addWidget(self._browser)

        self._render()

    def _render(self) -> None:
        """Load and render the manual into the browser."""
        text = load_manual_text()
        if not text:
            body = "<p>The user manual could not be found.</p>"
        else:
            body = markdown_to_html(text)
        self._browser.setHtml(
            "<html><body style='margin:16px;'>"
            "<style>"
            "body { font-family: 'Segoe UI', sans-serif; line-height: 1.5; }"
            "h1 { font-size: 22px; } h2 { font-size: 18px; } h3 { font-size: 15px; }"
            "code { font-family: Consolas, monospace; }"
            "pre { padding: 8px; border-radius: 6px; }"
            "table { border-collapse: collapse; }"
            "th, td { border: 1px solid #888; padding: 4px 10px; }"
            "blockquote { margin-left: 12px; padding-left: 12px; border-left: 3px solid #888; }"
            "a { color: #2f6fed; }"
            "</style>"
            f"{body}"
            "</body></html>"
        )
