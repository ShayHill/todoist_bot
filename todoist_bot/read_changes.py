"""Sync with Todoist and return data.

Only return data if changes have been made since last sync or if explicitly called
with sync_token = "*".

This module already catches and bypasses any expected exceptions. If something goes
wrong with the sync, it will return None. Handle this in main.py by sleeping a bit
then trying again.

:author: Shay Hill
:created: 2022-12-28
"""

import json
from dataclasses import dataclass
from typing import Optional, Type, TypeVar, cast

import requests
from requests.structures import CaseInsensitiveDict

from todoist_bot.headers import SYNC_URL

# This should cover everything in Todoist response.json()
JsonDictValue = str | int | bool | None | list["JsonDict"] | dict[str, "JsonDict"]
JsonDict = dict[str, JsonDictValue]
Objects = list[JsonDict]

_T = TypeVar("_T", str, int, bool, None, list["JsonDict"], dict[str, "JsonDict"])


@dataclass(frozen=True)
class _Model:
    data: JsonDict

    def __getattr__(self, name: str) -> JsonDictValue:
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

    def _getitem_assert_type(self, name: str, expected_type: Type[_T]) -> _T:
        """Get item from data dict and assert its type.

        :param key: Key
        :param expected_type: Expected type
        :return: self.data[key]
        :raise AttributeError: If attribute is not found
        :raise AssertionError: If item is not of expected type
        """
        try:
            value = self.data[name]
        except KeyError as e:
            raise AttributeError(
                f"{self.__class__.__name__} has no attribute {name}"
            ) from e
        assert isinstance(value, expected_type), f"{name} must be {expected_type}"
        return value

    @property
    def id(self) -> str:
        """Get id from data dict.

        :return: self.data["id"]
        :raise AttributeError: If id is not found.

        Every model has an id. Return it.
        """
        return self._getitem_assert_type("id", str)

    @property
    def labels(self) -> list[str]:
        """Get labels from data dict.

        :return: self.data["labels"]
        :raise AttributeError: If labels is not found.

        Only Tasks have labels.
        """
        labels = self._getitem_assert_type("labels", list)
        assert all(isinstance(label, str) for label in labels)
        return cast(list[str], labels)


Label = type("Label", (_Model,), {})
Note = type("Note", (_Model,), {})
Project = type("Project", (_Model,), {})
ProjectNote = type("ProjectNote", (_Model,), {})
Section = type("Section", (_Model,), {})
Task = type("Task", (_Model,), {})


_RESOURCE_TYPES: dict[str, Type[_Model] | None] = {
    "labels": Label,
    "notes": Note,
    "project_notes": ProjectNote,
    "projects": Project,
    "sections": Section,
    "items": Task,
}


class Todoist:
    """Todist data model.

    The api just returns projects, sections, tasks, etc. as a dictionary of lists of
    dictionaries. The only way to distinguish a task from a project, for instance, is
    to look at the dictionary keys or pass around the entire export json dictionary
    and take "item" or "project" keys from it. That works, but it makes things like
    isintance() (and other nice ways to sort objects) a little less straightforward.
    """

    def __init__(self, resp_json: JsonDict) -> None:
        """Initialize a Todoist object from a Todoist response.json()

        :param resp_json: The response.json() from a Todoist API call

        For any resource type with an associated _Model class in _RESOURCE_TYPES,
        create a list of _Model instances. For resource types with a None value in
        _RESOURCE_TYPES, assign the returned value to an attribute of the same name.
        """
        for attrib, constructor in _RESOURCE_TYPES.items():
            if constructor is None:
                setattr(self, attrib, resp_json[attrib])
                continue
            objects = cast(Objects, resp_json[attrib])
            setattr(self, attrib, [constructor(obj) for obj in objects])


def read_refresh(
    headers: CaseInsensitiveDict[str], sync_token: str = "*"
) -> Optional[Todoist]:
    """Load changes from Todoist or raise exception.

    :param headers: Headers for the request (produced by headers.get_headers)
    :param sync_token: Token to sync from. If *any* changes are found, will request
        again with "*" to return all data.
    :return: Todoist data as a Todoist instance or None if no changes have been made.

    If no changes have been made or sync fails, return an empty dictionary.
    If any changes have been made, request and return ALL data, not just the changes.
    """
    data = {"sync_token": sync_token, "resource_types": list(_RESOURCE_TYPES.keys())}
    try:
        resp = requests.post(SYNC_URL, headers=headers, data=json.dumps(data))
        resp.raise_for_status()
    except Exception as e:
        print(f"Failed to reach Todoist: {e}")
        return None

    resp_json = cast(JsonDict, resp.json())

    if not any(resp_json[r] for r in _RESOURCE_TYPES):
        print("No changes since last sync")
        return None

    if sync_token != "*":
        # changes have been made, return all data
        return read_refresh(headers, "*")

    todoist = Todoist(resp_json)
    return todoist
