"""Loop to check for and address updates.

:author: Shay Hill
:created: 2022-12-12
"""

import argparse
import time
from typing import Callable, TypeAlias

from paragraphs import par
from todoist_tree.headers import new_headers
from todoist_tree.read_changes import Project, Section, Task, read_changes
from todoist_tree.task_subsets import select_all, select_parallel, select_serial
from todoist_tree.tree import AnyNode, map_id_to_branch
from todoist_tree.write_changes import (
    queue_add_label,
    queue_new_label,
    queue_remove_label,
    write_changes,
)

Command = dict[str, str | dict[str, str | int | list[str]]]

# type alias for select_serial and select_parallel
Selecter: TypeAlias = Callable[
    [list[Project], list[Section], list[Task], dict[str, AnyNode], str],
    tuple[list[Task], list[Task]],
]


def _get_parser() -> argparse.ArgumentParser:
    """Return an argument parser for this script.

    :return: an argument parser for `python main.py ...`
    """
    parser = argparse.ArgumentParser(
        description="Automations for Todoist",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    _ = parser.add_argument(
        "-a", "--api_key", help="REQUIRED: your Todoist API Key.", type=str
    )
    _ = parser.add_argument(
        "-s",
        "--serial",
        nargs="*",
        help=par(
            """format "label suffix". Add [label] to the next (sub)task beneath or at
            any item with a name ending in [suffix]. Example: "next_action -n" will
            add the label `@next_action` to the next task beneath or at any project,
            section, or task with a name ending in -n."""
        ),
        type=str,
    )
    _ = parser.add_argument(
        "-p",
        "--parallel",
        nargs="*",
        help=par(
            """format "label suffix". Add [label] to all childless (sub)tasks beneath
            or at any item with a name ending in [suffix]. Example: "actionable -a"
            will add the label `@actionable` to all childless (sub)tasks beneath or
            at any project, section, or task with a name ending in -a."""
        ),
        type=str,
    )
    _ = parser.add_argument(
        "-l",
        "--all",
        nargs="*",
        help=par(
            """format "label suffix". Add [label] to all (sub)tasks beneath or at any
            item with a name ending in [suffix]. Example: "parked -p" will add the
            label `@parked` to all (sub)tasks beneath or at any project, section, or
            task with a name ending in -p."""
        ),
        type=str,
    )
    _ = parser.add_argument(
        "-d",
        "--delay",
        help="Specify the delay in seconds between syncs (default 5).",
        default=5,
        type=int,
    )
    _ = parser.add_argument(
        "-n",
        "--dry-run",
        help="Do not update Todoist. Describe changes and exit.",
        action="store_true",
    )
    _ = parser.add_argument(
        "-o",
        "--once",
        help="Update Todoist once then stop watching for changes.",
        action="store_true",
    )
    return parser


def _sleep(start_time: float, delay: int) -> None:
    """Sleep for `delay` seconds."""
    end_time = time.time()
    delta_time = end_time - start_time
    sleep_time = delay - delta_time
    if sleep_time >= 0:
        print(f"\nsleeping for {sleep_time}. Waiting for changes...")
        time.sleep(sleep_time)
    else:
        print(f"operation took longer than delay time: {delta_time}")


def main():
    """Main function."""
    parser = _get_parser()
    args = parser.parse_args()

    if not args.api_key or not any([args.serial, args.parallel, args.all]):
        parser.print_help()
        return

    headers = new_headers(args.api_key)
    todoist = None
    sync_token: str = "*"

    while True:
        start_time = time.time()

        todoist = read_changes(headers, sync_token)
        if todoist is None:
            _sleep(start_time, args.delay)
            continue

        sync_token = todoist.sync_token
        todoist_label_names = [x.name for x in todoist.labels]
        projects = todoist.projects
        sections = todoist.sections
        tasks = todoist.tasks

        id2node = map_id_to_branch(projects, sections, tasks)

        commands: list[Command] = []

        def _mark_selection(input_arg: str, fselect: Selecter) -> None:
            """Mark selection of tasks with given label."""
            arg_words = input_arg.split()
            label, suffix = "_".join(arg_words[:-1]), arg_words[-1]
            to_label, to_clear = fselect(projects, sections, tasks, id2node, suffix)

            to_label = [t for t in to_label if label not in t.labels]
            if to_label and label not in todoist_label_names:
                queue_new_label(commands, label)

            for task in to_label:
                queue_add_label(commands, task, label)
            for task in (t for t in to_clear if label in t.labels):
                queue_remove_label(commands, task, label)

        for arg in args.serial or ():
            _mark_selection(arg, select_serial)

        for arg in args.parallel or ():
            _mark_selection(arg, select_parallel)

        for arg in args.all or ():
            _mark_selection(arg, select_all)

        if args.dry_run:
            break

        sync_token = write_changes(sync_token, headers, commands)

        if args.once:
            break

        _sleep(start_time, args.delay)


if __name__ == "__main__":
    main()
