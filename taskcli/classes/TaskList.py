from datetime import date, datetime
from .Task import Task
import textwrap
import csv
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"

DATA_DIR = Path.home() / ".taskcli"
DATA_DIR.mkdir(exist_ok=True)

FILE_PATH = DATA_DIR / "tasklist.csv"

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

def ensure_data_dir():
    DATA_DIR.mkdir(exist_ok=True)

def _supports_color() -> bool:
    if os.environ.get("NO_COLOR") is not None:
        return False
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

def _visible_len(text: str) -> int:
    return len(_ANSI_RE.sub("", text))

def _truncate_plain(text: str, width: int) -> str:
    if width <= 0:
        return ""
    cleaned = " ".join(str(text).split())
    if len(cleaned) <= width:
        return cleaned
    if width == 1:
        return cleaned[:1]
    return cleaned[: width - 1] + "…"

def _pad(text: str, width: int, align: str = "left") -> str:
    padding = width - _visible_len(text)
    if padding <= 0:
        return text
    if align == "right":
        return (" " * padding) + text
    return text + (" " * padding)

def _format_status(task: Task, use_color: bool) -> str:
    if task.completion_date_unknown:
        return "Unknown"
    if task.completion_date:
        label = "✔ Completed"
        return f"{GREEN}{label}{RESET}" if use_color else label
    label = "✗ Pending"
    return f"{RED}{label}{RESET}" if use_color else label

def _clean_required_text(value: str | None) -> tuple[str, bool]:
    if value is None:
        return "Unknown", True
    text = str(value).strip()
    if text == "" or text.lower() == "unknown":
        return "Unknown", True
    return text, False

def _parse_id(value: str | None) -> tuple[int | None, bool]:
    if value is None:
        return None, True
    text = str(value).strip()
    if text == "":
        return None, True
    try:
        return int(text), False
    except ValueError:
        return None, True

def _parse_required_date(value: str | None) -> tuple[date | None, bool]:
    if value is None:
        return None, True
    text = str(value).strip()
    if text == "" or text.lower() == "unknown":
        return None, True
    try:
        return datetime.strptime(text, "%Y-%m-%d").date(), False
    except ValueError:
        return None, True

def _parse_optional_date(value: str | None) -> tuple[date | None, bool]:
    if value is None:
        return None, False
    text = str(value).strip()
    if text == "":
        return None, False
    if text.lower() == "unknown":
        return None, True
    try:
        return datetime.strptime(text, "%Y-%m-%d").date(), False
    except ValueError:
        return None, True

class TaskList:
    tasks: list[Task]

    def __init__(self):
        self.next_id = 0
        self.tasks = []
        ensure_data_dir()
        try:
            seen_ids: set[int] = set()
            with open(FILE_PATH, newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                for row in reader:
                    if not row:
                        continue

                    # Expected format: id, description, tag, insertion_date, completion_date
                    # If a description contains unquoted commas, csv.reader may split it.
                    # Use: id = first, completion = last, insertion = second last,
                    # tag = third last, description = join of remaining middle.
                    if len(row) >= 5:
                        id_str = row[0]
                        completion_str = row[-1]
                        insertion_str = row[-2]
                        tag_str = row[-3]
                        description_str = ",".join(row[1:-3])
                    else:
                        padded = row + [""] * (5 - len(row))
                        id_str, description_str, tag_str, insertion_str, completion_str = padded

                    parsed_id, _id_corrupt = _parse_id(id_str)
                    description, _desc_corrupt = _clean_required_text(description_str)
                    tag, _tag_corrupt = _clean_required_text(tag_str)
                    insertion_date, insertion_unknown = _parse_required_date(insertion_str)
                    completion_date, completion_unknown = _parse_optional_date(completion_str)

                    # ID must stay an int for CLI operations; remap missing/corrupt/duplicate IDs.
                    if parsed_id is None or parsed_id in seen_ids:
                        parsed_id = self.next_id

                    seen_ids.add(parsed_id)
                    self.next_id = max(self.next_id, parsed_id + 1)

                    task = Task(
                        id=parsed_id,
                        description=description,
                        tag=tag,
                        insertion_date=insertion_date,
                        completion_date=completion_date,
                        insertion_date_unknown=insertion_unknown,
                        completion_date_unknown=completion_unknown,
                    )
                    self.tasks.append(task)
        except FileNotFoundError:
            pass

    def save_tasks(self):
        temp_path: str | None = None
        try:
            fd, temp_path = tempfile.mkstemp(
                prefix=f"{FILE_PATH.name}.",
                suffix=".tmp",
                dir=DATA_DIR,
                text=True,
            )
            with os.fdopen(fd, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                for task in self.tasks:
                    insertion_str = (
                        task.insertion_date.isoformat()
                        if task.insertion_date and not task.insertion_date_unknown
                        else "Unknown"
                    )
                    if task.completion_date_unknown:
                        completion_str = "Unknown"
                    else:
                        completion_str = task.completion_date.isoformat() if task.completion_date else ""
                    writer.writerow([
                        task.id,
                        task.description,
                        task.tag,
                        insertion_str,
                        completion_str,
                    ])
                f.flush()
                os.fsync(f.fileno())

            try:
                os.chmod(temp_path, FILE_PATH.stat().st_mode & 0o777)
            except FileNotFoundError:
                pass

            os.replace(temp_path, FILE_PATH)

            try:
                dir_fd = os.open(DATA_DIR, getattr(os, "O_DIRECTORY", 0))
            except OSError:
                dir_fd = None

            if dir_fd is not None:
                try:
                    os.fsync(dir_fd)
                finally:
                    os.close(dir_fd)
        finally:
            if temp_path is not None:
                try:
                    os.unlink(temp_path)
                except FileNotFoundError:
                    pass

    def get_task_by_id(self, task_id: int) -> Task | None:
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None

    def add_task(self, description: str, tag: str) -> bool:
        task = Task(self.next_id, description, tag)
        self.tasks.append(task)
        self.next_id += 1
        return True
    
    def delete_task(self, task_id: int) -> bool:
        task = self.get_task_by_id(task_id)
        if not task:
            print(f"Task {task_id} does not exist")
            return False
        print(f"Task {task.id}: \"{task.description}\" selected for deletion.")
        confirmation = input(f"Enter 'DELETE' to confirm: ")
        if confirmation == "DELETE":
            self.tasks.remove(task)
        else:
            print(f"OK, not deleting task {task.id}")
            return False
        return True
    
    def complete_task(self, task_id: int) -> bool:
        task = self.get_task_by_id(task_id)
        if not task:
            print(f"Task {task_id} does not exist")
            return False
        task.complete_task()
        return True

    def display_tasks(self, pending=False, completed=False, tag=None):
        if not self.tasks:
            print("No tasks yet. Add one with: taskcli add <description> [-t TAG]")
            return
        
        tasks = self.tasks

        if pending and not completed:
            tasks = [t for t in tasks if t.completion_date is None]
        elif completed and not pending:
            tasks = [t for t in tasks if t.completion_date is not None]
        
        if tag:
            tasks = [t for t in tasks if t.tag.lower() == tag.lower()]
        if not tasks:
            filters = []
            if tag:
                filters.append(f"tag={tag}")
            if pending and not completed:
                filters.append("status=pending")
            elif completed and not pending:
                filters.append("status=completed")
            suffix = f" ({', '.join(filters)})" if filters else ""
            print(f"No tasks found{suffix}.")
            return

        tasks = sorted(tasks, key=lambda t: t.id)
        use_color = _supports_color()
        term_width = shutil.get_terminal_size(fallback=(100, 20)).columns

        id_width = max(len("ID"), max(len(str(t.id)) for t in tasks))
        created_width = max(len("Created"), 10)
        status_width = max(len("Status"), max(_visible_len(_format_status(t, use_color=False)) for t in tasks))
        tag_width = max(len("Tag"), min(20, max(len(str(t.tag)) for t in tasks)))

        fixed = (
            id_width
            + tag_width
            + created_width
            + status_width
        )
        table_overhead = (3 * 5) + 1  # sum(widths) + 3*cols + 1
        min_desc_width = 20
        remaining = term_width - (fixed + table_overhead)
        desc_width = max(len("Description"), min(60, max(min_desc_width, remaining)))

        # If we're still too wide, shrink description first, then tag.
        total_width = fixed + desc_width + table_overhead
        if total_width > term_width:
            overflow = total_width - term_width
            shrink = min(overflow, max(0, desc_width - min_desc_width))
            desc_width -= shrink
            overflow -= shrink

            min_tag_width = 8
            if overflow > 0:
                shrink = min(overflow, max(0, tag_width - min_tag_width))
                tag_width -= shrink

        def hr(char: str = "-") -> str:
            return (
                "+"
                + "+".join([
                    char * (id_width + 2),
                    char * (desc_width + 2),
                    char * (tag_width + 2),
                    char * (created_width + 2),
                    char * (status_width + 2),
                ])
                + "+"
            )

        def row(cells: list[tuple[str, int, str]]) -> str:
            rendered = []
            for text, width, align in cells:
                rendered.append(" " + _pad(text, width, align=align) + " ")
            return "|" + "|".join(rendered) + "|"

        shown_pending = sum(1 for t in tasks if t.completion_date is None)
        shown_completed = len(tasks) - shown_pending
        print(f"Tasks: {len(tasks)} shown (pending: {shown_pending}, completed: {shown_completed})")

        print(hr("-"))
        print(row([
            ("ID", id_width, "right"),
            ("Description", desc_width, "left"),
            ("Tag", tag_width, "left"),
            ("Created", created_width, "left"),
            ("Status", status_width, "left"),
        ]))
        print(hr("="))

        for task in tasks:
            created = task.insertion_date.strftime("%Y-%m-%d") if task.insertion_date else "Unknown"
            status = _format_status(task, use_color=use_color)

            print(row([
                (str(task.id), id_width, "right"),
                (_truncate_plain(task.description, desc_width), desc_width, "left"),
                (_truncate_plain(task.tag, tag_width), tag_width, "left"),
                (created, created_width, "left"),
                (status, status_width, "left"),
            ]))

        print(hr("-"))

    def display_single_task(self, task_id: int):
        task = self.get_task_by_id(task_id)
        if not task:
            print(f"Task {task_id} does not exist")
            return

        use_color = _supports_color()
        term_width = shutil.get_terminal_size(fallback=(100, 20)).columns

        created = task.insertion_date.strftime("%Y-%m-%d") if task.insertion_date else "Unknown"
        if task.completion_date_unknown:
            completed = "Unknown"
        elif task.completion_date:
            completed = task.completion_date.strftime("%Y-%m-%d")
        else:
            completed = "-"

        status = _format_status(task, use_color=use_color)

        title = f"Task Details (ID: {task.id})"
        labels = ["Description", "Tag", "Created", "Completed", "Status"]
        label_width = max(len(f"{l}:") for l in labels)

        # Box width: fits terminal, but never too narrow to be readable.
        min_box_width = 60
        max_box_width = 100
        width = max(min_box_width, min(max_box_width, term_width))
        content_width = width - (2 + 1 + label_width + 2)  # | <label>: <content> |
        content_width = max(20, content_width)

        def hr(char: str = "-") -> str:
            return "+" + (char * (width - 2)) + "+"

        def title_line(text: str) -> str:
            inner = width - 2
            centered = text[:inner].center(inner)
            return "|" + centered + "|"

        def kv_lines(label: str, value: str) -> list[str]:
            wrapped = textwrap.wrap(str(value), width=content_width) or [""]
            lines = []
            for i, line in enumerate(wrapped):
                left = f"{label}:" if i == 0 else ""
                left = _pad(left, label_width, align="left")
                right = _pad(line, content_width, align="left")
                lines.append(f"| {left} {right} |")
            return lines

        print(hr("="))
        print(title_line(title))
        print(hr("="))
        for line in kv_lines("Description", " ".join(str(task.description).split())):
            print(line)
        for line in kv_lines("Tag", task.tag):
            print(line)
        for line in kv_lines("Created", created):
            print(line)
        for line in kv_lines("Completed", completed):
            print(line)
        for line in kv_lines("Status", status):
            print(line)
        print(hr("="))
