"""Tests for the task CRUD service."""

from __future__ import annotations

from datetime import date

import pytest

from kanban.models import Priority
from kanban.services.database import Database
from kanban.services.task_service import (
    DEFAULT_COLUMNS,
    PLACEHOLDER_TASK_DESCRIPTION,
    PLACEHOLDER_TASK_TITLE,
    TaskService,
)


@pytest.fixture
def service(database: Database) -> TaskService:
    return TaskService(database)


def test_create_board_with_default_column(service: TaskService) -> None:
    board = service.create_board("Work")
    assert board.id is not None
    assert [c.title for c in board.columns] == ["To Do"]


def test_create_default_board_seeds_columns_and_placeholder(service: TaskService) -> None:
    created = service.create_default_board()
    assert created.id is not None
    board = service.get_board_full(created.id)
    assert board is not None
    assert [c.title for c in board.columns] == DEFAULT_COLUMNS
    assert len(board.columns) == 4

    first = board.columns[0]
    assert len(first.tasks) == 1
    task = first.tasks[0]
    assert task.title == PLACEHOLDER_TASK_TITLE
    assert task.description == PLACEHOLDER_TASK_DESCRIPTION

    # Only the first column carries the placeholder card.
    for column in board.columns[1:]:
        assert column.tasks == []


def test_create_and_get_task(service: TaskService) -> None:
    board = service.create_board("Work")
    column = board.columns[0]
    task = service.create_task(column.id, "Write tests", priority=Priority.HIGH)
    assert task.id is not None

    fetched = service.get_task(task.id)
    assert fetched is not None
    assert fetched.title == "Write tests"
    assert fetched.priority is Priority.HIGH


def test_create_task_in_missing_column_raises(service: TaskService) -> None:
    with pytest.raises(LookupError):
        service.create_task(9999, "nope")


def test_update_task(service: TaskService) -> None:
    board = service.create_board("Work")
    task = service.create_task(board.columns[0].id, "Original")
    updated = service.update_task(task.id, title="Renamed", due_date=date(2025, 12, 1))
    assert updated.title == "Renamed"
    assert updated.due_date == date(2025, 12, 1)


def test_update_task_unknown_field_raises(service: TaskService) -> None:
    board = service.create_board("Work")
    task = service.create_task(board.columns[0].id, "Original")
    with pytest.raises(ValueError):
        service.update_task(task.id, not_a_field="x")


def test_create_task_truncates_title_to_128(service: TaskService) -> None:
    board = service.create_board("Work")
    long_title = "x" * 200
    task = service.create_task(board.columns[0].id, long_title)
    assert len(task.title) == 128
    assert task.title == "x" * 128


def test_update_task_truncates_title_to_128(service: TaskService) -> None:
    board = service.create_board("Work")
    task = service.create_task(board.columns[0].id, "Short")
    updated = service.update_task(task.id, title="y" * 300)
    assert len(updated.title) == 128
    assert updated.title == "y" * 128


def test_move_task_between_columns(service: TaskService) -> None:
    board = service.create_board("Work")
    todo = board.columns[0]
    doing = service.create_column(board.id, "In Progress")
    task = service.create_task(todo.id, "Move me")

    service.move_task(task.id, doing.id, 0)
    assert service.list_tasks_in_column(todo.id) == []
    assert [t.id for t in service.list_tasks_in_column(doing.id)] == [task.id]


def test_move_task_renumbers_target_column(service: TaskService) -> None:
    board = service.create_board("Work")
    doing = service.create_column(board.id, "In Progress")
    a = service.create_task(doing.id, "A")
    service.create_task(doing.id, "B")
    service.create_task(doing.id, "C")

    # Move A to the end of the same column; order should become B, C, A.
    service.move_task(a.id, doing.id, 3)
    assert [t.title for t in service.list_tasks_in_column(doing.id)] == ["B", "C", "A"]


def test_move_task_renumbers_source_column(service: TaskService) -> None:
    board = service.create_board("Work")
    todo = board.columns[0]
    doing = service.create_column(board.id, "In Progress")
    a = service.create_task(todo.id, "A")
    service.create_task(todo.id, "B")
    service.create_task(todo.id, "C")

    service.move_task(a.id, doing.id, 0)
    assert [t.title for t in service.list_tasks_in_column(todo.id)] == ["B", "C"]
    assert [t.title for t in service.list_tasks_in_column(doing.id)] == ["A"]


def test_move_task_clamps_out_of_range_index(service: TaskService) -> None:
    board = service.create_board("Work")
    todo = board.columns[0]
    doing = service.create_column(board.id, "In Progress")
    a = service.create_task(todo.id, "A")
    service.create_task(todo.id, "B")

    # An index beyond the end should clamp to the end of the target column.
    service.move_task(a.id, doing.id, 99)
    assert [t.title for t in service.list_tasks_in_column(doing.id)] == ["A"]
    assert [t.title for t in service.list_tasks_in_column(todo.id)] == ["B"]


def test_move_task_reorder_within_column(service: TaskService) -> None:
    board = service.create_board("Work")
    todo = board.columns[0]
    service.create_task(todo.id, "A")
    service.create_task(todo.id, "B")
    c = service.create_task(todo.id, "C")

    # Move C to the front of the same column.
    service.move_task(c.id, todo.id, 0)
    assert [t.title for t in service.list_tasks_in_column(todo.id)] == ["C", "A", "B"]


def test_delete_task(service: TaskService) -> None:
    board = service.create_board("Work")
    task = service.create_task(board.columns[0].id, "Delete me")
    service.delete_task(task.id)
    assert service.get_task(task.id) is None


def test_delete_missing_task_raises(service: TaskService) -> None:
    with pytest.raises(LookupError):
        service.delete_task(9999)


# -- Boards ---------------------------------------------------------------
def test_rename_board(service: TaskService) -> None:
    board = service.create_board("Work")
    renamed = service.rename_board(board.id, "Personal")
    assert renamed.name == "Personal"
    assert service.get_board(board.id) is not None
    assert service.get_board(board.id).name == "Personal"


def test_rename_missing_board_raises(service: TaskService) -> None:
    with pytest.raises(LookupError):
        service.rename_board(9999, "Nope")


def test_delete_board_cascades(service: TaskService) -> None:
    board = service.create_board("Work")
    column = board.columns[0]
    service.create_task(column.id, "Task")
    service.delete_board(board.id)
    assert service.get_board(board.id) is None
    assert service.list_boards() == []


def test_delete_missing_board_raises(service: TaskService) -> None:
    with pytest.raises(LookupError):
        service.delete_board(9999)


# -- Columns --------------------------------------------------------------
def test_rename_column(service: TaskService) -> None:
    board = service.create_board("Work")
    column = board.columns[0]
    renamed = service.rename_column(column.id, "Backlog")
    assert renamed.title == "Backlog"


def test_rename_missing_column_raises(service: TaskService) -> None:
    with pytest.raises(LookupError):
        service.rename_column(9999, "Nope")


def test_move_column_reorders(service: TaskService) -> None:
    board = service.create_board("Work")
    service.create_column(board.id, "B")
    c = service.create_column(board.id, "C")

    service.move_column(c.id, 0)
    titles = [col.title for col in service.get_board_full(board.id).columns]
    assert titles == ["C", "To Do", "B"]


def test_move_column_clamps_out_of_range(service: TaskService) -> None:
    board = service.create_board("Work")
    a = board.columns[0]
    service.create_column(board.id, "B")

    # Index beyond the end should clamp to the last position.
    service.move_column(a.id, 99)
    titles = [col.title for col in service.get_board_full(board.id).columns]
    assert titles == ["B", "To Do"]


def test_move_column_clamps_negative(service: TaskService) -> None:
    board = service.create_board("Work")
    a = board.columns[0]
    service.create_column(board.id, "B")

    service.move_column(a.id, -5)
    titles = [col.title for col in service.get_board_full(board.id).columns]
    assert titles == ["To Do", "B"]


def test_move_missing_column_raises(service: TaskService) -> None:
    with pytest.raises(LookupError):
        service.move_column(9999, 0)


def test_delete_column_renumbers_and_cascades(service: TaskService) -> None:
    board = service.create_board("Work")
    b = service.create_column(board.id, "B")
    service.create_column(board.id, "C")
    service.create_task(b.id, "Task in B")

    service.delete_column(b.id)
    full = service.get_board_full(board.id)
    assert [col.title for col in full.columns] == ["To Do", "C"]
    assert [col.order_idx for col in full.columns] == [0, 1]
    assert service.list_tasks_in_column(b.id) == []


def test_delete_missing_column_raises(service: TaskService) -> None:
    with pytest.raises(LookupError):
        service.delete_column(9999)


# -- Labels ---------------------------------------------------------------
def test_create_and_list_labels(service: TaskService) -> None:
    board = service.create_board("Work")
    red = service.create_label(board.id, "Bug", color="#ff0000")
    service.create_label(board.id, "Feature")

    labels = service.list_labels(board.id)
    assert [lbl.name for lbl in labels] == ["Bug", "Feature"]
    assert red.color == "#ff0000"


def test_create_label_missing_board_raises(service: TaskService) -> None:
    with pytest.raises(LookupError):
        service.create_label(9999, "Bug")


def test_list_labels_missing_board_returns_empty(service: TaskService) -> None:
    assert service.list_labels(9999) == []


def test_assign_and_unassign_label(service: TaskService) -> None:
    board = service.create_board("Work")
    task = service.create_task(board.columns[0].id, "Task")
    label = service.create_label(board.id, "Bug")

    service.assign_label(task.id, label.id)
    assert [lbl.id for lbl in service.get_task(task.id).labels] == [label.id]

    # Assigning again should be idempotent.
    service.assign_label(task.id, label.id)
    assert len(service.get_task(task.id).labels) == 1

    service.unassign_label(task.id, label.id)
    assert service.get_task(task.id).labels == []

    # Unassigning again should be idempotent.
    service.unassign_label(task.id, label.id)
    assert service.get_task(task.id).labels == []


def test_assign_label_missing_raises(service: TaskService) -> None:
    board = service.create_board("Work")
    task = service.create_task(board.columns[0].id, "Task")
    with pytest.raises(LookupError):
        service.assign_label(task.id, 9999)
    with pytest.raises(LookupError):
        service.assign_label(9999, 1)


def test_delete_label_removes_from_tasks(service: TaskService) -> None:
    board = service.create_board("Work")
    task = service.create_task(board.columns[0].id, "Task")
    label = service.create_label(board.id, "Bug")
    service.assign_label(task.id, label.id)

    service.delete_label(label.id)
    assert service.list_labels(board.id) == []
    assert service.get_task(task.id).labels == []


def test_delete_missing_label_raises(service: TaskService) -> None:
    with pytest.raises(LookupError):
        service.delete_label(9999)


# -- Search ---------------------------------------------------------------
def test_search_returns_all_when_no_filters(service: TaskService) -> None:
    board = service.create_board("Work")
    service.create_task(board.columns[0].id, "A")
    service.create_task(board.columns[0].id, "B")
    assert len(service.search_tasks(board.id)) == 2


def test_search_by_query_title_and_description(service: TaskService) -> None:
    board = service.create_board("Work")
    col = board.columns[0]
    service.create_task(col.id, "Write tests", description="cover the service")
    service.create_task(col.id, "Ship it", description="release notes")

    by_title = service.search_tasks(board.id, query="write")
    assert [t.title for t in by_title] == ["Write tests"]

    by_description = service.search_tasks(board.id, query="release")
    assert [t.title for t in by_description] == ["Ship it"]


def test_search_by_priority(service: TaskService) -> None:
    board = service.create_board("Work")
    col = board.columns[0]
    service.create_task(col.id, "Low", priority=Priority.LOW)
    service.create_task(col.id, "High", priority=Priority.HIGH)

    results = service.search_tasks(board.id, priority=Priority.HIGH)
    assert [t.title for t in results] == ["High"]


def test_search_by_column(service: TaskService) -> None:
    board = service.create_board("Work")
    todo = board.columns[0]
    doing = service.create_column(board.id, "In Progress")
    service.create_task(todo.id, "In todo")
    service.create_task(doing.id, "In doing")

    results = service.search_tasks(board.id, column_id=doing.id)
    assert [t.title for t in results] == ["In doing"]


def test_search_by_due_date_range(service: TaskService) -> None:
    board = service.create_board("Work")
    col = board.columns[0]
    service.create_task(col.id, "Early", due_date=date(2025, 1, 1))
    service.create_task(col.id, "Mid", due_date=date(2025, 6, 1))
    service.create_task(col.id, "Late", due_date=date(2025, 12, 1))

    before = service.search_tasks(board.id, due_before=date(2025, 6, 1))
    assert [t.title for t in before] == ["Early", "Mid"]

    after = service.search_tasks(board.id, due_after=date(2025, 6, 1))
    assert [t.title for t in after] == ["Mid", "Late"]


def test_search_by_label(service: TaskService) -> None:
    board = service.create_board("Work")
    col = board.columns[0]
    t1 = service.create_task(col.id, "Tagged")
    service.create_task(col.id, "Untagged")
    label = service.create_label(board.id, "Bug")
    service.assign_label(t1.id, label.id)

    results = service.search_tasks(board.id, label_id=label.id)
    assert [t.title for t in results] == ["Tagged"]


def test_search_combines_filters(service: TaskService) -> None:
    board = service.create_board("Work")
    col = board.columns[0]
    match = service.create_task(col.id, "Alpha bug", priority=Priority.HIGH)
    service.create_task(col.id, "Alpha feature", priority=Priority.LOW)
    service.create_task(col.id, "Beta bug", priority=Priority.HIGH)
    label = service.create_label(board.id, "Bug")
    service.assign_label(match.id, label.id)

    results = service.search_tasks(
        board.id,
        query="alpha",
        priority=Priority.HIGH,
        label_id=label.id,
    )
    assert [t.title for t in results] == ["Alpha bug"]


def test_search_scoped_to_board(service: TaskService) -> None:
    board_a = service.create_board("A")
    board_b = service.create_board("B")
    service.create_task(board_a.columns[0].id, "In A")
    service.create_task(board_b.columns[0].id, "In B")

    assert [t.title for t in service.search_tasks(board_a.id)] == ["In A"]
    assert [t.title for t in service.search_tasks(board_b.id)] == ["In B"]


# -- Archive -----------------------------------------------------------
def test_new_task_is_not_archived_by_default(service: TaskService) -> None:
    board = service.create_board("Work")
    task = service.create_task(board.columns[0].id, "Fresh")
    assert task.archived is False


def test_archive_task(service: TaskService) -> None:
    board = service.create_board("Work")
    task = service.create_task(board.columns[0].id, "Archive me")
    archived = service.archive_task(task.id)
    assert archived.archived is True


def test_restore_task(service: TaskService) -> None:
    board = service.create_board("Work")
    task = service.create_task(board.columns[0].id, "Restore me")
    service.archive_task(task.id)
    restored = service.restore_task(task.id)
    assert restored.archived is False


def test_archive_unknown_task_raises(service: TaskService) -> None:
    with pytest.raises(LookupError):
        service.archive_task(9999)


def test_restore_unknown_task_raises(service: TaskService) -> None:
    with pytest.raises(LookupError):
        service.restore_task(9999)


def test_list_archived_tasks(service: TaskService) -> None:
    board = service.create_board("Work")
    todo = board.columns[0]
    a = service.create_task(todo.id, "A")
    service.create_task(todo.id, "B")
    c = service.create_task(todo.id, "C")
    service.archive_task(a.id)
    service.archive_task(c.id)

    archived = service.list_archived_tasks(board.id)
    assert [t.id for t in archived] == [a.id, c.id]
    assert all(t.archived for t in archived)


def test_list_archived_tasks_scoped_to_board(service: TaskService) -> None:
    board_a = service.create_board("A")
    board_b = service.create_board("B")
    ta = service.create_task(board_a.columns[0].id, "In A")
    tb = service.create_task(board_b.columns[0].id, "In B")
    service.archive_task(ta.id)
    service.archive_task(tb.id)

    assert [t.id for t in service.list_archived_tasks(board_a.id)] == [ta.id]
    assert [t.id for t in service.list_archived_tasks(board_b.id)] == [tb.id]


def test_list_archived_tasks_empty(service: TaskService) -> None:
    board = service.create_board("Work")
    service.create_task(board.columns[0].id, "Not archived")
    assert service.list_archived_tasks(board.id) == []
