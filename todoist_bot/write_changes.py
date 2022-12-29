"""Add or remove labels from Todoist tasks.

All functions have an is_dry_run parameter that defaults to False. If True, no
changes will be written to Todoist.

:author: Shay Hill
:created: 2022-12-12
"""

import json
import time
import uuid

import requests
from requests.structures import CaseInsensitiveDict

from todoist_bot.headers import SYNC_URL
from todoist_bot.read_changes import Task

# commands to send to Todist API. Bigger isn't much faster. I don't know what the
# soft limit is, but I get a lot of bad requests over a few hundred.
_COMMAND_CHUNK_SIZE = 99

Command = dict[str, str | dict[str, str | int | list[str]]]


def queue_new_label(commands: list[Command], label: str):
    """Return a dictionary (command) to later add a new personal label.

    :param commands: a list of commands to which the new command will be appended
    :param label: label to add to personal labels
    :effect: the command is appended to the :calls: list of commands
    """
    print(f"create personal label '{label}'")
    commands.append(
        {
            "type": "label_add",
            "temp_id": uuid.uuid4().hex,
            "uuid": uuid.uuid4().hex,
            "args": {"name": label},
        }
    )


def queue_add_label(commands: list[Command], task: Task, label: str):
    """Return a dictionary (command) to add a label to an item.

    :param commands: a list of commands to which the new command will be appended
    :param task: item to update
    :param label: label to remove
    :effect: the command is appended to the :calls: list of commands
    """
    print(f"add '{label}' to '{task.content}'")
    commands.append(
        {
            "type": "item_update",
            "uuid": uuid.uuid4().hex,
            "args": {"id": task.id, "labels": task.labels + [label]},
        }
    )


def queue_remove_label(commands: list[Command], task: Task, label: str):
    """Return a dictionary (command) to remove a label from an item.

    :param commands: a list of commands to which the new command will be appended
    :param task: item to update
    :param label: label to remove
    :effect: the command is appended to the :calls: list of commands
    """
    print(f"remove '{label}' from '{task.content}'")
    commands.append(
        {
            "type": "item_update",
            "uuid": uuid.uuid4().hex,
            "args": {"id": task.id, "labels": [x for x in task.labels if x != label]},
        }
    )


def _write_some_changes(
    headers: CaseInsensitiveDict[str], commands: list[Command]
) -> str:
    """Write changes to the Todoist API.

    :param headers: Headers for the request (produced by headers.get_headers)
    :param commands: list of dictionaries (commands) to add to the API
    :return: sync_token from the API
    """
    resp = requests.post(
        SYNC_URL,
        headers=headers,
        data=json.dumps({"commands": commands}),
    )
    resp.raise_for_status()
    return str(resp.json()["sync_token"])


def write_changes(
    sync_token: str, headers: CaseInsensitiveDict[str], commands: list[Command]
) -> str:
    """Write the changes to the Todoist API, one chunk at a time.

    :param sync_token: current sync_token, will be updated if any commands are sent
    :param headers: Headers for the request (produced by headers.get_headers)
    :param commands: list of dictionaries (commands) to add to the API
    :return: sync_token from the API

    I don't know what the soft limit is, but I get lot of bad request errors if I
    send 1000 commands at once.
    """
    if not commands:
        return sync_token
    try:
        sync_token = _write_some_changes(headers, commands[:_COMMAND_CHUNK_SIZE])
    except Exception as e:
        print(e)
        # give up and start the whole main loop over
        return "*"
    time.sleep(1)
    return write_changes(sync_token, headers, commands[_COMMAND_CHUNK_SIZE:])
