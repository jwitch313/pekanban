"""Tests for bulk operations (Step 6, Slice 3, F-22)."""

from __future__ import annotations

from datetime import date

import pytest

from kanban.models import Priority
from kanban.services.bulk_service import BulkService
from kanban.services.database import Database
from kanban.services.task_service import TaskService


@pytest.fixture
def service(database: Database) -> BulkService:
    return BulkService(database)


@pytest.fixture
def task_service(database: Database) -> TaskService:
    return TaskService(database)


def _board_with_two_columns(task_service: TaskService, name: str) -> tuple[int, int]:
    board = task_service.create_board(name)
    first = board.columns[0].id
    second = task_service.create_column(board.id, "Done").id
    return first, second


def _task(task_service: TaskService, column_id: int, title: str) -> int:
    return task_service.create_task(column_id, title).id


def test_move_tasks_appends_in_selection_order(
    service: BulkService, task_service: TaskService
) -> None:
    src, dst = _board_with_two_columns(task_service, "Move")
    a = _task(task_service, src, "a")
    _task(task_service, src, "b")
    c = _task(task_service, src, "c")
    _task(task_service, dst, "existing")

    moved = service.move_tasks([c, a], dst)

    assert [t.id for t in moved] == [c, a]
    titles = [t.title for t in task_service.list_tasks_in_column(dst)]
    assert titles == ["existing", "c", "a"]
    assert [t.title for t in task_service.list_tasks_in_column(src)] == ["b"]


def test_move_tasks_renumbers_source(
    service: BulkService, task_service: TaskService
) -> None:
    src, dst = _board_with_two_columns(task_service, "Renumber")
    a = _task(task_service, src, "a")
    b = _task(task_service, src, "b")
    c = _task(task_service, src, "c")

    service.move_tasks([a, c], dst)

    remaining = task_service.list_tasks_in_column(src)
    assert [t.id for t in remaining] == [b]
    assert remaining[0].order_idx == 0


def test_move_tasks_empty_selection_raises(service: BulkService, task_service: TaskService) -> None:
    _, dst = _board_with_two_columns(task_service, "Empty")
    with pytest.raises(ValueError):
        service.move_tasks([], dst)


def test_move_tasks_missing_task_raises(service: BulkService, task_service: TaskService) -> None:
    src, dst = _board_with_two_columns(task_service, "Missing")
    a = _task(task_service, src, "a")
    with pytest.raises(LookupError):
        service.move_tasks([a, 9999], dst)


def test_move_tasks_missing_column_raises(service: BulkService, task_service: TaskService) -> None:
    src, _ = _board_with_two_columns(task_service, "NoColumn")
    a = _task(task_service, src, "a")
    with pytest.raises(LookupError):
        service.move_tasks([a], 9999)


def test_update_tasks_batch_edit(service: BulkService, task_service: TaskService) -> None:
    src, _ = _board_with_two_columns(task_service, "Edit")
    a = _task(task_service, src, "a")
    b = _task(task_service, src, "b")
    other = _task(task_service, src, "other")

    updated = service.update_tasks([a, b], priority=Priority.HIGH, due_date=date(2026, 4, 1))

    assert {t.id for t in updated} == {a, b}
    for tid in (a, b):
        task = task_service.get_task(tid)
        assert task is not None
        assert task.priority is Priority.HIGH
        assert task.due_date == date(2026, 4, 1)
    untouched = task_service.get_task(other)
    assert untouched is not None
    assert untouched.priority is Priority.MEDIUM


def test_update_tasks_invalid_field_raises(service: BulkService, task_service: TaskService) -> None:
    src, _ = _board_with_two_columns(task_service, "BadField")
    a = _task(task_service, src, "a")
    with pytest.raises(ValueError):
        service.update_tasks([a], bogus=True)


def test_update_tasks_no_fields_raises(service: BulkService, task_service: TaskService) -> None:
    src, _ = _board_with_two_columns(task_service, "NoFields")
    a = _task(task_service, src, "a")
    with pytest.raises(ValueError):
        service.update_tasks([a])


def test_delete_tasks(service: BulkService, task_service: TaskService) -> None:
    src, _ = _board_with_two_columns(task_service, "Delete")
    a = _task(task_service, src, "a")
    b = _task(task_service, src, "b")
    c = _task(task_service, src, "c")

    deleted = service.delete_tasks([a, c])

    assert deleted == 2
    remaining = task_service.list_tasks_in_column(src)
    assert [t.id for t in remaining] == [b]
    assert remaining[0].order_idx == 0
    assert task_service.get_task(a) is None
    assert task_service.get_task(c) is None


def test_delete_tasks_deduplicates(service: BulkService, task_service: TaskService) -> None:
    src, _ = _board_with_two_columns(task_service, "Dedupe")
    a = _task(task_service, src, "a")
    assert service.delete_tasks([a, a]) == 1
