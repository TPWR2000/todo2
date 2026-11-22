"""Tkinter main window for the Task Manager."""

from datetime import date
import tkinter as tk
from tkinter import ttk, messagebox

from exceptions import TaskError
from models.task import Task
from services.task_service import TaskService


class TaskDialog(tk.Toplevel):
    """Dialog for adding or editing a task."""

    def __init__(self, parent: tk.Misc, title: str, task: Task | None = None) -> None:
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.result: dict[str, str] | None = None
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        self.title_entry = ttk.Entry(self)
        self.description_entry = tk.Text(self, height=6, wrap="word")
        self.priority_combobox = ttk.Combobox(
            self, values=("low", "medium", "high"), state="readonly", width=12
        )
        self.due_date_entry = ttk.Entry(self)

        self._build_fields(task)
        self._build_buttons()
        self.transient(parent)
        self.grab_set()
        self.title_entry.focus_set()

    def _build_fields(self, task: Task | None) -> None:
        ttk.Label(self, text="Title").grid(row=0, column=0, sticky="w", padx=12, pady=(12, 2))
        self.title_entry.grid(row=1, column=0, columnspan=2, sticky="ew", padx=12)
        ttk.Label(self, text="Description").grid(
            row=2, column=0, sticky="w", padx=12, pady=(8, 2)
        )
        self.description_entry.grid(row=3, column=0, columnspan=2, sticky="ew", padx=12)
        ttk.Label(self, text="Priority").grid(
            row=4, column=0, sticky="w", padx=12, pady=(8, 2)
        )
        self.priority_combobox.grid(row=5, column=0, sticky="w", padx=12)
        ttk.Label(self, text="Due date").grid(
            row=4, column=1, sticky="w", padx=12, pady=(8, 2)
        )
        self.due_date_entry.grid(row=5, column=1, sticky="w", padx=12)

        if task:
            self.title_entry.insert(0, task.title)
            self.description_entry.insert("1.0", task.description)
            self.priority_combobox.set(task.priority)
            self.due_date_entry.insert(0, task.due_date or "")
        else:
            self.priority_combobox.set("medium")

    def _build_buttons(self) -> None:
        button_frame = ttk.Frame(self)
        button_frame.grid(row=6, column=0, columnspan=2, pady=12)
        ttk.Button(button_frame, text="Save", command=self._save).pack(side="left", padx=6)
        ttk.Button(button_frame, text="Cancel", command=self.destroy).pack(
            side="left", padx=6
        )
        self.bind("<Escape>", lambda _event: self.destroy())
        self.bind("<Control-Return>", lambda _event: self._save())
        self.title_entry.bind("<Return>", lambda _event: self._save())
        self.due_date_entry.bind("<Return>", lambda _event: self._save())

    def _save(self) -> None:
        self.result = {
            "title": self.title_entry.get(),
            "description": self.description_entry.get("1.0", "end-1c"),
            "priority": self.priority_combobox.get(),
            "due_date": self.due_date_entry.get(),
        }
        self.destroy()


class TaskManagerWindow(tk.Tk):
    """Main application window."""

    def __init__(self, task_service: TaskService) -> None:
        super().__init__()
        self.task_service = task_service
        self.title("Task Manager")
        self.geometry("860x560")

        self.status_filter = tk.StringVar(value="all")
        self.priority_filter = tk.StringVar(value="all")
        self.search_query = tk.StringVar()

        self._build_interface()
        self.refresh_tasks()

    def _build_interface(self) -> None:
        controls = ttk.Frame(self, padding=10)
        controls.pack(fill="x")
        ttk.Label(controls, text="Status").pack(side="left")
        status_combobox = ttk.Combobox(
            controls,
            textvariable=self.status_filter,
            values=("all", "pending", "completed"),
            state="readonly",
            width=12,
        )
        status_combobox.pack(side="left", padx=(4, 12))
        status_combobox.bind("<<ComboboxSelected>>", lambda _event: self.refresh_tasks())

        ttk.Label(controls, text="Priority").pack(side="left")
        priority_combobox = ttk.Combobox(
            controls,
            textvariable=self.priority_filter,
            values=("all", "low", "medium", "high"),
            state="readonly",
            width=12,
        )
        priority_combobox.pack(side="left", padx=(4, 12))
        priority_combobox.bind("<<ComboboxSelected>>", lambda _event: self.refresh_tasks())

        ttk.Label(controls, text="Search").pack(side="left")
        search_entry = ttk.Entry(controls, textvariable=self.search_query, width=24)
        search_entry.pack(side="left", padx=(4, 12))
        search_entry.bind("<KeyRelease>", lambda _event: self.refresh_tasks())
        ttk.Button(controls, text="Clear Filters", command=self.clear_filters).pack(
            side="left"
        )

        action_frame = ttk.Frame(self, padding=(10, 0, 10, 10))
        action_frame.pack(fill="x")
        ttk.Button(action_frame, text="Add Task", command=self.add_task).pack(side="left", padx=(0, 6))
        ttk.Button(action_frame, text="Edit Task", command=self.edit_task).pack(side="left", padx=6)
        ttk.Button(action_frame, text="Toggle Completion", command=self.toggle_completion).pack(
            side="left", padx=6
        )
        ttk.Button(action_frame, text="Delete Task", command=self.delete_task).pack(
            side="left", padx=6
        )
        self.statistics_label = ttk.Label(action_frame, text="")
        self.statistics_label.pack(side="right")

        table_frame = ttk.Frame(self, padding=(10, 0, 10, 10))
        table_frame.pack(fill="both", expand=True)
        columns = ("title", "description", "priority", "due_date", "status")
        self.task_tree = ttk.Treeview(
            table_frame, columns=columns, show="headings", selectmode="browse"
        )
        headings = (
            ("title", "Title", 180),
            ("description", "Description", 240),
            ("priority", "Priority", 90),
            ("due_date", "Due Date", 100),
            ("status", "Status", 100),
        )
        for column_name, heading, width in headings:
            self.task_tree.heading(column_name, text=heading)
            self.task_tree.column(column_name, width=width, anchor="w")
        self.task_tree.tag_configure("completed", foreground="#777777")
        self.task_tree.tag_configure("overdue", foreground="#b00020")
        vertical_scroll = ttk.Scrollbar(
            table_frame, orient="vertical", command=self.task_tree.yview
        )
        self.task_tree.configure(yscrollcommand=vertical_scroll.set)
        self.task_tree.pack(side="left", fill="both", expand=True)
        vertical_scroll.pack(side="right", fill="y")
        self.task_tree.bind("<Double-1>", lambda _event: self.edit_task())
        self.task_tree.bind("<Delete>", lambda _event: self.delete_task())
        self.task_tree.bind("<<TreeviewSelect>>", lambda _event: self.preview_selected_description())

        preview_frame = ttk.LabelFrame(self, text="Description", padding=(10, 6))
        preview_frame.pack(fill="x", padx=10, pady=(0, 10))
        self.description_preview = tk.Text(
            preview_frame, height=3, wrap="word", state="disabled"
        )
        self.description_preview.pack(fill="x")

    def refresh_tasks(self) -> None:
        """Reload filtered tasks and statistics."""
        try:
            for item in self.task_tree.get_children():
                self.task_tree.delete(item)
            priority_filter = self.priority_filter.get()
            if priority_filter == "all":
                priority_filter = None
            tasks = self.task_service.list_tasks(
                status_filter=self.status_filter.get(),
                priority_filter=priority_filter,
                search_query=self.search_query.get(),
            )
            for task in tasks:
                status = "Completed" if task.is_completed else "Pending"
                tags = ()
                if task.is_completed:
                    tags = ("completed",)
                elif self._is_overdue(task):
                    tags = ("overdue",)
                self.task_tree.insert(
                    "",
                    "end",
                    iid=str(task.id),
                    values=(
                        task.title,
                        task.description,
                        task.priority.capitalize(),
                        task.due_date or "",
                        status,
                    ),
                    tags=tags,
                )
            self.preview_selected_description()
            self._refresh_statistics()
        except TaskError as error:
            messagebox.showerror("Task Manager", str(error), parent=self)

    def clear_filters(self) -> None:
        """Reset status, priority, and search filters."""
        self.status_filter.set("all")
        self.priority_filter.set("all")
        self.search_query.set("")
        self.refresh_tasks()

    @staticmethod
    def _is_overdue(task: Task) -> bool:
        if task.due_date is None:
            return False
        try:
            due_date = date.fromisoformat(task.due_date)
        except ValueError:
            return False
        return due_date < date.today()

    def preview_selected_description(self) -> None:
        """Show the selected task description in the preview bar."""
        selection = self.task_tree.selection()
        description = ""
        if selection:
            try:
                task = self.task_service.get_task(int(selection[0]))
                description = task.description
            except TaskError:
                description = ""
        self.description_preview.configure(state="normal")
        self.description_preview.delete("1.0", "end")
        self.description_preview.insert("1.0", description)
        self.description_preview.configure(state="disabled")

    def _refresh_statistics(self) -> None:
        statistics = self.task_service.get_statistics()
        self.statistics_label.configure(
            text=(
                f"Total: {statistics['total']}  "
                f"Completed: {statistics['completed']}  "
                f"Pending: {statistics['pending']}  "
                f"Progress: {statistics['completion_percentage']}%"
            )
        )

    def add_task(self) -> None:
        """Open the add-task dialog."""
        dialog = TaskDialog(self, "Add Task")
        self.wait_window(dialog)
        if dialog.result is None:
            return
        try:
            self.task_service.create_task(**dialog.result)
            self.refresh_tasks()
        except TaskError as error:
            messagebox.showerror("Invalid Task", str(error), parent=self)

    def get_selected_task(self) -> Task | None:
        """Return the task selected in the table."""
        selection = self.task_tree.selection()
        if not selection:
            messagebox.showwarning(
                "No Task Selected", "Please select a task first.", parent=self
            )
            return None
        task_id = int(selection[0])
        try:
            return self.task_service.get_task(task_id)
        except TaskError as error:
            messagebox.showerror("Task Manager", str(error), parent=self)
            self.refresh_tasks()
            return None

    def edit_task(self) -> None:
        """Open the edit dialog for the selected task."""
        task = self.get_selected_task()
        if task is None:
            return
        dialog = TaskDialog(self, "Edit Task", task)
        self.wait_window(dialog)
        if dialog.result is None:
            return
        try:
            self.task_service.update_task(task.id, **dialog.result)
            self.refresh_tasks()
        except TaskError as error:
            messagebox.showerror("Invalid Task", str(error), parent=self)

    def toggle_completion(self) -> None:
        """Toggle completion for the selected task."""
        task = self.get_selected_task()
        if task is None:
            return
        try:
            self.task_service.toggle_task_completion(task.id)
            self.refresh_tasks()
        except TaskError as error:
            messagebox.showerror("Task Manager", str(error), parent=self)

    def delete_task(self) -> None:
        """Delete the selected task after confirmation."""
        task = self.get_selected_task()
        if task is None:
            return
        confirmed = messagebox.askyesno(
            "Delete Task",
            f'Delete "{task.title}"?',
            parent=self,
        )
        if not confirmed:
            return
        try:
            self.task_service.delete_task(task.id)
            self.refresh_tasks()
        except TaskError as error:
            messagebox.showerror("Task Manager", str(error), parent=self)

    def close_application(self) -> None:
        """Close the application window."""
        close_repository = getattr(self.task_service.repository, "close", None)
        if close_repository is not None:
            close_repository()
        self.destroy()
