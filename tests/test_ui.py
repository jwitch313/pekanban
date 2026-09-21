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


def test_no_new_board_created_on_relaunch(qapp, tmp_path) -> None:
    """A second launch over an existing DB must reuse the board, not add one."""
    from kanban.services.database import create_database

    db = create_database(tmp_path / "relaunch.db")
    db.init_db()
    first = MainWindow(database=db)
    assert len(first._service.list_boards()) == 1
    first.close()

    second = MainWindow(database=db)
    assert len(second._service.list_boards()) == 1
    assert second._current_board_id is not None
    second.close()
    db.dispose()


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


def test_card_priority_button_emits_signal(qapp) -> None:
    """Selecting a priority from the card menu emits priority_changed."""
    card = CardWidget(5, "Task", Priority.LOW, None)
    emitted: list[tuple[int, object]] = []
    card.priority_changed.connect(lambda tid, prio: emitted.append((tid, prio)))
    card._build_priority_menu()
    card._priority_actions[Priority.URGENT].trigger()
    assert emitted == [(5, Priority.URGENT)]


def test_priority_button_has_no_dropdown_menu(qapp) -> None:
    """The priority button must not use setMenu (no dropdown arrow)."""
    card = CardWidget(5, "Task", Priority.LOW, None)
    assert card._priority_button.menu() is None


def test_priority_button_click_builds_menu(qapp) -> None:
    """Clicking the priority button builds a menu listing every priority."""
    card = CardWidget(5, "Task", Priority.LOW, None)
    menu = card._build_priority_menu()
    assert [action.text() for action in menu.actions()] == [
        "Low",
        "Medium",
        "High",
        "Urgent",
    ]


def test_card_priority_actions_exclusive(qapp) -> None:
    """The card's priority actions behave like radio buttons."""
    card = CardWidget(5, "Task", Priority.LOW, None)
    card._build_priority_menu()
    assert card._priority_actions[Priority.LOW].isChecked()
    card._priority_actions[Priority.HIGH].trigger()
    assert card._priority_actions[Priority.HIGH].isChecked()
    assert not card._priority_actions[Priority.LOW].isChecked()


def test_change_task_priority_persists(window: MainWindow) -> None:
    """Changing a task's priority updates and persists it."""
    board = window._service.get_board_full(window._current_board_id)
    assert board is not None
    column = board.columns[0]
    window._on_task_added(column.id, "Priority task")
    board = window._service.get_board_full(window._current_board_id)
    assert board is not None
    task = board.columns[0].tasks[0]
    window._on_priority_changed(task.id, Priority.URGENT)
    board = window._service.get_board_full(window._current_board_id)
    assert board is not None
    assert board.columns[0].tasks[0].priority is Priority.URGENT


def test_card_due_set_emits_date(qapp) -> None:
    """Confirming a picked due date emits due_date_changed with that date."""
    from PySide6.QtCore import QDate
    from PySide6.QtWidgets import QDateEdit

    card = CardWidget(5, "Task", Priority.LOW, None)
    emitted: list[tuple[int, object]] = []
    card.due_date_changed.connect(lambda tid, d: emitted.append((tid, d)))
    card._due_picker = QDateEdit()
    card._due_picker.setDate(QDate(2025, 6, 15))
    card._on_set_due()
    assert emitted == [(5, date(2025, 6, 15))]


def test_due_date_picker_popup_is_retained(qapp) -> None:
    """The due-date popup must be retained so it stays visible after the click."""
    import gc

    from PySide6.QtWidgets import QDateEdit, QWidget

    card = CardWidget(5, "Task", Priority.LOW, None)
    card._show_due_date_picker()
    gc.collect()
    assert isinstance(card._due_popup, QWidget)
    assert card._due_popup.isVisible()
    assert isinstance(card._due_picker, QDateEdit)
    assert card._due_picker.calendarPopup()


def test_due_date_picker_popup_is_opaque_in_light_theme(qapp) -> None:
    """The due-date popup must render with an opaque, theme-matched background."""
    from kanban.ui.theme import LIGHT_QSS

    previous = qapp.styleSheet()
    try:
        qapp.setStyleSheet(LIGHT_QSS)
        card = CardWidget(5, "Task", Priority.LOW, None)
        card.show()
        card._show_due_date_picker()
        qapp.processEvents()
        corner = card._due_popup.grab().toImage().pixelColor(0, 0)
        assert corner.alpha() > 0, "due-date popup background is transparent"
    finally:
        qapp.setStyleSheet(previous)


def test_due_date_picker_defaults_to_today(qapp) -> None:
    """The due-date picker must default to the current date, not 2000-01-01."""
    from PySide6.QtCore import QDate

    card = CardWidget(5, "Task", Priority.LOW, None)
    card._show_due_date_picker()
    assert card._due_picker.date() == QDate.currentDate()


def test_due_date_label_below_priority(qapp) -> None:
    """The due-date label must sit on its own row below the priority badge."""
    from PySide6.QtWidgets import QLabel, QLayout

    card = CardWidget(5, "Task", Priority.LOW, date.today())
    due_label = card.findChild(QLabel, "dueDate")
    badge = card.findChild(QLabel, "priorityBadge")
    assert due_label is not None
    assert badge is not None
    main = card.layout()
    assert main is not None

    def containing_layout(layout: QLayout, widget: QLabel) -> QLayout | None:
        for index in range(layout.count()):
            item = layout.itemAt(index)
            if item is None:
                continue
            if item.widget() is widget:
                return layout
            sub = item.layout()
            if sub is not None:
                found = containing_layout(sub, widget)
                if found is not None:
                    return found
        return None

    assert containing_layout(main, due_label) is not containing_layout(main, badge)


def test_card_due_clear_emits_none(qapp) -> None:
    """Clearing the due date emits due_date_changed with None."""
    card = CardWidget(5, "Task", Priority.LOW, None)
    emitted: list[tuple[int, object]] = []
    card.due_date_changed.connect(lambda tid, d: emitted.append((tid, d)))
    card._on_clear_due()
    assert emitted == [(5, None)]


def test_set_due_date_persists(window: MainWindow) -> None:
    """Setting a task's due date updates and persists it."""
    board = window._service.get_board_full(window._current_board_id)
    assert board is not None
    column = board.columns[0]
    window._on_task_added(column.id, "Due task")
    board = window._service.get_board_full(window._current_board_id)
    assert board is not None
    task = board.columns[0].tasks[0]
    window._on_due_date_changed(task.id, date(2025, 6, 15))
    board = window._service.get_board_full(window._current_board_id)
    assert board is not None
    assert board.columns[0].tasks[0].due_date == date(2025, 6, 15)


def test_card_description_label_shown_when_set(qapp) -> None:
    """A card with a description renders a description label; without one it does not."""
    from PySide6.QtWidgets import QLabel

    with_desc = CardWidget(1, "Task", Priority.LOW, None, description="Some notes")
    assert with_desc.findChild(QLabel, "taskDescription") is not None

    without_desc = CardWidget(2, "Task", Priority.LOW, None)
    assert without_desc.findChild(QLabel, "taskDescription") is None

    empty_desc = CardWidget(3, "Task", Priority.LOW, None, description="")
    assert empty_desc.findChild(QLabel, "taskDescription") is None


def test_card_description_below_title(qapp) -> None:
    """The description label must sit directly under the title label."""
    from PySide6.QtWidgets import QLabel, QLayout

    card = CardWidget(1, "Task", Priority.LOW, None, description="Notes")
    title = card.findChild(QLabel, "taskTitle")
    desc = card.findChild(QLabel, "taskDescription")
    assert title is not None
    assert desc is not None
    main = card.layout()
    assert main is not None

    def index_of(layout: QLayout, widget: QLabel) -> int:
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item is not None and item.widget() is widget:
                return i
        return -1

    assert index_of(main, desc) == index_of(main, title) + 1


def test_card_title_font_larger_than_description(qapp) -> None:
    """The title must be bold and larger than the description text."""
    from PySide6.QtWidgets import QLabel

    card = CardWidget(1, "Task", Priority.LOW, None, description="Notes")
    title = card.findChild(QLabel, "taskTitle")
    desc = card.findChild(QLabel, "taskDescription")
    assert title is not None
    assert desc is not None
    assert title.font().bold()
    assert title.font().pointSize() > desc.font().pointSize()


def test_notes_button_exists_on_card(qapp) -> None:
    """The card must expose a notes button with a relevant icon."""
    from PySide6.QtWidgets import QPushButton

    card = CardWidget(1, "Task", Priority.LOW, None)
    button = card.findChild(QPushButton, "notesButton")
    assert button is not None
    assert not button.icon().isNull()


def test_notes_popup_is_retained(qapp) -> None:
    """The notes popup must be retained so it stays visible after the click."""
    import gc

    from PySide6.QtWidgets import QTextEdit, QWidget

    card = CardWidget(1, "Task", Priority.LOW, None, description="Existing")
    card._show_notes_popup()
    gc.collect()
    assert isinstance(card._notes_popup, QWidget)
    assert card._notes_popup.isVisible()
    assert isinstance(card._notes_edit, QTextEdit)
    assert card._notes_edit.toPlainText() == "Existing"


def test_card_description_set_emits(qapp) -> None:
    """Confirming the notes popup emits description_changed with the text."""
    from PySide6.QtWidgets import QTextEdit

    card = CardWidget(5, "Task", Priority.LOW, None)
    emitted: list[tuple[int, object]] = []
    card.description_changed.connect(lambda tid, d: emitted.append((tid, d)))
    card._notes_edit = QTextEdit()
    card._notes_edit.setPlainText("My notes")
    card._on_set_description()
    assert emitted == [(5, "My notes")]


def test_card_description_clear_emits_none(qapp) -> None:
    """Clearing the description emits description_changed with None."""
    card = CardWidget(5, "Task", Priority.LOW, None)
    emitted: list[tuple[int, object]] = []
    card.description_changed.connect(lambda tid, d: emitted.append((tid, d)))
    card._on_clear_description()
    assert emitted == [(5, None)]


def test_column_add_task_field_maxlength(qapp) -> None:
    """The column's add-task field must cap the title at 128 characters."""
    column = ColumnWidget(1, "To Do", [])
    assert column._add_edit.maxLength() == 128


def test_board_view_forwards_description_changed(qapp) -> None:
    """The board view must forward the card's description_changed signal."""
    view = BoardView()
    captured: list[tuple[int, object]] = []
    view.description_changed.connect(lambda *a: captured.append(a))
    column = ColumnWidget(9, "To Do", [])
    view.add_column_widget(column)
    column.description_changed.emit(1, "notes")
    assert captured == [(1, "notes")]


def test_set_description_persists(window: MainWindow) -> None:
    """Setting a task's description updates and persists it."""
    board = window._service.get_board_full(window._current_board_id)
    assert board is not None
    column = board.columns[0]
    window._on_task_added(column.id, "Desc task")
    board = window._service.get_board_full(window._current_board_id)
    assert board is not None
    task = board.columns[0].tasks[0]
    window._on_description_changed(task.id, "Some notes")
    board = window._service.get_board_full(window._current_board_id)
    assert board is not None
    assert board.columns[0].tasks[0].description == "Some notes"


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


def test_board_view_has_no_add_column_button(qapp) -> None:
    """The add-column control lives in the sidebar, not the board view."""
    from PySide6.QtWidgets import QPushButton

    view = BoardView()
    buttons = view.findChildren(QPushButton)
    assert not any(b.accessibleName() == "Add column" for b in buttons)


def test_column_accepts_drop_and_emits_task_moved(qapp) -> None:
    column = ColumnWidget(
        5,
        "To Do",
        [
            (10, "A", Priority.LOW, None, [], [], None),
            (11, "B", Priority.HIGH, None, [], [], None),
        ],
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
        [
            (10, "A", Priority.LOW, None, [], [], None),
            (11, "B", Priority.HIGH, None, [], [], None),
        ],
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


def test_sidebar_rename_button_opens_editor(qapp) -> None:
    """Clicking the pencil button must open the inline rename editor."""
    from PySide6.QtWidgets import QLineEdit, QPushButton

    from kanban.models import Board
    from kanban.ui.sidebar import Sidebar

    sidebar = Sidebar()
    sidebar.load_boards([Board(id=1, name="A")])
    sidebar._list.setCurrentRow(0)
    button = next(
        b for b in sidebar.findChildren(QPushButton) if b.accessibleName() == "Rename board"
    )
    button.click()
    assert sidebar._list.findChild(QLineEdit) is not None


def test_sidebar_columns_section_adds_column(window: MainWindow) -> None:
    """The sidebar Columns section adds a column to the current board."""
    from PySide6.QtWidgets import QPushButton

    sidebar = window._sidebar
    board_id = window._current_board_id
    assert board_id is not None

    sidebar._column_edit.setText("In Progress")
    button = next(
        b for b in sidebar.findChildren(QPushButton) if b.accessibleName() == "Add column"
    )
    button.click()

    board = window._service.get_board_full(board_id)
    assert board is not None
    assert [c.title for c in board.columns] == ["To Do", "In Progress"]
    assert sidebar._column_edit.text() == ""


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
        [(10, "A", Priority.LOW, None, [], [], None)],
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


def test_search_bar_due_fields_are_plain_text(qapp) -> None:
    """The due-date fields must be plain, typeable text boxes."""
    from PySide6.QtWidgets import QLineEdit

    from kanban.ui.search_bar import SearchBar

    bar = SearchBar()
    assert isinstance(bar._due_after, QLineEdit)
    assert isinstance(bar._due_before, QLineEdit)
    assert bar._due_after.isEnabled()
    assert bar._due_before.isEnabled()


def test_search_bar_due_filter_activates_on_date_set(qapp) -> None:
    """Typing a due date activates that filter; untouched fields stay off."""
    from kanban.ui.search_bar import SearchBar

    bar = SearchBar()
    assert bar.build_filters()["due_after"] is None
    assert bar.build_filters()["due_before"] is None

    bar._due_after.setText("2024-01-01")
    filters = bar.build_filters()
    assert filters["due_after"] == date(2024, 1, 1)
    assert filters["due_before"] is None


def test_search_bar_due_range(qapp) -> None:
    from kanban.ui.search_bar import SearchBar

    bar = SearchBar()
    bar._due_after.setText("2024-01-01")
    bar._due_before.setText("2024-01-31")
    filters = bar.build_filters()
    assert filters["due_after"] == date(2024, 1, 1)
    assert filters["due_before"] == date(2024, 1, 31)


def test_search_bar_invalid_due_text_is_ignored(qapp) -> None:
    """Unparseable due-date text must not contribute a filter."""
    from kanban.ui.search_bar import SearchBar

    bar = SearchBar()
    bar._due_after.setText("not-a-date")
    assert bar.build_filters()["due_after"] is None


def test_search_bar_calendar_button_opens_popup(qapp) -> None:
    """The calendar button must open a retained QCalendarWidget popup."""
    from PySide6.QtWidgets import QCalendarWidget, QPushButton

    from kanban.ui.search_bar import SearchBar

    bar = SearchBar()
    button = bar._due_after_calendar
    assert isinstance(button, QPushButton)
    assert not button.icon().isNull()

    bar._show_due_calendar(button, bar._due_after)
    assert bar._due_calendar_popup is not None
    assert bar._due_calendar_popup.isVisible()
    assert isinstance(bar._due_calendar_popup.findChild(QCalendarWidget), QCalendarWidget)


def test_search_bar_calendar_selection_updates_field(qapp) -> None:
    """Picking a date in the calendar popup writes it into the target field."""
    from PySide6.QtCore import QDate
    from PySide6.QtWidgets import QCalendarWidget

    from kanban.ui.search_bar import SearchBar

    bar = SearchBar()
    bar._show_due_calendar(bar._due_after_calendar, bar._due_after)
    calendar = bar._due_calendar_popup.findChild(QCalendarWidget)
    calendar.setSelectedDate(QDate(2025, 6, 15))
    calendar.selectionChanged.emit()
    assert bar._due_after.text() == "2025-06-15"
    assert bar.build_filters()["due_after"] == date(2025, 6, 15)


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


def test_theme_button_present(window: MainWindow) -> None:
    """The search bar must expose a theme button with System/Light/Dark actions."""
    from PySide6.QtGui import QAction

    actions = window._search_bar._theme_actions
    assert set(actions) == {"system", "light", "dark"}
    for action in actions.values():
        assert isinstance(action, QAction)
        assert action.isCheckable()


def test_theme_button_has_icon(window: MainWindow) -> None:
    """The theme button must carry a relevant icon."""
    button = window._search_bar._theme_button
    assert not button.icon().isNull()


def test_menu_bar_is_eliminated(window: MainWindow) -> None:
    """The menu bar must be gone; theme control lives in the search bar."""
    assert window.menuBar().actions() == []


def test_theme_actions_are_exclusive(window: MainWindow) -> None:
    """Theme actions must behave like radio buttons (one checked at a time)."""
    actions = window._search_bar._theme_actions
    actions["dark"].trigger()
    assert actions["dark"].isChecked()
    assert not actions["light"].isChecked()
    assert not actions["system"].isChecked()


def test_select_dark_theme_applies_and_persists(window: MainWindow) -> None:
    """Choosing Dark applies the dark stylesheet and persists the choice."""
    from PySide6.QtWidgets import QApplication

    from kanban.ui.theme import DARK_QSS

    window._search_bar._theme_actions["dark"].trigger()
    assert QApplication.instance().styleSheet() == DARK_QSS
    assert window._settings.theme_mode() == "dark"


def test_select_light_theme_applies_and_persists(window: MainWindow) -> None:
    """Choosing Light applies the light stylesheet and persists the choice."""
    from PySide6.QtWidgets import QApplication

    from kanban.ui.theme import LIGHT_QSS

    window._search_bar._theme_actions["light"].trigger()
    assert QApplication.instance().styleSheet() == LIGHT_QSS
    assert window._settings.theme_mode() == "light"


def test_select_system_theme_persists(window: MainWindow) -> None:
    """Choosing System persists the choice and re-applies the detected theme."""
    from PySide6.QtWidgets import QApplication

    from kanban.ui.theme import DARK_QSS, LIGHT_QSS

    window._search_bar._theme_actions["system"].trigger()
    assert window._settings.theme_mode() == "system"
    assert QApplication.instance().styleSheet() in {LIGHT_QSS, DARK_QSS}


def _qss_rule(qss: str, selector: str) -> str:
    """Return the declaration block for ``selector`` (e.g. ``QMenu::item``)."""
    needle = selector + " {"
    idx = qss.find(needle)
    assert idx != -1, f"{selector!r} rule not found in QSS"
    brace = idx + len(selector)
    end = qss.find("}", brace)
    return qss[brace + 1 : end]


def _menu_item_bg_luma(qss: str) -> float:
    """Average RGB of the ``QMenu::item`` background color in a stylesheet."""
    rule = _qss_rule(qss, "QMenu::item")
    hexval = rule.split("background-color:", 1)[1].split(";", 1)[0].strip().lstrip("#")
    return (int(hexval[0:2], 16) + int(hexval[2:4], 16) + int(hexval[4:6], 16)) / 3


def test_menu_items_explicitly_styled_in_both_themes() -> None:
    """Menu items must be styled explicitly so they stay visible and on-theme.

    Relying on the system palette for ``QMenu::item`` leaves dropdown menus
    invisible or mismatched on the native Windows style; an explicit rule with
    both a background and a text color fixes that.
    """
    from kanban.ui.theme import DARK_QSS, LIGHT_QSS

    for qss in (LIGHT_QSS, DARK_QSS):
        rule = _qss_rule(qss, "QMenu::item")
        assert "background-color" in rule, "QMenu::item lacks an explicit background"
        assert "color" in rule, "QMenu::item lacks an explicit text color"


def test_menu_item_backgrounds_match_theme() -> None:
    """Light-theme menu items must be lighter than dark-theme menu items."""
    from kanban.ui.theme import DARK_QSS, LIGHT_QSS

    assert _menu_item_bg_luma(LIGHT_QSS) > _menu_item_bg_luma(DARK_QSS)
