"""Add or remove labels from Todoist tasks.

All functions have an is_dry_run parameter that defaults to False. If True, no
changes will be written to Todoist.

:author: Shay Hill
:created: 2022-12-12
"""

import json
import uuid
from typing import cast

import requests
from requests.structures import CaseInsensitiveDict
from todoist_api_python.models import Task as apip_task

from todoist_bot.headers import SYNC_URL
from todoist_bot.read_changes import Task

# This should cover everything in Todoist response.json()
JsonDictValue = str | int | bool | None | list["JsonDict"] | dict[str, "JsonDict"]
JsonDict = dict[str, JsonDictValue]

# A more constrained dict type for command responses
ItemResponse = dict[str, str | dict[str, str | int | list[str]]]

Command = dict[str, str | dict[str, str | int | list[str]]]


def label_tasks(calls: list[Command], tasks: list[apip_task], label: str):
    """Add a label to each model in the list.

    :param calls: a list of commands to which new commands will be appended
    :param tasks: list of Task instances
    :param label: name of label to add
    """
    queue_new_label(calls, label)
    for task in (t for t in tasks if label not in t.labels):
        queue_add_label(calls, cast(Task, task), label)


def unlabel_tasks(calls: list[Command], tasks: list[apip_task], label: str):
    """Remove a label from each model in the list.

    :param calls: a list of commands to which new commands will be appended
    :param tasks: list of Task instances
    :param label: name of label to remove
    """
    for task in (t for t in tasks if label in t.labels):
        queue_remove_label(calls, cast(Task, task), label)


def queue_new_label(calls: list[Command], label: str):
    """Return a dictionary (command) to later add a new personal label.

    :param calls: a list of commands to which the new command will be appended
    :param label: label to add to personal labels
    :effect: the command is appended to the :calls: list of commands
    """
    print(f"create personal label '{label}'")
    calls.append(
        {
            "type": "label_add",
            "temp_id": uuid.uuid4().hex,
            "uuid": uuid.uuid4().hex,
            "args": {"name": label},
        }
    )


def queue_add_label(calls: list[Command], task: Task, label: str):
    """Return a dictionary (command) to add a label to an item.

    :param calls: a list of commands to which the new command will be appended
    :param task: item to update
    :param label: label to remove
    :effect: the command is appended to the :calls: list of commands
    """
    labels = task.labels
    print(f"add '{label}' to '{task.content}'")
    calls.append(
        {
            "type": "item_update",
            "uuid": uuid.uuid4().hex,
            "args": {"id": task.id, "labels": labels + [label]},
        }
    )


def queue_remove_label(calls: list[Command], task: Task, label: str):
    """Return a dictionary (command) to remove a label from an item.

    :param calls: a list of commands to which the new command will be appended
    :param task: item to update
    :param label: label to remove
    :effect: the command is appended to the :calls: list of commands
    """
    labels = task.labels
    print(f"remove '{label}' from '{task.content}'")
    calls.append(
        {
            "type": "item_update",
            "uuid": uuid.uuid4().hex,
            "args": {"id": task.id, "labels": [x for x in labels if x != label]},
        }
    )


def write_changes(
    headers: CaseInsensitiveDict[str], changes: list[Command]
) -> JsonDict:
    """Write the changes to the Todoist API.

    :param headers: Headers for the request (produced by headers.get_headers)
    :param changes: list of dictionaries (commands) to add to the API
    :return: response.json() from the API
    """
    resp = requests.post(
        SYNC_URL,
        headers=headers,
        data=json.dumps({"commands": changes}),
    )
    resp.raise_for_status()
    return resp.json()
