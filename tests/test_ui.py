"""Offscreen UI tests for the main window and its CRUD wiring."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from datetime import date, timedelta

from PySide6.QtCore import QMimeData, QPoint, Qt
from PySide6.QtGui import QDropEvent

from kanban.main_window import MainWindow
from kanban.models import Priority
from kanban.ui.board_view import BoardView
from kanban.ui.card_widget import KANBAN_TASK_MIME, PRIORITY_COLORS, CardWidget
from kanban.ui.column_widget import ColumnWidget


def test_default_board_created(window: MainWindow) -> None:
    assert window._current_board_id is not None
    assert len(window._service.list_boards()) == 1


def test_add_board(window: MainWindow) -> None:
    window._on_board_added("Second Board")
    boards = window._service.list_boards()
    assert len(boards) == 2
    assert any(b.name == "Second Board" for b in boards)


def test_add_column_and_task(window: MainWindow) -> None:
    board_id = window._current_board_id
    assert board_id is not None
    window._on_column_added("In Progress")
    board = window._service.get_board_full(board_id)
    assert board is not None
    assert [c.title for c in board.columns] == ["To Do", "In Progress"]

    doing = board.columns[1]
    window._on_task_added(doing.id, "Ship it")
    board = window._service.get_board_full(board_id)
    assert board is not None
    assert [t.title for t in board.columns[1].tasks] == ["Ship it"]


def test_delete_task(window: MainWindow) -> None:
    board = window._service.get_board_full(window._current_board_id)
    assert board is not None
    column = board.columns[0]
    window._on_task_added(column.id, "Temp task")
    board = window._service.get_board_full(window._current_board_id)
    assert board is not None
    task = board.columns[0].tasks[0]
    window._on_task_deleted(task.id)
    board = window._service.get_board_full(window._current_board_id)
    assert board is not None
    assert board.columns[0].tasks == []


def test_card_make_mime_data(qapp) -> None:
    card = CardWidget(7, "Task", Priority.HIGH, None)
    mime = card.make_mime_data()
    assert mime.hasFormat(KANBAN_TASK_MIME)
    assert bytes(mime.data(KANBAN_TASK_MIME)).decode("utf-8") == "7"


def test_card_should_start_drag(qapp) -> None:
    card = CardWidget(1, "Task", Priority.LOW, None)
    # No drag has been initiated yet.
    assert card._should_start_drag(QPoint(100, 100)) is False
    card._drag_start = QPoint(0, 0)
    # Within the drag threshold.
    assert card._should_start_drag(QPoint(3, 3)) is False
    # Beyond the drag threshold.
    assert card._should_start_drag(QPoint(10, 0)) is True


def test_card_overdue_highlighting(qapp) -> None:
    past = date.today() - timedelta(days=1)
    future = date.today() + timedelta(days=1)
    assert CardWidget(1, "Old", Priority.LOW, past).overdue is True
    assert CardWidget(2, "New", Priority.LOW, future).overdue is False
    assert CardWidget(3, "No due", Priority.LOW, None).overdue is False


def test_priority_colors_cover_all_priorities(qapp) -> None:
    assert set(PRIORITY_COLORS) == set(Priority)


def test_all_buttons_have_icons(window: MainWindow) -> None:
    """Every button in the UI must carry a relevant icon."""
    from PySide6.QtWidgets import QPushButton

    # Add a task and a label chip so card-level buttons are exercised.
    board = window._service.get_board_full(window._current_board_id)
    assert board is not None
    column = board.columns[0]
    window._on_task_added(column.id, "Icon check")
    label = window._service.create_label(window._current_board_id, "Bug", "#d9534f")
    board = window._service.get_board_full(window._current_board_id)
    assert board is not None
    task = board.columns[0].tasks[0]
    window._service.assign_label(task.id, label.id)
    window._load_current_board()

    buttons = window.findChildren(QPushButton)
    assert buttons, "expected at least one button in the UI"
    for button in buttons:
        assert not button.icon().isNull(), (
            f"button {button.accessibleName() or button.text()!r} has no icon"
        )


def test_column_heading_stays_at_top(qapp) -> None:
    """Empty/short columns must fill the board height with the heading on top."""
    from PySide6.QtWidgets import QSizePolicy, QSpacerItem

    column = ColumnWidget(1, "Empty", [])
    # The column expands vertically so its heading sits at the top of the board.
    assert column.sizePolicy().verticalPolicy() == QSizePolicy.Policy.Expanding
    # A stretch pushes the add-task row to the bottom (Trello-style layout).
    layout = column.layout()
    assert layout is not None
    spacers = [
        layout.itemAt(i) for i in range(layout.count()) if isinstance(layout.itemAt(i), QSpacerItem)
    ]
    assert spacers, "expected a stretch between the cards and the add-task row"


def test_board_add_column_row_top_aligned(qapp) -> None:
    """The inline add-column control must be top-aligned, not centered."""
    from PySide6.QtWidgets import QSpacerItem

    view = BoardView()
    layout = view._add_column_row.layout()
    assert layout is not None
    # A trailing stretch keeps the control pinned to the top of the board.
    last = layout.itemAt(layout.count() - 1)
    assert isinstance(last, QSpacerItem)


def test_column_accepts_drop_and_emits_task_moved(qapp) -> None:
    column = ColumnWidget(
        5,
        "To Do",
        [(10, "A", Priority.LOW, None, [], []), (11, "B", Priority.HIGH, None, [], [])],
    )
    captured: list[tuple[int, int, int]] = []
    column.task_moved.connect(lambda *a: captured.append(a))

    mime = QMimeData()
    mime.setData(KANBAN_TASK_MIME, b"42")
    drop = QDropEvent(
        QPoint(10, 10),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    column.dropEvent(drop)
    assert captured == [(42, 5, 0)]


def test_column_drop_index_boundaries(qapp) -> None:
    column = ColumnWidget(
        5,
        "To Do",
        [(10, "A", Priority.LOW, None, [], []), (11, "B", Priority.HIGH, None, [], [])],
    )
    # Dropping above the first card yields index 0.
    assert column._drop_index_at(QPoint(0, 0)) == 0
    # Dropping below every card yields the number of cards.
    assert column._drop_index_at(QPoint(0, 100000)) == 2


def test_board_view_forwards_task_moved(qapp) -> None:
    view = BoardView()
    captured: list[tuple[int, int, int]] = []
    view.task_moved.connect(lambda *a: captured.append(a))
    column = ColumnWidget(9, "To Do", [])
    view.add_column_widget(column)
    column.task_moved.emit(1, 9, 0)
    assert captured == [(1, 9, 0)]


def test_board_view_reflects_columns(window: MainWindow) -> None:
    board = window._service.get_board_full(window._current_board_id)
    assert board is not None
    window._board_view.load_board(board)
    container = window._board_view.widget()
    assert container is not None
    # Count column widgets present in the layout.
    from kanban.ui.column_widget import ColumnWidget

    columns = list(container.findChildren(ColumnWidget))
    assert len(columns) == len(board.columns)


# -- Column controls (rename / move / delete) -----------------------------
def test_column_rename_emits_signal(qapp) -> None:
    column = ColumnWidget(5, "To Do", [], index=0)
    captured: list[tuple[int, str]] = []
    column.column_renamed.connect(lambda *a: captured.append(a))

    column._start_rename()
    assert not column._rename_edit.isHidden()
    column._rename_edit.setText("Backlog")
    column._commit_rename()

    assert captured == [(5, "Backlog")]
    assert column._title_label.text() == "Backlog"
    assert column._rename_edit.isHidden()


def test_column_rename_blank_is_ignored(qapp) -> None:
    column = ColumnWidget(5, "To Do", [], index=0)
    captured: list[tuple[int, str]] = []
    column.column_renamed.connect(lambda *a: captured.append(a))

    column._start_rename()
    column._rename_edit.setText("   ")
    column._commit_rename()

    assert captured == []
    assert column._title_label.text() == "To Do"


def test_column_move_buttons_emit_index(qapp) -> None:
    column = ColumnWidget(5, "To Do", [], index=2)
    captured: list[tuple[int, int]] = []
    column.column_moved.connect(lambda *a: captured.append(a))

    column._move_left()
    column._move_right()
    assert captured == [(5, 1), (5, 3)]


def test_column_delete_emits_signal(qapp) -> None:
    column = ColumnWidget(5, "To Do", [], index=0)
    captured: list[int] = []
    column.column_deleted.connect(lambda v: captured.append(v))

    column._delete_column()
    assert captured == [5]


def test_board_view_forwards_column_signals(qapp) -> None:
    view = BoardView()
    renamed: list[tuple[int, str]] = []
    moved: list[tuple[int, int]] = []
    deleted: list[int] = []
    view.column_renamed.connect(lambda *a: renamed.append(a))
    view.column_moved.connect(lambda *a: moved.append(a))
    view.column_deleted.connect(lambda v: deleted.append(v))

    column = ColumnWidget(9, "To Do", [], index=0)
    view.add_column_widget(column)
    column.column_renamed.emit(9, "New")
    column.column_moved.emit(9, 1)
    column.column_deleted.emit(9)

    assert renamed == [(9, "New")]
    assert moved == [(9, 1)]
    assert deleted == [9]


def test_window_rename_column(window: MainWindow) -> None:
    board = window._service.get_board_full(window._current_board_id)
    assert board is not None
    column = board.columns[0]
    window._on_column_renamed(column.id, "Backlog")
    board = window._service.get_board_full(window._current_board_id)
    assert board is not None
    assert board.columns[0].title == "Backlog"


def test_window_move_column(window: MainWindow) -> None:
    board_id = window._current_board_id
    assert board_id is not None
    window._on_column_added("B")
    window._on_column_added("C")
    board = window._service.get_board_full(board_id)
    assert board is not None
    first = board.columns[0]

    window._on_column_moved(first.id, 2)
    board = window._service.get_board_full(board_id)
    assert board is not None
    assert [c.title for c in board.columns] == ["B", "C", "To Do"]


def test_window_delete_column(window: MainWindow) -> None:
    board_id = window._current_board_id
    assert board_id is not None
    window._on_column_added("In Progress")
    board = window._service.get_board_full(board_id)
    assert board is not None
    column = board.columns[1]

    window._on_column_deleted(column.id)
    board = window._service.get_board_full(board_id)
    assert board is not None
    assert [c.title for c in board.columns] == ["To Do"]


# -- Board controls (rename / delete) -------------------------------------
def test_sidebar_rename_emits_signal(qapp) -> None:
    from kanban.models import Board
    from kanban.ui.sidebar import Sidebar

    sidebar = Sidebar()
    captured: list[tuple[int, str]] = []
    sidebar.board_renamed.connect(lambda *a: captured.append(a))
    sidebar.load_boards([Board(id=1, name="A"), Board(id=2, name="B")])
    sidebar._list.setCurrentRow(0)
    item = sidebar._list.currentItem()
    assert item is not None
    sidebar._start_rename()
    item.setText("Renamed")
    assert captured == [(1, "Renamed")]


def test_sidebar_rename_blank_is_ignored(qapp) -> None:
    from kanban.models import Board
    from kanban.ui.sidebar import Sidebar

    sidebar = Sidebar()
    captured: list[tuple[int, str]] = []
    sidebar.board_renamed.connect(lambda *a: captured.append(a))
    sidebar.load_boards([Board(id=1, name="A")])
    sidebar._list.setCurrentRow(0)
    item = sidebar._list.currentItem()
    assert item is not None
    sidebar._start_rename()
    item.setText("   ")
    assert captured == []


def test_sidebar_delete_emits_signal(qapp) -> None:
    from kanban.models import Board
    from kanban.ui.sidebar import Sidebar

    sidebar = Sidebar()
    captured: list[int] = []
    sidebar.board_deleted.connect(lambda v: captured.append(v))
    sidebar.load_boards([Board(id=1, name="A"), Board(id=2, name="B")])
    sidebar._list.setCurrentRow(1)
    sidebar._delete_board()
    assert captured == [2]


def test_window_rename_board(window: MainWindow) -> None:
    board_id = window._current_board_id
    assert board_id is not None
    window._on_board_renamed(board_id, "Renamed Board")
    board = window._service.get_board(board_id)
    assert board is not None
    assert board.name == "Renamed Board"


def test_window_delete_board_switches_to_remaining(window: MainWindow) -> None:
    window._on_board_added("Second")
    first_id = window._current_board_id
    assert first_id is not None
    window._on_board_deleted(first_id)
    assert window._current_board_id != first_id
    assert len(window._service.list_boards()) == 1


def test_window_delete_last_board_creates_default(window: MainWindow) -> None:
    board_id = window._current_board_id
    assert board_id is not None
    window._on_board_deleted(board_id)
    assert window._current_board_id is not None
    boards = window._service.list_boards()
    assert len(boards) == 1
    assert boards[0].name == "My Board"
    assert window._current_board_id == boards[0].id


# -- Labels (chips, picker, panel, wiring) --------------------------------
def test_label_chip_style_and_remove_signal(qapp) -> None:
    from kanban.ui.card_widget import DEFAULT_LABEL_COLOR, LabelChip

    chip = LabelChip(3, "Bug", "#d9534f")
    assert chip.label_id == 3
    assert "#d9534f" in chip.styleSheet()

    fallback = LabelChip(4, "Misc", None)
    assert DEFAULT_LABEL_COLOR in fallback.styleSheet()

    captured: list[int] = []
    chip.remove_requested.connect(lambda v: captured.append(v))
    chip.click()
    assert captured == [3]


def test_card_renders_label_chips(qapp) -> None:
    card = CardWidget(
        1,
        "Task",
        Priority.LOW,
        None,
        labels=[(1, "Bug", "#d9534f"), (2, "Feature", "#4a90d9")],
    )
    assert card.label_ids == [1, 2]

    captured: list[tuple[int, int]] = []
    card.label_unassign_requested.connect(lambda *a: captured.append(a))
    card._label_chips[0].remove_requested.emit(1)
    assert captured == [(1, 1)]


def test_card_label_menu_excludes_assigned_and_emits(qapp) -> None:
    card = CardWidget(
        7,
        "Task",
        Priority.LOW,
        None,
        labels=[(1, "Bug", "#d9534f")],
        board_labels=[(1, "Bug", "#d9534f"), (2, "Feature", "#4a90d9")],
    )
    menu = card._build_label_menu()
    # Only the unassigned label should appear.
    assert [action.text() for action in menu.actions()] == ["Feature"]

    captured: list[tuple[int, int]] = []
    card.label_assign_requested.connect(lambda *a: captured.append(a))
    menu.actions()[0].trigger()
    assert captured == [(7, 2)]


def test_column_forwards_label_signals(qapp) -> None:
    column = ColumnWidget(
        5,
        "To Do",
        [(10, "A", Priority.LOW, None, [], [])],
        board_labels=[(1, "Bug", "#d9534f")],
    )
    assigned: list[tuple[int, int]] = []
    unassigned: list[tuple[int, int]] = []
    column.label_assign_requested.connect(lambda *a: assigned.append(a))
    column.label_unassign_requested.connect(lambda *a: unassigned.append(a))

    card = column._card_layout.itemAt(0).widget()
    assert isinstance(card, CardWidget)
    card.label_assign_requested.emit(10, 1)
    card.label_unassign_requested.emit(10, 1)
    assert assigned == [(10, 1)]
    assert unassigned == [(10, 1)]


def test_board_view_forwards_label_signals(qapp) -> None:
    view = BoardView()
    assigned: list[tuple[int, int]] = []
    unassigned: list[tuple[int, int]] = []
    view.label_assign_requested.connect(lambda *a: assigned.append(a))
    view.label_unassign_requested.connect(lambda *a: unassigned.append(a))

    column = ColumnWidget(9, "To Do", [])
    view.add_column_widget(column)
    column.label_assign_requested.emit(1, 2)
    column.label_unassign_requested.emit(1, 2)
    assert assigned == [(1, 2)]
    assert unassigned == [(1, 2)]


def test_board_view_filters_visible_tasks(qapp) -> None:
    from kanban.models import Board, BoardColumn, Task

    board = Board(id=1, name="B")
    column = BoardColumn(id=1, title="To Do", order_idx=0)
    t1 = Task(id=1, title="One", priority=Priority.LOW, order_idx=0)
    t2 = Task(id=2, title="Two", priority=Priority.HIGH, order_idx=1)
    column.tasks.extend([t1, t2])
    board.columns.append(column)

    view = BoardView()
    view.load_board(board, visible_task_ids={2})
    cards = view.widget().findChildren(CardWidget)
    assert [card.task_id for card in cards] == [2]


def test_label_panel_add_and_delete(qapp) -> None:
    from kanban.ui.label_panel import PRESET_COLORS, LabelPanel

    panel = LabelPanel()
    added: list[tuple[str, str]] = []
    deleted: list[int] = []
    panel.label_added.connect(lambda *a: added.append(a))
    panel.label_deleted.connect(lambda v: deleted.append(v))

    panel.load_labels([(1, "Bug", "#d9534f"), (2, "Feature", "#4a90d9")])
    assert panel._list.count() == 2

    panel._name_edit.setText("Urgent")
    panel._submit_new_label()
    assert len(added) == 1
    assert added[0][0] == "Urgent"
    assert added[0][1] in PRESET_COLORS

    panel._list.setCurrentRow(1)
    panel._delete_label()
    assert deleted == [2]


def test_label_panel_blank_name_ignored(qapp) -> None:
    from kanban.ui.label_panel import LabelPanel

    panel = LabelPanel()
    added: list[tuple[str, str]] = []
    panel.label_added.connect(lambda *a: added.append(a))
    panel._name_edit.setText("   ")
    panel._submit_new_label()
    assert added == []


def test_label_panel_shows_names_and_swatch(qapp) -> None:
    """Label names must be visible and each row carries a color swatch icon."""
    from kanban.ui.label_panel import LabelPanel

    panel = LabelPanel()
    panel.load_labels([(1, "Bug", "#d9534f"), (2, "Feature", "#4a90d9")])
    assert panel._list.count() == 2
    for i in range(panel._list.count()):
        item = panel._list.item(i)
        assert item is not None
        # The label name must be present and its foreground must be opaque.
        assert item.text() != ""
        assert item.foreground().color().alpha() != 0
        # A color swatch icon must be attached so the color is visible at a glance.
        assert not item.icon().isNull()


def test_label_panel_color_combo_has_swatch_icons(qapp) -> None:
    """Each color option must show a swatch icon while keeping the hex as data."""
    from kanban.ui.label_panel import PRESET_COLORS, LabelPanel

    panel = LabelPanel()
    assert panel._color_combo.count() == len(PRESET_COLORS)
    for i in range(panel._color_combo.count()):
        icon = panel._color_combo.itemIcon(i)
        assert icon is not None and not icon.isNull()
        assert panel._color_combo.itemData(i) in PRESET_COLORS


def test_window_label_crud(window: MainWindow) -> None:
    board_id = window._current_board_id
    assert board_id is not None

    window._on_label_added("Bug", "#d9534f")
    labels = window._service.list_labels(board_id)
    assert len(labels) == 1
    label = labels[0]

    board = window._service.get_board_full(board_id)
    assert board is not None
    column = board.columns[0]
    window._on_task_added(column.id, "Task")
    board = window._service.get_board_full(board_id)
    assert board is not None
    task = board.columns[0].tasks[0]

    window._on_label_assigned(task.id, label.id)
    board = window._service.get_board_full(board_id)
    assert board is not None
    assert [lbl.id for lbl in board.columns[0].tasks[0].labels] == [label.id]

    window._on_label_unassigned(task.id, label.id)
    board = window._service.get_board_full(board_id)
    assert board is not None
    assert board.columns[0].tasks[0].labels == []

    window._on_label_deleted(label.id)
    assert window._service.list_labels(board_id) == []


def test_sidebar_forwards_label_signals(qapp) -> None:
    from kanban.ui.sidebar import Sidebar

    sidebar = Sidebar()
    added: list[tuple[str, str]] = []
    deleted: list[int] = []
    sidebar.label_added.connect(lambda *a: added.append(a))
    sidebar.label_deleted.connect(lambda v: deleted.append(v))

    sidebar.load_labels([(1, "Bug", "#d9534f")])
    assert sidebar._label_panel._list.count() == 1

    sidebar._label_panel._name_edit.setText("New")
    sidebar._label_panel._submit_new_label()
    assert len(added) == 1

    sidebar._label_panel._list.setCurrentRow(0)
    sidebar._label_panel._delete_label()
    assert deleted == [1]


# -- Slice 5: search & filtering ------------------------------------------


def test_search_bar_defaults(qapp) -> None:
    from kanban.ui.search_bar import SearchBar

    bar = SearchBar()
    filters = bar.build_filters()
    assert filters == {
        "query": "",
        "priority": None,
        "column_id": None,
        "label_id": None,
        "due_before": None,
        "due_after": None,
    }


def test_search_bar_build_filters_reflects_controls(qapp) -> None:
    from kanban.ui.search_bar import SearchBar

    bar = SearchBar()
    bar._query.setText("  urgent  ")
    bar._priority.setCurrentIndex(1)
    bar.load_columns([(7, "Doing")])
    bar._column.setCurrentIndex(1)
    bar.load_labels([(3, "Bug")])
    bar._label.setCurrentIndex(1)

    filters = bar.build_filters()
    assert filters["query"] == "urgent"
    assert filters["priority"] is Priority.LOW
    assert filters["column_id"] == 7
    assert filters["label_id"] == 3
    assert filters["due_before"] is None
    assert filters["due_after"] is None


def test_search_bar_due_range(qapp) -> None:
    from PySide6.QtCore import QDate

    from kanban.ui.search_bar import SearchBar

    bar = SearchBar()
    bar._due_enabled.setChecked(True)
    bar._due_after.setDate(QDate(2024, 1, 1))
    bar._due_before.setDate(QDate(2024, 1, 31))
    filters = bar.build_filters()
    assert filters["due_after"] == date(2024, 1, 1)
    assert filters["due_before"] == date(2024, 1, 31)


def test_search_bar_clear_resets_and_emits(qapp) -> None:
    from kanban.ui.search_bar import SearchBar

    bar = SearchBar()
    emitted: list[dict] = []
    bar.filters_changed.connect(lambda f: emitted.append(f))

    bar._query.setText("something")
    bar.clear()

    assert bar.build_filters()["query"] == ""
    assert emitted and emitted[-1]["query"] == ""


def test_search_bar_reset_does_not_emit(qapp) -> None:
    from kanban.ui.search_bar import SearchBar

    bar = SearchBar()
    emitted: list[dict] = []
    bar.filters_changed.connect(lambda f: emitted.append(f))

    bar._query.setText("something")
    emitted.clear()
    bar.reset()

    assert bar.build_filters()["query"] == ""
    assert emitted == []


def test_window_no_filter_shows_all_cards(window: MainWindow) -> None:
    board_id = window._current_board_id
    assert board_id is not None
    board = window._service.get_board_full(board_id)
    assert board is not None
    column = board.columns[0]
    window._on_task_added(column.id, "Alpha")
    window._on_task_added(column.id, "Beta")

    cards = window._board_view.widget().findChildren(CardWidget)
    assert len(cards) == 2


def test_window_query_filter_shows_matching_cards(window: MainWindow) -> None:
    board_id = window._current_board_id
    assert board_id is not None
    board = window._service.get_board_full(board_id)
    assert board is not None
    column = board.columns[0]
    window._on_task_added(column.id, "Alpha task")
    window._on_task_added(column.id, "Beta task")

    window._apply_filters(
        {
            "query": "alpha",
            "priority": None,
            "column_id": None,
            "label_id": None,
            "due_before": None,
            "due_after": None,
        }
    )

    cards = window._board_view.widget().findChildren(CardWidget)
    assert len(cards) == 1
    assert cards[0].accessibleName() == "Task: Alpha task"


def test_window_priority_filter(window: MainWindow) -> None:
    board_id = window._current_board_id
    assert board_id is not None
    board = window._service.get_board_full(board_id)
    assert board is not None
    column = board.columns[0]
    window._on_task_added(column.id, "Low task")
    window._service.create_task(column.id, "High task", priority=Priority.HIGH)
    window._load_current_board()

    window._apply_filters(
        {
            "query": "",
            "priority": Priority.HIGH,
            "column_id": None,
            "label_id": None,
            "due_before": None,
            "due_after": None,
        }
    )

    cards = window._board_view.widget().findChildren(CardWidget)
    assert len(cards) == 1
    assert cards[0].accessibleName() == "Task: High task"


def test_window_clear_filters_restores_all(window: MainWindow) -> None:
    board_id = window._current_board_id
    assert board_id is not None
    board = window._service.get_board_full(board_id)
    assert board is not None
    column = board.columns[0]
    window._on_task_added(column.id, "Alpha")
    window._on_task_added(column.id, "Beta")

    window._apply_filters(
        {
            "query": "alpha",
            "priority": None,
            "column_id": None,
            "label_id": None,
            "due_before": None,
            "due_after": None,
        }
    )
    assert len(window._board_view.widget().findChildren(CardWidget)) == 1

    window._search_bar.clear()
    assert len(window._board_view.widget().findChildren(CardWidget)) == 2


def test_window_board_switch_resets_filters(window: MainWindow) -> None:
    board_id = window._current_board_id
    assert board_id is not None
    board = window._service.get_board_full(board_id)
    assert board is not None
    column = board.columns[0]
    window._on_task_added(column.id, "Alpha")
    window._on_task_added(column.id, "Beta")

    window._apply_filters(
        {
            "query": "alpha",
            "priority": None,
            "column_id": None,
            "label_id": None,
            "due_before": None,
            "due_after": None,
        }
    )
    assert len(window._board_view.widget().findChildren(CardWidget)) == 1

    window._on_board_added("Second")
    assert window._search_bar.build_filters()["query"] == ""
    assert window._filters == {}


def test_theme_menu_present(window: MainWindow) -> None:
    """A View menu must expose System/Light/Dark theme actions."""
    from PySide6.QtGui import QAction

    actions = window._theme_actions
    assert set(actions) == {"system", "light", "dark"}
    for action in actions.values():
        assert isinstance(action, QAction)
        assert action.isCheckable()


def test_theme_actions_are_exclusive(window: MainWindow) -> None:
    """Theme actions must behave like radio buttons (one checked at a time)."""
    window._theme_actions["dark"].trigger()
    assert window._theme_actions["dark"].isChecked()
    assert not window._theme_actions["light"].isChecked()
    assert not window._theme_actions["system"].isChecked()


def test_select_dark_theme_applies_and_persists(window: MainWindow) -> None:
    """Choosing Dark applies the dark stylesheet and persists the choice."""
    from PySide6.QtWidgets import QApplication

    from kanban.ui.theme import DARK_QSS

    window._theme_actions["dark"].trigger()
    assert QApplication.instance().styleSheet() == DARK_QSS
    assert window._settings.theme_mode() == "dark"


def test_select_light_theme_applies_and_persists(window: MainWindow) -> None:
    """Choosing Light applies the light stylesheet and persists the choice."""
    from PySide6.QtWidgets import QApplication

    from kanban.ui.theme import LIGHT_QSS

    window._theme_actions["light"].trigger()
    assert QApplication.instance().styleSheet() == LIGHT_QSS
    assert window._settings.theme_mode() == "light"


def test_select_system_theme_persists(window: MainWindow) -> None:
    """Choosing System persists the choice and re-applies the detected theme."""
    from PySide6.QtWidgets import QApplication

    from kanban.ui.theme import DARK_QSS, LIGHT_QSS

    window._theme_actions["system"].trigger()
    assert window._settings.theme_mode() == "system"
    assert QApplication.instance().styleSheet() in {LIGHT_QSS, DARK_QSS}
