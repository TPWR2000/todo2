"""Application entry point for the Task Manager."""

from repositories.task_repository import SqliteTaskRepository
from services.task_service import TaskService
from ui.main_window import TaskManagerWindow


def main() -> None:
    """Configure the application and start the Tkinter event loop."""
    repository = SqliteTaskRepository("task_manager.db")
    service = TaskService(repository)
    window = TaskManagerWindow(service)
    window.protocol("WM_DELETE_WINDOW", window.close_application)
    window.mainloop()


if __name__ == "__main__":
    main()
