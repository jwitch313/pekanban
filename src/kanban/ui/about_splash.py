"""A splash-style window that introduces PeKanBan and its author.

The splash shows the PeKanBan logo prominently above three lines of text. Each
line carries a hyperlink (the author's site, Instagram, and a PayPal tip link)
that opens in the system browser. The logo variant is chosen to match the
active theme so it stays legible on both light and dark backgrounds.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from kanban import __version__
from kanban.assets import asset_path
from kanban.ui.theme import ThemeMode

#: The three credit lines shown on the splash, as HTML with hyperlinks.
_CREDIT_LINES = (
    '<a href="https://JamesWitcher.com">App by James Witcher</a>',
    '<a href="https://www.instagram.com/jwitch313">Connect on Instagram @jWitch313</a>',
    (
        'If this app has brought you value, '
        '<a href="https://www.paypal.com/paypalme/JamesWitcher">buy me a shot</a> '
        "of bourbon. Thanks."
    ),
)


def _logo_name(mode: ThemeMode) -> str:
    """Return the logo asset name that suits the given theme."""
    return "logo-icon-dark.svg" if mode is ThemeMode.DARK else "logo-icon.svg"


def _render_logo(mode: ThemeMode, size: int = 128) -> QPixmap:
    """Render the theme-appropriate logo to a pixmap at ``size`` pixels."""
    renderer = QSvgRenderer(str(asset_path(_logo_name(mode))))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    if renderer.isValid():
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
    return pixmap


class AboutSplash(QWidget):
    """A top-level splash window with the logo and author credits."""

    def __init__(self, mode: ThemeMode = ThemeMode.LIGHT, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("aboutSplash")
        self.setWindowTitle("About PeKanBan")
        self.setWindowFlag(Qt.WindowType.Window, True)
        self.setFixedSize(360, 300)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        logo = QLabel()
        logo.setPixmap(_render_logo(mode))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo, 0, Qt.AlignmentFlag.AlignCenter)

        title = QLabel("PeKanBan")
        title.setObjectName("aboutTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        version = QLabel(f"Version {__version__}")
        version.setObjectName("aboutVersion")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version)

        layout.addSpacing(8)

        credits = QLabel()
        credits.setObjectName("aboutCredits")
        credits.setOpenExternalLinks(True)
        credits.setTextFormat(Qt.TextFormat.RichText)
        credits.setAlignment(Qt.AlignmentFlag.AlignCenter)
        credits.setWordWrap(True)
        credits.setText(
            "<div style='line-height:1.9;'>"
            + "<br/>".join(_CREDIT_LINES)
            + "</div>"
        )
        layout.addWidget(credits)
