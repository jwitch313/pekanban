"""Time-tracking service (F-12).

A single global timer: at most one task has a running (open) time entry at a
time. Starting a timer on a task closes any currently running one. Pausing and
stopping both close the running interval; pausing flags it so it can be
resumed. Reports aggregate the closed intervals per task and per column.

Pure business logic with no GUI dependencies.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from kanban.models import BoardColumn, Task, TimeEntry
from kanban.services.database import Database


class TimeTrackingService:
    """Start/stop/pause per-task timers and report time spent."""

    def __init__(self, database: Database) -> None:
        self._db = database

    # -- Timer control ----------------------------------------------------
    def start_timer(self, task_id: int, now: datetime | None = None) -> TimeEntry:
        """Start a timer on a task, closing any currently running timer."""
        now = now or datetime.now()
        with self._db.session() as session:
            if session.get(Task, task_id) is None:
                raise LookupError(f"Task {task_id} does not exist")
            self._close_running(session, now)
            entry = TimeEntry(task_id=task_id, started_at=now, ended_at=None, paused=False)
            session.add(entry)
            session.flush()
            return entry

    def pause_timer(self, task_id: int, now: datetime | None = None) -> TimeEntry:
        """Pause a task's running timer, closing the interval as paused."""
        now = now or datetime.now()
        with self._db.session() as session:
            entry = self._running_for(session, task_id)
            if entry is None:
                raise LookupError(f"No running timer for task {task_id}")
            entry.ended_at = now
            entry.paused = True
            session.flush()
            return entry

    def resume_timer(self, task_id: int, now: datetime | None = None) -> TimeEntry:
        """Resume a task's timer by opening a fresh interval."""
        now = now or datetime.now()
        with self._db.session() as session:
            if session.get(Task, task_id) is None:
                raise LookupError(f"Task {task_id} does not exist")
            self._close_running(session, now)
            entry = TimeEntry(task_id=task_id, started_at=now, ended_at=None, paused=False)
            session.add(entry)
            session.flush()
            return entry

    def stop_timer(self, task_id: int, now: datetime | None = None) -> TimeEntry:
        """Stop a task's running timer, closing the interval."""
        now = now or datetime.now()
        with self._db.session() as session:
            entry = self._running_for(session, task_id)
            if entry is None:
                raise LookupError(f"No running timer for task {task_id}")
            entry.ended_at = now
            entry.paused = False
            session.flush()
            return entry

    def active_timer(self) -> TimeEntry | None:
        """Return the currently running time entry, if any."""
        with self._db.session() as session:
            return (
                session.execute(select(TimeEntry).where(TimeEntry.ended_at.is_(None)))
                .scalars()
                .first()
            )

    # -- Reports ----------------------------------------------------------
    def total_for_task(self, task_id: int) -> float:
        """Total tracked seconds for a task (closed intervals only)."""
        with self._db.session() as session:
            task = session.get(Task, task_id)
            if task is None:
                raise LookupError(f"Task {task_id} does not exist")
            entries = list(task.time_entries)
            return sum(e.duration_seconds for e in entries if e.ended_at is not None)

    def total_for_column(self, column_id: int) -> float:
        """Total tracked seconds across all tasks in a column."""
        with self._db.session() as session:
            column = session.get(BoardColumn, column_id)
            if column is None:
                raise LookupError(f"Column {column_id} does not exist")
            total = 0.0
            for task in column.tasks:
                for entry in task.time_entries:
                    if entry.ended_at is not None:
                        total += entry.duration_seconds
            return total

    # -- Helpers ----------------------------------------------------------
    @staticmethod
    def _running_for(session: Session, task_id: int) -> TimeEntry | None:
        return (
            session.execute(
                select(TimeEntry).where(
                    TimeEntry.task_id == task_id,
                    TimeEntry.ended_at.is_(None),
                )
            )
            .scalars()
            .first()
        )

    @staticmethod
    def _close_running(session: Session, now: datetime) -> None:
        running = (
            session.execute(select(TimeEntry).where(TimeEntry.ended_at.is_(None)))
            .scalars()
            .all()
        )
        for entry in running:
            entry.ended_at = now
            entry.paused = False
