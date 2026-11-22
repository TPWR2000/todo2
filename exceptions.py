"""Custom exceptions for Task Manager domain errors."""


class TaskError(Exception):
    """Base exception for task-related errors."""


class TaskValidationError(TaskError):
    """Raised when task input violates domain rules."""


class TaskNotFoundError(TaskError):
    """Raised when a task cannot be found."""
