"""Tests for the Help window, About splash, markdown converter, and wiring."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from kanban.assets import doc_path
from kanban.ui.about_splash import AboutSplash
from kanban.ui.help_window import HelpWindow, load_manual_text
from kanban.ui.markdown import markdown_to_html
from kanban.ui.sidebar import Sidebar
from kanban.ui.theme import ThemeMode


# -- Markdown converter ---------------------------------------------------
def test_markdown_heading() -> None:
    assert markdown_to_html("# Title") == "<h1>Title</h1>"
    assert markdown_to_html("### Sub") == "<h3>Sub</h3>"


def test_markdown_paragraph() -> None:
    assert markdown_to_html("Hello world") == "<p>Hello world</p>"


def test_markdown_bold_italic() -> None:
    assert markdown_to_html("**bold** and *italic*") == "<p><b>bold</b> and <i>italic</i></p>"


def test_markdown_inline_code() -> None:
    assert markdown_to_html("Use `kanban.db` here") == "<p>Use <code>kanban.db</code> here</p>"


def test_markdown_code_fence() -> None:
    html = markdown_to_html("```\na < b\n```")
    assert "<pre><code>" in html
    assert "a &lt; b" in html
    assert "</code></pre>" in html


def test_markdown_link() -> None:
    html = markdown_to_html("[text](https://example.com)")
    assert '<a href="https://example.com">text</a>' in html


def test_markdown_unordered_list() -> None:
    html = markdown_to_html("- one\n- two")
    assert "<ul>" in html
    assert "<li>one</li>" in html
    assert "<li>two</li>" in html


def test_markdown_ordered_list() -> None:
    html = markdown_to_html("1. first\n2. second")
    assert "<ol>" in html
    assert "<li>first</li>" in html


def test_markdown_blockquote() -> None:
    html = markdown_to_html("> a note")
    assert "<blockquote>" in html
    assert "<p>a note</p>" in html


def test_markdown_table() -> None:
    md = "| A | B |\n| --- | --- |\n| 1 | 2 |"
    html = markdown_to_html(md)
    assert "<table>" in html
    assert "<th>A</th>" in html
    assert "<td>1</td>" in html


def test_markdown_horizontal_rule() -> None:
    assert "<hr/>" in markdown_to_html("---")


def test_markdown_escapes_html() -> None:
    assert "<script>" not in markdown_to_html("<script>alert(1)</script>")


# -- Help window ----------------------------------------------------------
def test_manual_file_is_bundled() -> None:
    assert doc_path("user_manual.md").is_file()


def test_load_manual_text_is_nonempty() -> None:
    assert load_manual_text().strip()


def test_help_window_renders_manual(qapp: QApplication) -> None:
    win = HelpWindow()
    html = win._browser.toHtml()
    assert "PeKanBan" in html
    assert "Getting Started" in html
    win.close()


def test_help_window_is_top_level(qapp: QApplication) -> None:
    win = HelpWindow()
    assert win.windowTitle() == "PeKanBan — Help"
    win.close()


# -- About splash ---------------------------------------------------------
def test_about_splash_shows_title_and_version(qapp: QApplication) -> None:
    from PySide6.QtWidgets import QLabel

    splash = AboutSplash(ThemeMode.LIGHT)
    texts = [label.text() for label in splash.findChildren(QLabel)]
    assert any("PeKanBan" in t for t in texts)
    assert any("Version" in t for t in texts)
    splash.close()


def test_about_splash_has_all_links(qapp: QApplication) -> None:
    from PySide6.QtWidgets import QLabel

    splash = AboutSplash(ThemeMode.LIGHT)
    html = " ".join(label.text() for label in splash.findChildren(QLabel))
    assert "JamesWitcher.com" in html
    assert "instagram.com/jwitch313" in html
    assert "paypal.com/paypalme/JamesWitcher" in html
    splash.close()


def test_about_splash_logo_renders(qapp: QApplication) -> None:
    from PySide6.QtWidgets import QLabel

    for mode in (ThemeMode.LIGHT, ThemeMode.DARK):
        splash = AboutSplash(mode)
        labels = splash.findChildren(QLabel)
        assert any(label.pixmap() is not None for label in labels)
        splash.close()


# -- Sidebar buttons & signals -------------------------------------------
def test_sidebar_has_help_and_about_buttons(qapp: QApplication) -> None:
    sidebar = Sidebar()
    assert sidebar._help_button is not None
    assert sidebar._about_button is not None
    sidebar.close()


def test_sidebar_help_button_emits_signal(qapp: QApplication) -> None:
    sidebar = Sidebar()
    fired = []
    sidebar.help_requested.connect(lambda: fired.append("help"))
    sidebar._help_button.click()
    assert fired == ["help"]
    sidebar.close()


def test_sidebar_about_button_emits_signal(qapp: QApplication) -> None:
    sidebar = Sidebar()
    fired = []
    sidebar.about_requested.connect(lambda: fired.append("about"))
    sidebar._about_button.click()
    assert fired == ["about"]
    sidebar.close()


# -- Main window wiring ---------------------------------------------------
def test_main_window_help_handler(window) -> None:
    window._on_help_requested()
    assert window._help_window is not None
    assert window._help_window.isVisible()


def test_main_window_about_handler(window) -> None:
    window._on_about_requested()
    assert window._about_splash is not None
    assert window._about_splash.isVisible()


def test_main_window_reuses_help_window(window) -> None:
    window._on_help_requested()
    first = window._help_window
    window._on_help_requested()
    assert window._help_window is first
