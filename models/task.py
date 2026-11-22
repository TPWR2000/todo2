"""Task domain model."""

from dataclasses import dataclass, field
from datetime import datetime, timezone


def current_timestamp() -> str:
    """Return the current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class Task:
    """Represent a task in the application."""

    id: int | None
    title: str
    description: str
    priority: str
    due_date: str | None
    is_completed: bool
    created_at: str = field(default_factory=current_timestamp)
