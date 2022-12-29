"""Sync with Todoist and return data.

Only return data if changes have been made since last sync or if explicitly called
with sync_token = "*".

This module already catches and bypasses any expected exceptions. If something goes
wrong with the sync, it will return None. Handle this in main.py by sleeping a bit
then trying again.

:author: Shay Hill
:created: 2022-12-28
"""

import dataclasses
import json
import time
from typing import Optional, cast

import requests
from requests.structures import CaseInsensitiveDict

from todoist_bot.headers import SYNC_URL

# This should cover everything in Todoist response.json()
_JsonDictValue = str | int | bool | None | list["_JsonDict"] | dict[str, "_JsonDict"]
_JsonDict = dict[str, _JsonDictValue]
_Objects = list[_JsonDict]

# This is everything this project will look at.
_RESOURCE_TYPES = ("items", "labels", "projects", "sections")


@dataclasses.dataclass
class _Model:
    data: _JsonDict
    id: str = dataclasses.field(init=False)

    def __post_init__(self) -> None:
        """Cast some properties."""
        self.id = cast(str, self.data["id"])

    def __getattr__(self, name: str) -> _JsonDictValue:
        """Get attribute from data dict.

        :param name: Attribute name.
        :return: self.data[name]
        :raise AttributeError: If attribute is not found.
        """
        try:
            return self.data[name]
        except KeyError as e:
            raise AttributeError(
                f"{self.__class__.__name__} has no attribute {name}"
            ) from e


Label = type("Label", (_Model,), {})


class Project(_Model):
    """Project model."""

    name: str = dataclasses.field(init=False)
    child_order: int = dataclasses.field(init=False)
    parent_id: str = dataclasses.field(init=False)

    def __post_init__(self) -> None:
        """Cast some properties."""
        super().__post_init__()
        self.name = cast(str, self.data["name"])
        self.child_order = cast(int, self.data["child_order"])
        self.parent_id = cast(str, self.data["parent_id"])


class Section(_Model):
    """Project model."""

    name: str = dataclasses.field(init=False)
    section_order: int = dataclasses.field(init=False)
    project_id: str = dataclasses.field(init=False)

    def __post_init__(self) -> None:
        """Cast some properties."""
        super().__post_init__()
        self.name = cast(str, self.data["name"])
        self.section_order = cast(int, self.data["section_order"])
        self.project_id = cast(str, self.data["project_id"])


class Task(_Model):
    """Task model."""

    labels: list[str] = dataclasses.field(init=False)
    content: str = dataclasses.field(init=False)
    child_order: int = dataclasses.field(init=False)
    parent_id: str = dataclasses.field(init=False)
    project_id: str = dataclasses.field(init=False)
    section_id: str = dataclasses.field(init=False)

    def __post_init__(self) -> None:
        """Cast some properties."""
        super().__post_init__()
        self.labels = cast(list[str], self.data["labels"])
        self.content = cast(str, self.data["content"])
        self.child_order = cast(int, self.data["child_order"])
        self.parent_id = cast(str, self.data["parent_id"])
        self.project_id = cast(str, self.data["project_id"])
        self.section_id = cast(str, self.data["section_id"])


class Todoist:
    """Todist data model.

    The api just returns projects, sections, tasks, etc. as a dictionary of lists of
    dictionaries. The only way to distinguish a task from a project, for instance, is
    to look at the dictionary keys or pass around the entire export json dictionary
    and take "item" or "project" keys from it. That works, but it makes things like
    isintance() (and other nice ways to sort objects) a little less straightforward.
    """

    def __init__(self, resp_json: _JsonDict) -> None:
        """Initialize a Todoist object from a Todoist response.json()

        :param resp_json: The response.json() from a Todoist API call

        For any resource type with an associated _Model class in _RESOURCE_TYPES,
        create a list of _Model instances. For resource types with a None value in
        _RESOURCE_TYPES, assign the returned value to an attribute of the same name.
        """
        self.sync_token = cast(str, resp_json["sync_token"])
        self.labels = [Label(x) for x in cast(_Objects, resp_json["labels"])]
        self.projects = [Project(x) for x in cast(_Objects, resp_json["projects"])]
        self.sections = [Section(x) for x in cast(_Objects, resp_json["sections"])]
        self.tasks = [Task(x) for x in cast(_Objects, resp_json["items"])]


def read_changes(
    headers: CaseInsensitiveDict[str], sync_token: str = "*"
) -> Optional[Todoist]:
    """Load changes from Todoist or raise exception.

    :param headers: Headers for the request (produced by headers.get_headers)
    :param sync_token: Token to sync from. If any changes are found, will request
        again with "*" to return all data.
    :return: Todoist data as a Todoist instance or None if no changes have been made.

    If no changes have been made or sync fails, return an empty dictionary.
    If any changes have been made, request and return ALL data, not just the changes.
    """
    data = {"sync_token": sync_token, "resource_types": list(_RESOURCE_TYPES)}
    try:
        resp = requests.post(SYNC_URL, headers=headers, data=json.dumps(data))
        resp.raise_for_status()
    except Exception as e:
        print(f"Failed to reach Todoist: {e}")
        return None

    resp_json = cast(_JsonDict, resp.json())

    if not any(resp_json[r] for r in _RESOURCE_TYPES):
        print("No changes since last sync")
        return None

    if not resp_json["full_sync"]:
        # changes have been made, return all data
        time.sleep(1)
        return read_changes(headers)

    print("Changes found, refreshing all data")
    todoist = Todoist(resp_json)
    return todoist
