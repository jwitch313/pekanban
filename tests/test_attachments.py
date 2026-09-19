"""Tests for file attachments (Step 5, Slice 4, F-13/F-31/F-32)."""

from __future__ import annotations

import pytest

from kanban.models import Attachment
from kanban.services.attachment_service import (
    MAX_ATTACHMENT_BYTES,
    STORAGE_WARNING_BYTES,
    AttachmentService,
)
from kanban.services.database import Database
from kanban.services.task_service import TaskService


@pytest.fixture
def service(database: Database, tmp_path) -> AttachmentService:
    return AttachmentService(database, storage_dir=tmp_path / "attachments")


def _task(database: Database) -> int:
    task_service = TaskService(database)
    board = task_service.create_board("Work")
    task = task_service.create_task(board.columns[0].id, "With file")
    return task.id


def test_attach_file_copies_and_records(
    service: AttachmentService, database: Database, tmp_path
) -> None:
    task_id = _task(database)
    source = tmp_path / "notes.txt"
    source.write_text("hello attachment", encoding="utf-8")

    attachment = service.attach_file(task_id, source)

    assert attachment.id is not None
    assert attachment.filename == "notes.txt"
    assert attachment.size_bytes == len(b"hello attachment")
    assert attachment.mime_type == "text/plain"
    stored = tmp_path / "attachments"
    files = list(stored.iterdir())
    assert len(files) == 1
    assert files[0].read_text(encoding="utf-8") == "hello attachment"


def test_attach_file_missing_source_raises(service: AttachmentService, database: Database) -> None:
    task_id = _task(database)
    with pytest.raises(FileNotFoundError):
        service.attach_file(task_id, "does/not/exist.txt")


def test_attach_file_missing_task_raises(service: AttachmentService, tmp_path) -> None:
    source = tmp_path / "a.txt"
    source.write_text("x", encoding="utf-8")
    with pytest.raises(LookupError):
        service.attach_file(9999, source)


def test_attach_file_exceeds_limit_raises(
    service: AttachmentService, database: Database, tmp_path
) -> None:
    task_id = _task(database)
    source = tmp_path / "big.bin"
    # Sparse file: set size without writing the bytes.
    with source.open("w+b") as handle:
        handle.seek(MAX_ATTACHMENT_BYTES)
        handle.write(b"\0")
    with pytest.raises(ValueError):
        service.attach_file(task_id, source)


def test_list_attachments(service: AttachmentService, database: Database, tmp_path) -> None:
    task_id = _task(database)
    for name in ("a.txt", "b.txt"):
        source = tmp_path / name
        source.write_text(name, encoding="utf-8")
        service.attach_file(task_id, source)

    attachments = service.list_attachments(task_id)
    assert [a.filename for a in attachments] == ["a.txt", "b.txt"]


def test_delete_attachment_removes_file_and_record(
    service: AttachmentService, database: Database, tmp_path
) -> None:
    task_id = _task(database)
    source = tmp_path / "a.txt"
    source.write_text("x", encoding="utf-8")
    attachment = service.attach_file(task_id, source)

    service.delete_attachment(attachment.id)

    assert service.list_attachments(task_id) == []
    assert list((tmp_path / "attachments").iterdir()) == []


def test_delete_attachment_missing_raises(service: AttachmentService) -> None:
    with pytest.raises(LookupError):
        service.delete_attachment(9999)


def test_total_storage_bytes(service: AttachmentService, database: Database, tmp_path) -> None:
    task_id = _task(database)
    for name, content in (("a.txt", "12345"), ("b.txt", "12")):
        source = tmp_path / name
        source.write_text(content, encoding="utf-8")
        service.attach_file(task_id, source)

    assert service.total_storage_bytes() == 7


def test_storage_warning_below_threshold(service: AttachmentService) -> None:
    assert service.storage_warning() is False


def test_storage_warning_at_threshold(service: AttachmentService, database: Database) -> None:
    # Simulate reaching the threshold without writing real files.
    with database.session() as session:
        session.add(
            Attachment(
                task_id=1,
                filename="big",
                filepath="/tmp/big",
                size_bytes=STORAGE_WARNING_BYTES,
            )
        )
        session.flush()
    assert service.storage_warning() is True
