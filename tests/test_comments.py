"""Tests for comments (Step 5, Slice 5, F-14)."""

from __future__ import annotations

import pytest

from kanban.models import Comment
from kanban.services.comment_service import CommentService
from kanban.services.database import Database
from kanban.services.task_service import TaskService


@pytest.fixture
def service(database: Database) -> CommentService:
    return CommentService(database)


def _task(database: Database) -> int:
    task_service = TaskService(database)
    board = task_service.create_board("Work")
    task = task_service.create_task(board.columns[0].id, "Discussed")
    return task.id


def test_add_comment_returns_comment(service: CommentService, database: Database) -> None:
    task_id = _task(database)

    comment = service.add_comment(task_id, "  First thought  ", user_name="alice")

    assert comment.id is not None
    assert comment.task_id == task_id
    assert comment.content == "First thought"
    assert comment.user_name == "alice"


def test_add_comment_blank_raises(service: CommentService, database: Database) -> None:
    task_id = _task(database)
    with pytest.raises(ValueError):
        service.add_comment(task_id, "   ")


def test_add_comment_missing_task_raises(service: CommentService) -> None:
    with pytest.raises(LookupError):
        service.add_comment(9999, "hello")


def test_list_comments_chronological(service: CommentService, database: Database) -> None:
    task_id = _task(database)
    service.add_comment(task_id, "one")
    service.add_comment(task_id, "two")
    service.add_comment(task_id, "three")

    comments = service.list_comments(task_id)

    assert [c.content for c in comments] == ["one", "two", "three"]
    assert all(isinstance(c, Comment) for c in comments)


def test_list_comments_missing_task_raises(service: CommentService) -> None:
    with pytest.raises(LookupError):
        service.list_comments(9999)


def test_delete_comment(service: CommentService, database: Database) -> None:
    task_id = _task(database)
    first = service.add_comment(task_id, "keep")
    second = service.add_comment(task_id, "remove")

    service.delete_comment(second.id)

    assert [c.id for c in service.list_comments(task_id)] == [first.id]


def test_delete_comment_missing_raises(service: CommentService) -> None:
    with pytest.raises(LookupError):
        service.delete_comment(9999)


def test_find_mentions_multiple_and_dedup() -> None:
    mentions = CommentService.find_mentions("ping @alice and @bob, cc @alice again")
    assert mentions == ["alice", "bob"]


def test_find_mentions_none() -> None:
    assert CommentService.find_mentions("no mentions here") == []


def test_find_mentions_matches_any_at_handle() -> None:
    # The regex treats any @handle as a mention, including email domains.
    assert CommentService.find_mentions("email me at alice@example.com") == ["example"]
