"""File-attachment service (F-13, F-31, F-32).

Copies files into the app's on-disk attachment store and records their
metadata against a task. Enforces the 10MB per-file limit (F-31) and exposes
a storage warning once total attachment size reaches the 475MB threshold
(F-32).

Pure business logic with no GUI dependencies.
"""

from __future__ import annotations

import mimetypes
import shutil
import uuid
from pathlib import Path

from sqlalchemy import select

from kanban.models import Attachment, Task
from kanban.services.database import Database

#: Maximum size of a single attachment (F-31): 10 MB.
MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024

#: Storage warning threshold (F-32): 475 MB.
STORAGE_WARNING_BYTES = 475 * 1024 * 1024


def default_storage_dir() -> Path:
    """Return the default on-disk location for attachment files."""
    return Path.home() / ".kanban" / "attachments"


class AttachmentService:
    """Attach, list, and delete files; report storage usage."""

    def __init__(self, database: Database, storage_dir: str | Path | None = None) -> None:
        self._db = database
        self._storage_dir = Path(storage_dir) if storage_dir is not None else default_storage_dir()

    # -- Attachments ------------------------------------------------------
    def attach_file(self, task_id: int, source_path: str | Path) -> Attachment:
        """Copy ``source_path`` into the store and attach it to a task.

        Raises ``FileNotFoundError`` if the source is missing and
        ``ValueError`` if it exceeds the per-file size limit.
        """
        source = Path(source_path)
        if not source.is_file():
            raise FileNotFoundError(f"Attachment source not found: {source}")
        size = source.stat().st_size
        if size > MAX_ATTACHMENT_BYTES:
            raise ValueError(
                f"Attachment is {size} bytes, exceeding the {MAX_ATTACHMENT_BYTES} byte limit"
            )
        with self._db.session() as session:
            if session.get(Task, task_id) is None:
                raise LookupError(f"Task {task_id} does not exist")
            self._storage_dir.mkdir(parents=True, exist_ok=True)
            dest = self._storage_dir / f"{uuid.uuid4().hex}_{source.name}"
            shutil.copy2(source, dest)
            attachment = Attachment(
                task_id=task_id,
                filename=source.name,
                filepath=str(dest),
                mime_type=mimetypes.guess_type(source.name)[0],
                size_bytes=size,
            )
            session.add(attachment)
            session.flush()
            return attachment

    def list_attachments(self, task_id: int) -> list[Attachment]:
        """Return a task's attachments ordered by id."""
        with self._db.session() as session:
            task = session.get(Task, task_id)
            if task is None:
                raise LookupError(f"Task {task_id} does not exist")
            return list(task.attachments)

    def delete_attachment(self, attachment_id: int) -> None:
        """Delete an attachment record and its stored file."""
        with self._db.session() as session:
            attachment = session.get(Attachment, attachment_id)
            if attachment is None:
                raise LookupError(f"Attachment {attachment_id} does not exist")
            filepath = attachment.filepath
            session.delete(attachment)
            session.flush()
        stored = Path(filepath)
        if stored.is_file():
            stored.unlink()

    # -- Storage reporting ------------------------------------------------
    def total_storage_bytes(self) -> int:
        """Total bytes used by all stored attachments."""
        with self._db.session() as session:
            rows = session.execute(select(Attachment.size_bytes)).scalars().all()
            return sum(rows)

    def storage_warning(self) -> bool:
        """Whether total attachment storage has reached the warning threshold."""
        return self.total_storage_bytes() >= STORAGE_WARNING_BYTES
