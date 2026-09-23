"""A splash-style window that introduces PeKanBan and its author.

The splash shows the PeKanBan logo prominently above three lines of text. Each
line carries a hyperlink (the author's site, Instagram, and a PayPal tip link)
that opens in the system browser. The logo variant, the link color, and the
native title-bar color are all chosen to match the active theme so the window
stays legible on both light and dark backgrounds.

The window is a fixed-size top-level dialog: it keeps only the close button
(minimize and maximize are removed) and is sized to fit its content so no line
of text ever wraps.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPixmap, QShowEvent
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from kanban import __version__
from kanban.assets import asset_path
from kanban.ui.theme import ThemeMode, title_bar_color
from kanban.ui.titlebar import set_title_bar_color

#: Link color per theme. Light blue on dark backgrounds, the app accent on light.
_LINK_COLORS: dict[ThemeMode, str] = {
    ThemeMode.LIGHT: "#2f6fed",
    ThemeMode.DARK: "#7aa5ff",
}


def _link_color(mode: ThemeMode) -> str:
    """Return the hyperlink color that suits the given theme."""
    return _LINK_COLORS[mode]


def _credit_html(link_color: str) -> str:
    """Build the three credit lines as HTML.

    Only the intended words are hyperlinks: the author's name, the Instagram
    handle, and the "buy me a shot" phrase. The surrounding text is plain.
    """
    lines = (
        f'App by <a href="https://JamesWitcher.com" style="color:{link_color};">'
        "James Witcher</a>",
        f'Connect on Instagram <a href="https://www.instagram.com/jwitch313" '
        f'style="color:{link_color};">@jWitch313</a>',
        (
            "If this app has brought you value, "
            f'<a href="https://www.paypal.com/paypalme/JamesWitcher" '
            f'style="color:{link_color};">buy me a shot</a> '
            "of bourbon. Thanks."
        ),
    )
    return "<div style='line-height:1.9;'>" + "<br/>".join(lines) + "</div>"


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
        self._mode = mode
        self.setObjectName("aboutSplash")
        self.setWindowTitle("About PeKanBan")
        # Keep only the close button; drop minimize and maximize entirely.
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.CustomizeWindowHint
            | Qt.WindowType.WindowCloseButtonHint
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._logo_label = QLabel()
        self._logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._logo_label, 0, Qt.AlignmentFlag.AlignCenter)

        title = QLabel("PeKanBan")
        title.setObjectName("aboutTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        version = QLabel(f"Version {__version__}")
        version.setObjectName("aboutVersion")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version)

        layout.addSpacing(8)

        self._credits_label = QLabel()
        self._credits_label.setObjectName("aboutCredits")
        self._credits_label.setOpenExternalLinks(True)
        self._credits_label.setTextFormat(Qt.TextFormat.RichText)
        self._credits_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._credits_label.setWordWrap(False)
        layout.addWidget(self._credits_label)

        self.set_theme_mode(mode)

        # Size the window to fit its content so no line of text wraps.
        self.adjustSize()
        self.setFixedSize(self.size())

    def set_theme_mode(self, mode: ThemeMode) -> None:
        """Re-apply the given theme: logo, link colors, and title-bar color.

        Called on construction and again each time the splash is shown, so the
        window always matches the app's active theme even if the theme changed
        after the splash was first created (the splash instance is cached).
        """
        self._mode = mode
        self._logo_label.setPixmap(_render_logo(mode))
        self._credits_label.setText(_credit_html(_link_color(mode)))
        if self.isVisible():
            set_title_bar_color(int(self.winId()), title_bar_color(mode))

    def showEvent(self, event: QShowEvent) -> None:  # noqa: N802 - Qt naming
        """Recolor the native Windows title bar to match the active theme."""
        super().showEvent(event)
        set_title_bar_color(int(self.winId()), title_bar_color(self._mode))
