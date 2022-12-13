"""Add or remove labels from Todoist tasks.

All functions have an is_dry_run parameter that defaults to False. If True, no
changes will be written to Todoist.

:author: Shay Hill
:created: 2022-12-12
"""

from typing import Optional

from todoist_api_python.api import TodoistAPI
from todoist_api_python.models import Label, Task


def _add_personal_label(
    api: TodoistAPI, name: str, is_dry_run: bool = False
) -> Optional[Label]:
    """Add a label to the Todoist personal label list if it does not already exist.

    :param api: TodoistApi instance
    :name: name for new label
    :return: Label instance
    """
    for label in api.get_labels():
        if label.name == name:
            return label
    print(f"creating new personal label '{name}'")
    if is_dry_run:
        return None
    label = api.add_label(name)  # type: ignore
    return label


def label_tasks(
    api: TodoistAPI, tasks: list[Task], label: str, is_dry_run: bool = False
):
    """Add a label to each model in the list.

    :param api: TodoistApi instance
    :param tasks: list of Task instances
    :param label: name of label to add
    """
    try:
        _ = _add_personal_label(api, label, is_dry_run)
    except Exception as e:
        print(f"Error adding label '{label}': {e}")
        return
    for task in tasks:
        if label in task.labels:
            continue
        print(f"adding label '{label}' to '{task.content}'")
        if is_dry_run:
            continue
        try:
            api.update_task(task_id=task.id, labels=task.labels + [label])  # type: ignore
        except Exception as e:
            print(f"Error adding label '{label}' to '{task.content}': {e}")


def unlabel_tasks(
    api: TodoistAPI, tasks: list[Task], label: str, is_dry_run: bool = False
):
    """Remove a label from each model in the list.

    :param api: TodoistApi instance
    :param tasks: list of Task instances
    :param label: name of label to remove
    """
    for task in tasks:
        if label not in task.labels:
            continue
        print(f"removing label '{label}' from '{task.content}'")
        if is_dry_run:
            continue
        try:
            api.update_task(  # type: ignore
                task_id=task.id, labels=[l for l in task.labels if l != label]
            )
        except Exception as e:
            print(f"Error removing label '{label}' from '{task.content}': {e}")
