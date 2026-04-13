import sys
import argparse
from taskcli import TaskList

def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "TaskCLI is a small command-line task manager.\n"
            "\n"
            "It stores your tasks locally and lets you add, list, inspect, complete,\n"
            "and delete tasks from the terminal."
        ),
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=(
            "What each command does:\n"
            "  add      Create a new task (description + optional tag)\n"
            "  view     List tasks; filter by pending/completed and/or tag\n"
            "  viewone  Show details for a single task by ID\n"
            "  complete Mark a task as completed\n"
            "  pending Mark a task as pending\n"
            "  delete   Delete a task (asks for confirmation)\n"
            "\n"
            "Data:\n"
            "  Tasks are stored at: ~/.taskcli/tasklist.csv\n"
            "\n"
            "Examples:\n"
            "  taskcli add buy milk and bread -t Home\n"
            "  taskcli view\n"
            "  taskcli view --pending\n"
            "  taskcli viewone 2\n"
            "  taskcli complete 2\n"
            "  taskcli pending 2\n"
            "  taskcli delete 2\n"
        ),
    )

    subparsers = parser.add_subparsers(dest="command", title="Commands", metavar="COMMAND")

    # add
    add_parser = subparsers.add_parser(
        "add",
        help="Add a new task",
        description=(
            "Create a new task.\n"
            "\n"
            "The description can be multiple words (quotes are optional). "
            "If you don't pass a tag, it defaults to 'General'."
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    add_parser.add_argument(
        "description",
        nargs="+",
        help="Task description (no quotes needed)"
    )
    add_parser.add_argument(
        "-t", "--tag",
        default="General",
        help="Optional category/tag"
    )

    # view
    view_parser = subparsers.add_parser(
        "view",
        help="Display all tasks",
        description=(
            "List tasks.\n"
            "\n"
            "By default it shows all tasks. You can filter by status (pending/completed)\n"
            "and/or by tag."
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    view_parser.add_argument(
        "--pending",
        action="store_true",
        help="Show only pending tasks"
    )
    view_parser.add_argument(
        "--completed",
        action="store_true",
        help="Show only completed tasks"
    )
    view_parser.add_argument(
        "--tag",
        help="Filter by tag"
    )

    # viewone
    viewone_parser = subparsers.add_parser(
        "viewone",
        help="Display details of a task",
        description="Show details for a single task by its numeric ID.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    viewone_parser.add_argument(
        "id",
        type=int,
        help="Task ID"
    )

    # delete
    delete_parser = subparsers.add_parser(
        "delete",
        help="Delete a task",
        description=(
            "Delete a task by its numeric ID.\n"
            "\n"
            "This action asks for confirmation; you must type DELETE to proceed."
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    delete_parser.add_argument(
        "id",
        type=int,
        help="Task ID"
    )

    # complete
    complete_parser = subparsers.add_parser(
        "complete",
        help="Mark a task as completed",
        description="Mark a task as completed by its numeric ID.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    complete_parser.add_argument(
        "id",
        type=int,
        help="Task ID"
    )

    # mark task as pending
    pending_parser = subparsers.add_parser(
        "pending",
        help="Mark a task as pending",
        description="Mark a task as pending by its numeric ID.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    pending_parser.add_argument(
        "id",
        type=int,
        help="Task ID"
    )

    return parser

def execute_command(user_input):
    task_list = TaskList()

    if (user_input.command == "view"):
        task_list.display_tasks(
            pending=user_input.pending,
            completed=user_input.completed,
            tag=user_input.tag
        )

    elif (user_input.command == "add"):
        task_str = " ".join(user_input.description).strip()
        if task_str == "":
            print("Description needed")
            return
        if (task_list.add_task(task_str, user_input.tag.strip())):
            task_list.save_tasks()
            print(f"Task added: {task_str}")

    elif (user_input.command == "viewone"):
        task_list.display_single_task(user_input.id)

    elif (user_input.command == "delete"):
        if(task_list.delete_task(user_input.id)):
            task_list.save_tasks()
            print(f"Task {user_input.id} deleted")

    elif (user_input.command == "complete"):
        if (task_list.complete_task(user_input.id)):
            task_list.save_tasks()
            print(f"Task {user_input.id} marked as completed")

    elif (user_input.command == "pending"):
        if (task_list.uncomplete_task(user_input.id)):
            task_list.save_tasks()
            print(f"Task {user_input.id} marked as pending")


def task_manager():
    parser = build_parser()

    if (len(sys.argv) == 1):
        parser.print_help()
        return
    
    args = parser.parse_args()

    execute_command(args)

if __name__ == "__main__":
    task_manager()
