"""Repository abstraction and SQLite implementation."""

from abc import ABC, abstractmethod
import sqlite3

from exceptions import TaskNotFoundError
from models.task import Task


class TaskRepository(ABC):
    """Define persistence operations for tasks."""

    @abstractmethod
    def create_task(self, task: Task) -> Task:
        """Create a task and return it with an assigned identifier."""

    @abstractmethod
    def get_task_by_id(self, task_id: int) -> Task:
        """Return a task by identifier or raise TaskNotFoundError."""

    @abstractmethod
    def list_tasks(
        self,
        status_filter: str = "all",
        priority_filter: str | None = None,
        search_query: str = "",
    ) -> list[Task]:
        """Return tasks matching the supplied filters."""

    @abstractmethod
    def update_task(self, task: Task) -> Task:
        """Update an existing task and return it."""

    @abstractmethod
    def delete_task(self, task_id: int) -> None:
        """Delete a task or raise TaskNotFoundError."""

    @abstractmethod
    def get_statistics(self) -> dict[str, int | float]:
        """Return aggregate task statistics."""


class SqliteTaskRepository(TaskRepository):
    """Persist tasks in a SQLite database."""

    def __init__(self, database_path: str = "task_manager.db") -> None:
        self.database_path = database_path
        self._memory_connection: sqlite3.Connection | None = None
        if database_path == ":memory:":
            self._memory_connection = sqlite3.connect(database_path)
            self._memory_connection.row_factory = sqlite3.Row
        self._initialize_database()

    def _connect(self) -> sqlite3.Connection:
        if self._memory_connection is not None:
            return self._memory_connection
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize_database(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    priority TEXT NOT NULL,
                    due_date TEXT,
                    is_completed INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                )
                """
            )

    def create_task(self, task: Task) -> Task:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO tasks (
                    title, description, priority, due_date, is_completed, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    task.title,
                    task.description,
                    task.priority,
                    task.due_date,
                    int(task.is_completed),
                    task.created_at,
                ),
            )
        task.id = cursor.lastrowid
        return task

    def get_task_by_id(self, task_id: int) -> Task:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM tasks WHERE id = ?", (task_id,)
            ).fetchone()
        if row is None:
            raise TaskNotFoundError(f"Task {task_id} was not found.")
        return self._row_to_task(row)

    def list_tasks(
        self,
        status_filter: str = "all",
        priority_filter: str | None = None,
        search_query: str = "",
    ) -> list[Task]:
        query = "SELECT * FROM tasks"
        conditions: list[str] = []
        parameters: list[str | int] = []

        if status_filter == "completed":
            conditions.append("is_completed = 1")
        elif status_filter == "pending":
            conditions.append("is_completed = 0")

        if priority_filter:
            conditions.append("priority = ?")
            parameters.append(priority_filter)

        if search_query.strip():
            conditions.append("(LOWER(title) LIKE ? OR LOWER(description) LIKE ?)")
            search_pattern = f"%{search_query.strip().lower()}%"
            parameters.extend((search_pattern, search_pattern))

        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY created_at DESC, id DESC"

        with self._connect() as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [self._row_to_task(row) for row in rows]

    def update_task(self, task: Task) -> Task:
        if task.id is None:
            raise TaskNotFoundError("Cannot update a task without an identifier.")
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE tasks
                SET title = ?, description = ?, priority = ?, due_date = ?,
                    is_completed = ?
                WHERE id = ?
                """,
                (
                    task.title,
                    task.description,
                    task.priority,
                    task.due_date,
                    int(task.is_completed),
                    task.id,
                ),
            )
        if cursor.rowcount == 0:
            raise TaskNotFoundError(f"Task {task.id} was not found.")
        return task

    def delete_task(self, task_id: int) -> None:
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM tasks WHERE id = ?", (task_id,)
            )
        if cursor.rowcount == 0:
            raise TaskNotFoundError(f"Task {task_id} was not found.")

    def get_statistics(self) -> dict[str, int | float]:
        with self._connect() as connection:
            total = connection.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
            completed = connection.execute(
                "SELECT COUNT(*) FROM tasks WHERE is_completed = 1"
            ).fetchone()[0]
        pending = total - completed
        percentage = round((completed / total * 100), 1) if total else 0.0
        return {
            "total": total,
            "completed": completed,
            "pending": pending,
            "completion_percentage": percentage,
        }

    def close(self) -> None:
        """Close the persistent in-memory connection, if present."""
        if self._memory_connection is not None:
            self._memory_connection.close()
            self._memory_connection = None

    def add_task(self, task: Task) -> Task:
        """Compatibility alias for create_task."""
        return self.create_task(task)

    def get_task(self, task_id: int) -> Task:
        """Compatibility alias for get_task_by_id."""
        return self.get_task_by_id(task_id)

    def get_all_tasks(self) -> list[Task]:
        """Return all tasks."""
        return self.list_tasks()

    @staticmethod
    def _row_to_task(row: sqlite3.Row) -> Task:
        return Task(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            priority=row["priority"],
            due_date=row["due_date"] or None,
            is_completed=bool(row["is_completed"]),
            created_at=row["created_at"],
        )
