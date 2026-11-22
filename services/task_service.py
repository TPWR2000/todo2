"""Task business logic."""

from datetime import datetime

from exceptions import TaskValidationError, TaskNotFoundError
from models.task import Task, current_timestamp
from repositories.task_repository import TaskRepository


class TaskService:
    """Apply validation and task rules independently of UI and storage."""

    VALID_PRIORITIES = ("low", "medium", "high")
    VALID_STATUSES = ("all", "pending", "completed")

    def __init__(self, repository: TaskRepository) -> None:
        self.repository = repository

    def create_task(
        self,
        title: str,
        description: str = "",
        priority: str = "medium",
        due_date: str | None = None,
    ) -> Task:
        """Validate input and create a new task."""
        self._validate_title(title)
        self._validate_priority(priority)
        normalized_due_date = self._validate_due_date(due_date)
        task = Task(
            id=None,
            title=title.strip(),
            description=description.strip(),
            priority=priority.lower(),
            due_date=normalized_due_date,
            is_completed=False,
            created_at=current_timestamp(),
        )
        return self.repository.create_task(task)

    def list_tasks(
        self,
        status_filter: str = "all",
        priority_filter: str | None = None,
        search_query: str = "",
    ) -> list[Task]:
        """Return tasks matching validated filters."""
        if status_filter not in self.VALID_STATUSES:
            raise TaskValidationError("Status filter must be all, pending, or completed.")
        if priority_filter:
            self._validate_priority(priority_filter)
        return self.repository.list_tasks(status_filter, priority_filter, search_query)

    def update_task(
        self,
        task_id: int,
        title: str | None = None,
        description: str | None = None,
        priority: str | None = None,
        due_date: str | None = None,
    ) -> Task:
        """Update supplied fields of an existing task."""
        task = self.repository.get_task_by_id(task_id)
        updated_title = task.title if title is None else title
        updated_description = task.description if description is None else description
        updated_priority = task.priority if priority is None else priority
        updated_due_date = task.due_date if due_date is None else due_date

        self._validate_title(updated_title)
        self._validate_priority(updated_priority)
        normalized_due_date = self._validate_due_date(updated_due_date)
        task.title = updated_title.strip()
        task.description = updated_description.strip()
        task.priority = updated_priority.lower()
        task.due_date = normalized_due_date
        return self.repository.update_task(task)

    def toggle_task_completion(self, task_id: int) -> Task:
        """Invert the completion state of a task."""
        task = self.repository.get_task_by_id(task_id)
        task.is_completed = not task.is_completed
        return self.repository.update_task(task)

    def delete_task(self, task_id: int) -> None:
        """Delete an existing task."""
        if not isinstance(task_id, int) or isinstance(task_id, bool):
            raise TaskValidationError("Task identifier must be an integer.")
        self.repository.get_task_by_id(task_id)
        self.repository.delete_task(task_id)

    def get_statistics(self) -> dict[str, int | float]:
        """Return total, completed, pending, and completion percentage counts."""
        if hasattr(self.repository, "get_statistics"):
            return self.repository.get_statistics()
        tasks = self.repository.list_tasks()
        total = len(tasks)
        completed = sum(1 for task in tasks if task.is_completed)
        pending = total - completed
        percentage = round((completed / total * 100), 1) if total else 0.0
        return {
            "total": total,
            "completed": completed,
            "pending": pending,
            "completion_percentage": percentage,
        }

    def get_task(self, task_id: int) -> Task:
        """Return a task by identifier."""
        try:
            return self.repository.get_task_by_id(task_id)
        except TaskNotFoundError:
            raise

    @classmethod
    def _validate_title(cls, title: str) -> None:
        if not isinstance(title, str) or not title.strip():
            raise TaskValidationError("Title cannot be empty.")

    @classmethod
    def _validate_priority(cls, priority: str) -> None:
        if not isinstance(priority, str) or priority.lower() not in cls.VALID_PRIORITIES:
            raise TaskValidationError("Priority must be low, medium, or high.")

    @staticmethod
    def _validate_due_date(due_date: str | None) -> str | None:
        if due_date is None or due_date.strip() == "":
            return None
        try:
            parsed_date = datetime.strptime(due_date.strip(), "%Y-%m-%d")
        except ValueError as error:
            raise TaskValidationError(
                "Due date must use ISO format YYYY-MM-DD."
            ) from error
        if parsed_date.strftime("%Y-%m-%d") != due_date.strip():
            raise TaskValidationError("Due date must use ISO format YYYY-MM-DD.")
        return due_date.strip()
