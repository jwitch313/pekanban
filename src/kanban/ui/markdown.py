"""A small, dependency-free Markdown-to-HTML converter for the Help window.

PeKanBan's only runtime dependencies are PySide6 and SQLAlchemy, so the Help
window renders the user manual with this self-contained converter rather than
pulling in a third-party Markdown library. It supports the subset of Markdown
used by ``docs/user_manual.md``: headings, bold/italic, inline code, fenced
code blocks, blockquotes, tables, ordered/unordered lists, horizontal rules,
and ``[text](url)`` links.
"""

from __future__ import annotations

import html
import re


def _escape(text: str) -> str:
    """Escape HTML special characters, leaving quotes intact for attributes."""
    return html.escape(text, quote=False)


def _inline(text: str) -> str:
    """Convert inline Markdown (code, links, bold, italic) to HTML.

    Inline code spans are handled first and their contents are left untouched
    so that markers inside a code span are not reinterpreted.
    """
    parts = re.split(r"(`[^`]+`)", text)
    out: list[str] = []
    for part in parts:
        if part.startswith("`") and part.endswith("`") and len(part) >= 2:
            out.append(f"<code>{_escape(part[1:-1])}</code>")
            continue
        seg = _escape(part)
        # Links: [text](url)
        seg = re.sub(
            r"\[([^\]]+)\]\(([^)\s]+)\)",
            lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>',
            seg,
        )
        # Bold: **text**
        seg = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", seg)
        # Italic: *text*
        seg = re.sub(r"\*([^*]+)\*", r"<i>\1</i>", seg)
        out.append(seg)
    return "".join(out)


def _split_row(row: str) -> list[str]:
    """Split a Markdown table row into stripped cell values."""
    row = row.strip()
    if row.startswith("|"):
        row = row[1:]
    if row.endswith("|"):
        row = row[:-1]
    return [cell.strip() for cell in row.split("|")]


def _table_html(header: list[str], rows: list[list[str]]) -> str:
    """Render a table header and body rows as an HTML table."""
    parts = ["<table>"]
    parts.append(
        "<thead><tr>" + "".join(f"<th>{_inline(c)}</th>" for c in header) + "</tr></thead>"
    )
    parts.append("<tbody>")
    for row in rows:
        parts.append("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in row) + "</tr>")
    parts.append("</tbody></table>")
    return "".join(parts)


def markdown_to_html(md: str) -> str:
    """Convert a Markdown document to a fragment of HTML.

    The result is a sequence of block elements (headings, paragraphs, lists,
    tables, code blocks, blockquotes, and rules) suitable for the body of a
    :class:`QTextBrowser` document.
    """
    lines = md.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out: list[str] = []
    paragraph: list[str] = []
    i = 0
    n = len(lines)

    def flush_paragraph() -> None:
        if paragraph:
            out.append(f"<p>{_inline(' '.join(paragraph))}</p>")
            paragraph.clear()

    while i < n:
        stripped = lines[i].strip()

        # Fenced code block.
        if stripped.startswith("```"):
            flush_paragraph()
            i += 1
            code: list[str] = []
            while i < n and not lines[i].strip().startswith("```"):
                code.append(lines[i])
                i += 1
            i += 1  # skip the closing fence
            out.append("<pre><code>" + _escape("\n".join(code)) + "</code></pre>")
            continue

        # Blank line ends the current paragraph.
        if not stripped:
            flush_paragraph()
            i += 1
            continue

        # Horizontal rule.
        if re.fullmatch(r"(-{3,}|\*{3,}|_{3,})", stripped):
            flush_paragraph()
            out.append("<hr/>")
            i += 1
            continue

        # Heading.
        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            flush_paragraph()
            level = len(m.group(1))
            out.append(f"<h{level}>{_inline(m.group(2))}</h{level}>")
            i += 1
            continue

        # Blockquote (may span multiple lines).
        if stripped.startswith(">"):
            flush_paragraph()
            quote: list[str] = []
            while i < n and lines[i].strip().startswith(">"):
                quote.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            out.append(f"<blockquote>{markdown_to_html('\n'.join(quote))}</blockquote>")
            continue

        # Table: a pipe row followed by a separator row.
        if (
            stripped.startswith("|")
            and i + 1 < n
            and "-" in lines[i + 1]
            and re.match(r"^\s*\|?[\s:|-]+\|?\s*$", lines[i + 1])
        ):
            flush_paragraph()
            header = _split_row(stripped)
            i += 2  # skip the header and the separator row
            rows: list[list[str]] = []
            while i < n and lines[i].strip().startswith("|"):
                rows.append(_split_row(lines[i].strip()))
                i += 1
            out.append(_table_html(header, rows))
            continue

        # Unordered list.
        if re.match(r"^[-*+]\s+", stripped):
            flush_paragraph()
            items: list[str] = []
            while i < n and re.match(r"^[-*+]\s+", lines[i].strip()):
                items.append(re.sub(r"^[-*+]\s+", "", lines[i].strip()))
                i += 1
            out.append("<ul>" + "".join(f"<li>{_inline(it)}</li>" for it in items) + "</ul>")
            continue

        # Ordered list.
        if re.match(r"^\d+\.\s+", stripped):
            flush_paragraph()
            items: list[str] = []
            while i < n and re.match(r"^\d+\.\s+", lines[i].strip()):
                items.append(re.sub(r"^\d+\.\s+", "", lines[i].strip()))
                i += 1
            out.append("<ol>" + "".join(f"<li>{_inline(it)}</li>" for it in items) + "</ol>")
            continue

        # Regular paragraph line.
        paragraph.append(stripped)
        i += 1

    flush_paragraph()
    return "\n".join(out)
