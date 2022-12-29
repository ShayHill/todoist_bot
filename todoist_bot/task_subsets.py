"""Selection schemes for identifying tasks at or underneath an automation suffix.

:author: Shay Hill
:created: 2022-12-12
"""

from contextlib import suppress
from functools import partial

from todoist_bot.read_changes import Project, Section, Task
from todoist_bot.tree import AnyNode


def _has_suffix(elem: Project | Section | Task, suffix: str) -> bool:
    """Select an automation from an element name.

    :param elem: a Todoist Project, Section, or Task
    :return: an Automation or None

    Projects, Sections, and Tasks don't use the same attribute for the name. Tasks
    use "content", Projects and Sections use "name".
    """
    if isinstance(elem, (Project, Section)):
        name = elem.name
    else:
        name = elem.content

    return name.strip().endswith(suffix)


def select_serial(
    projects: list[Project],
    sections: list[Section],
    tasks: list[Task],
    id2node: dict[str, AnyNode],
    suffix: str,
) -> tuple[list[Task], list[Task]]:
    """Select next childless task at or under each marked model.

    :param projects: a list of Todoist Projects
    :param sections: a list of Todoist Sections
    :param tasks: a list of Todoist Tasks
    :param id2node: a mapping from Todoist model IDs to Nodes
    :param suffix: a suffix to identify serial tasks
    :return: a tuple of (selected, rejected) tasks
    """
    fselect = partial(_has_suffix, suffix=suffix)
    selected: dict[str, Task] = {}

    for model in filter(fselect, projects + sections + tasks):
        with suppress(StopIteration):
            model_id = model.id
            assert model_id is not None
            with suppress(StopIteration):
                next_task = next(id2node[model_id].iter_childless_tasks())
                selected[next_task.id] = next_task

    return list(selected.values()), [x for x in tasks if x.id not in selected]


def select_parallel(
    projects: list[Project],
    sections: list[Section],
    tasks: list[Task],
    id2node: dict[str, AnyNode],
    suffix: str,
) -> tuple[list[Task], list[Task]]:
    """Select every childless task at or under each marked model.

    :param projects: a list of Todoist Projects
    :param sections: a list of Todoist Sections
    :param tasks: a list of Todoist Tasks
    :param id2node: a mapping from Todoist model IDs to Nodes
    :param suffix: a suffix to identify parallel tasks
    :return: a tuple of (selected, rejected) tasks
    """
    fselect = partial(_has_suffix, suffix=suffix)
    selected: dict[str, Task] = {}

    for model in filter(fselect, projects + sections + tasks):
        model_id = model.id
        assert model_id is not None
        selected.update({x.id: x for x in id2node[model_id].iter_childless_tasks()})

    return list(selected.values()), [x for x in tasks if x.id not in selected]


def select_all(
    projects: list[Project],
    sections: list[Section],
    tasks: list[Task],
    id2node: dict[str, AnyNode],
    suffix: str,
) -> tuple[list[Task], list[Task]]:
    """Select every task at or under each marked model.

    :param projects: a list of Todoist Projects
    :param sections: a list of Todoist Sections
    :param tasks: a list of Todoist Tasks
    :param id2node: a mapping from Todoist model IDs to Nodes
    :param suffix: a suffix to identify parallel tasks
    :return: a tuple of (selected, rejected) tasks
    """
    fselect = partial(_has_suffix, suffix=suffix)
    selected: dict[str, Task] = {}

    for model in filter(fselect, projects + sections + tasks):
        model_id = model.id
        assert model_id is not None
        selected.update({x.id: x for x in id2node[model_id].iter_tasks()})

    return list(selected.values()), [x for x in tasks if x.id not in selected]
