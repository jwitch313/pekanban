"""A flow layout that wraps child widgets onto new lines as space runs out.

Qt has no built-in flow layout, so this module provides one (adapted from the
canonical Qt example). It is used for the card's label-chip row so that labels
re-flow onto additional lines instead of overflowing or clipping when the card
is narrower than the chips' combined width.

Note: in PySide6 ``QLayout`` exposes several methods (``addItem``, ``count``,
``itemAt``, ``takeAt``, ...) as pure virtual, so this subclass keeps its own
list of items and implements those methods directly rather than delegating to
the C++ base.
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtWidgets import QLayout, QLayoutItem, QWidget


class FlowLayout(QLayout):
    """A left-to-right layout that wraps items onto new lines when needed."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._items: list[QLayoutItem] = []
        self._h_spacing: int | None = None
        self._v_spacing: int | None = None

    # -- item management (pure virtual in PySide6) -------------------------
    def addItem(self, item: QLayoutItem) -> None:  # noqa: N802 - Qt naming
        self._items.append(item)
        parent = self.parent()
        if isinstance(parent, QWidget):
            parent.updateGeometry()

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int) -> QLayoutItem | None:  # noqa: N802 - Qt naming
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index: int) -> QLayoutItem | None:  # noqa: N802 - Qt naming
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def removeAt(self, index: int) -> None:  # noqa: N802 - Qt naming
        if 0 <= index < len(self._items):
            self._items.pop(index)

    def indexOf(self, item: QWidget | QLayoutItem) -> int:  # noqa: N802 - Qt naming
        for i, existing in enumerate(self._items):
            if existing is item or existing.widget() is item:
                return i
        return -1

    def isEmpty(self) -> bool:  # noqa: N802 - Qt naming
        return not self._items

    # -- spacing -----------------------------------------------------------
    def setHorizontalSpacing(self, spacing: int) -> None:  # noqa: N802 - Qt naming
        self._h_spacing = spacing

    def setVerticalSpacing(self, spacing: int) -> None:  # noqa: N802 - Qt naming
        self._v_spacing = spacing

    def horizontalSpacing(self) -> int:  # noqa: N802 - Qt naming
        if self._h_spacing is not None:
            return self._h_spacing
        return self._smart_spacing(Qt.Orientation.Horizontal)

    def verticalSpacing(self) -> int:  # noqa: N802 - Qt naming
        if self._v_spacing is not None:
            return self._v_spacing
        return self._smart_spacing(Qt.Orientation.Vertical)

    def _smart_spacing(self, orientation: Qt.Orientation) -> int:
        """Fall back to the style's default spacing for ``orientation``."""
        parent = self.parent()
        if not isinstance(parent, QWidget):
            return 6
        style = parent.style()
        metric = (
            style.PixelMetric.PM_LayoutHorizontalSpacing
            if orientation == Qt.Orientation.Horizontal
            else style.PixelMetric.PM_LayoutVerticalSpacing
        )
        return int(style.pixelMetric(metric))

    # -- geometry ----------------------------------------------------------
    def hasHeightForWidth(self) -> bool:  # noqa: N802 - Qt naming
        """A flow layout's height depends on its width."""
        return True

    def heightForWidth(self, width: int) -> int:  # noqa: N802 - Qt naming
        """Return the height needed to lay out all items within ``width``."""
        return self._do_layout(QRect(0, 0, width, 0), True).height()

    def sizeHint(self) -> QSize:  # noqa: N802 - Qt naming
        """The smallest size that fits every item on a single line."""
        total = QSize()
        for i in range(self.count()):
            item = self.itemAt(i)
            if item is not None:
                total += item.sizeHint()
        margin = self.contentsMargins()
        return QSize(
            total.width() + margin.left() + margin.right(),
            total.height() + margin.top() + margin.bottom(),
        )

    def minimumSize(self) -> QSize:  # noqa: N802 - Qt naming
        """The smallest size that still fits every item (one per line)."""
        size = QSize()
        margin = self.contentsMargins()
        for i in range(self.count()):
            item = self.itemAt(i)
            if item is not None:
                size = size.expandedTo(item.minimumSize())
        return QSize(
            size.width() + margin.left() + margin.right(),
            size.height() + margin.top() + margin.bottom(),
        )

    def setGeometry(  # noqa: N802 - Qt naming
        self,
        rect_or_x: QRect | int,
        y: int | None = None,
        w: int | None = None,
        h: int | None = None,
    ) -> None:
        """Accept either a single ``QRect`` or the ``(x, y, w, h)`` overload."""
        if isinstance(rect_or_x, QRect):
            rect = rect_or_x
        else:
            rect = QRect(rect_or_x, y or 0, w or 0, h or 0)
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def _do_layout(self, rect: QRect, test_only: bool) -> QSize:
        """Position items within ``rect``, wrapping onto new lines as needed."""
        left = rect.x() + self.contentsMargins().left()
        top = rect.y() + self.contentsMargins().top()
        right = rect.x() + rect.width() - self.contentsMargins().right()
        horizontal_space = self.horizontalSpacing()
        vertical_space = self.verticalSpacing()

        x = left
        y = top
        line_height = 0
        for i in range(self.count()):
            item = self.itemAt(i)
            if item is None:
                continue
            next_x = x + item.sizeHint().width() + horizontal_space
            if next_x - horizontal_space > right and line_height > 0:
                x = left
                y = y + line_height + vertical_space
                next_x = x + item.sizeHint().width() + horizontal_space
                line_height = 0
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
            x = next_x
            line_height = max(line_height, item.sizeHint().height())
        return QSize(rect.width(), y + line_height - top + self.contentsMargins().bottom())
