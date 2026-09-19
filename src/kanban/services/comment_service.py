"""Comment service (F-14).

Manages the discussion thread on a task: add, list, and delete comments, plus
a helper to extract ``@mentions`` from comment text for context.

Pure business logic with no GUI dependencies.
"""

from __future__ import annotations

import re

from kanban.models import Comment, Task
from kanban.services.database import Database

_MENTION_RE = re.compile(r"@([A-Za-z0-9_]+)")


class CommentService:
    """Add, list, and delete comments on a task; extract @mentions."""

    def __init__(self, database: Database) -> None:
        self._db = database

    def add_comment(self, task_id: int, content: str, user_name: str = "") -> Comment:
        """Append a comment to a task's thread.

        Raises ``ValueError`` if the content is blank.
        """
        text = content.strip()
        if not text:
            raise ValueError("Comment content must not be blank")
        with self._db.session() as session:
            if session.get(Task, task_id) is None:
                raise LookupError(f"Task {task_id} does not exist")
            comment = Comment(task_id=task_id, content=text, user_name=user_name)
            session.add(comment)
            session.flush()
            return comment

    def list_comments(self, task_id: int) -> list[Comment]:
        """Return a task's comments in chronological order."""
        with self._db.session() as session:
            task = session.get(Task, task_id)
            if task is None:
                raise LookupError(f"Task {task_id} does not exist")
            return list(task.comments)

    def delete_comment(self, comment_id: int) -> None:
        """Delete a comment by id."""
        with self._db.session() as session:
            comment = session.get(Comment, comment_id)
            if comment is None:
                raise LookupError(f"Comment {comment_id} does not exist")
            session.delete(comment)
            session.flush()

    @staticmethod
    def find_mentions(content: str) -> list[str]:
        """Return the unique @mentioned usernames in order of appearance."""
        seen: dict[str, None] = {}
        for match in _MENTION_RE.finditer(content):
            seen.setdefault(match.group(1), None)
        return list(seen)
