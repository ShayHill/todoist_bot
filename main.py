"""Loop to check for and address updates.

:author: Shay Hill
:created: 2022-12-12
"""

import argparse
import time
from typing import Callable, TypeAlias

from paragraphs import par as paragraphs_par  # type: ignore
from todoist_api_python.api import TodoistAPI
from todoist_api_python.models import Project, Section, Task

from todoist_bot.task_subsets import select_parallel, select_serial
from todoist_bot.tree import AnyNode, map_id_to_branch
from todoist_bot.write_changes import label_tasks, unlabel_tasks


def par(long_string: str) -> str:
    """I need to add types to my old paragraphs library"""
    return paragraphs_par(long_string)  # type: ignore


# type alias for select_serial and select_parallel
Selecter: TypeAlias = Callable[
    [list[Project], list[Section], list[Task], dict[str, AnyNode], str],
    tuple[list[Task], list[Task]],
]


def _get_parser() -> argparse.ArgumentParser:
    """Return an argument parser for this script."""
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
            any item with a name ending in [suffix]. Example: "next_action --" will
            add the label `next_action` to the next task beneath or at any project,
            section, or task with a name ending in --."""
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
            will add the label `actionable` to all childless (sub)tasks beneath or at
            any project, section, or task with a name ending in -a."""
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
        print(f"sleeping for {sleep_time}. Waiting for changes...")
        time.sleep(sleep_time)
    else:
        print(f"operation took longer than delay time: {delta_time}")


def main():
    parser = _get_parser()
    args = parser.parse_args()

    if not args.api_key or (not args.serial and not args.parallel):
        parser.print_help()
        return

    api = TodoistAPI(args.api_key)

    while True:
        start_time = time.time()

        # cache some of the api calls
        try:
            projects = api.get_projects()
        except Exception as e:
            print(f"errer getting Todoist Projects: {e}")
            _sleep(start_time, args.delay)
            continue

        try:
            sections = api.get_sections()  # type: ignore
        except Exception as e:
            print(f"errer getting Todoist Sections: {e}")
            _sleep(start_time, args.delay)
            continue

        try:
            tasks = api.get_tasks()  # type: ignore
        except Exception as e:
            print(f"errer getting Todoist Tasks: {e}")
            _sleep(start_time, args.delay)
            continue

        id2node = map_id_to_branch(projects, sections, tasks)

        def _mark_selection(input_arg: str, fselect: Selecter) -> None:
            """Mark selection of tasks with given label."""
            arg_words = input_arg.split()
            label, suffix = "_".join(arg_words[:-1]), arg_words[-1]
            to_label, to_clear = fselect(projects, sections, tasks, id2node, suffix)
            if to_label:
                label_tasks(api, to_label, label, args.dry_run)
            unlabel_tasks(api, to_clear, label, args.dry_run)

        for arg in args.serial or ():
            _mark_selection(arg, select_serial)

        for arg in args.parallel or ():
            _mark_selection(arg, select_parallel)

        if args.dry_run or args.once:
            break

        _sleep(start_time, args.delay)


if __name__ == "__main__":
    main()
