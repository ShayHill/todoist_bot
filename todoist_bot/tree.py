"""Simple tree for Todoist API models.

This makes for clean code outside this module, but it's a bit noisier here than it
would otherwise be because Todoist allows endless (or near enough) nesting of
projects and tasks. That is, projects can have subprojects can have subprojects can
have subprojects, and tasks can have subtasks can have subtasks can have subtasks,
and so on.

:author: Shay Hill
:created: 2022-12-12
"""
from __future__ import annotations

from collections import deque
from typing import Any, Generic, Iterator, TypeAlias, TypeVar

from todoist_api_python.models import Project, Section, Task

_Model: TypeAlias = Project | Section | Task
_ModelT = TypeVar("_ModelT", bound=_Model)


def _node_sort_key(node: Node[_ModelT]) -> tuple[int, int]:
    """Generate a key so that nodes are sorted by type then order.

    :param node: the node to sort
    :return: a tuple of (type, order)

    Directly-connected tasks are selected first. E.g., if a project has tasks that
    are in a sections and tasks that are not within a section, the tasks that are not
    in a section are selected first.

    Highest priority first:

        * Project -> Task
        * Project -> Section -> Task
        * Project -> Subproject -> Task
        * Project -> Subproject -> Section -> Task
        * Project -> Subproject ... Subproject -> Task
        * Project -> Subproject ... Subproject -> Section -> Task
    """
    if isinstance(node.data, Task):
        return 1, node.data.order
    if isinstance(node.data, Section):
        return 2, node.data.order
    if isinstance(node.data, Task) and node.data.parent_id:
        return 3, node.data.order
    raise ValueError(f"Unexpected node type: {node.data}")


class Node(Generic[_ModelT]):
    """A node in a tree of projects, sections, and tasks."""

    def __init__(self, model: _ModelT):
        self.data: _ModelT = model
        self._children: list[Node[Any]] = []
        self._are_children_sorted: bool = False

    def add_child(self, child: AnyNode) -> None:
        """Add a child to this node.

        :param child: the child to add
        """
        if self._are_children_sorted:
            raise ValueError("Cannot add a child to a sorted node")
        self._children.append(child)

    def _sort_children(self):
        """Sort the children of this node.

        Result is cached, so this can only be called after the tree is built.
        """
        if self._are_children_sorted:
            return
        self._children = sorted(self._children, key=_node_sort_key)
        self._are_children_sorted = True

    def iter_tasks(self) -> Iterator[Task]:
        """Yield all tasks at and beneath self (post-order transversal).

        :effects: sorts self._children
        :yields Task: all tasks under self
        """
        self._sort_children()
        for child in self._children:
            yield from child.iter_tasks()
        if isinstance(self.data, Task):
            yield self.data

    def iter_childless_tasks(self) -> Iterator[Task]:
        """Yield childless tasks at and beneath self (post-order transversal).

        This is the engine that runs parallel processing.

        :yields: every childless task beneath self and self.data if self is childless.
        :effects: sorts self._children
        """
        self._sort_children()
        for child in self._children:
            yield from child.iter_childless_tasks()
        if isinstance(self.data, Task) and not self._children:
            yield self.data


AnyNode = Node[Project] | Node[Section] | Node[Task]


def _place_subs(id2node: dict[str, Node[Project]] | dict[str, Node[Task]]) -> None:
    """Place subtasks or subprojects under their parents.

    :param id2node: map of node ids to nodes (includes parents and perhaps children)
    :effect: if there are any subtasks or subprojects, they are will be added to
        their parent element's children attribute.
    :raised ValueError: if a subtask or subproject is found without a parent
    """
    queue = deque(x for x in id2node.values() if x.data.parent_id is not None)
    while queue:
        found_parent = False
        for _ in range(len(queue)):
            child = queue.popleft()
            parent_id = child.data.parent_id
            assert parent_id is not None
            try:
                id2node[parent_id].add_child(child)
                found_parent = True
            except KeyError:
                queue.append(child)
        if not found_parent:
            raise ValueError("Could not find a parent for all tasks")


def map_id_to_branch(
    projects: list[Project], sections: list[Section], tasks: list[Task]
) -> dict[str, AnyNode]:
    """Build a tree of nodes from the API cache.

    :param api_cache: the API cache
    :return: a map of node ids to nodes. Each node with children will contain
        references to any children, so the branch can be searched downward.

    There will not be a root node to this tree, every Project will be a root.
    """
    project_nodes: dict[str, Node[Project]]
    project_nodes = {p.id: Node(p) for p in projects}
    _place_subs(project_nodes)

    section_nodes: dict[str, Node[Section]]
    section_nodes = {s.id: Node(s) for s in sections}
    for sect in section_nodes.values():
        project_nodes[sect.data.project_id].add_child(sect)

    task_nodes: dict[str, Node[Task]]
    task_nodes = {t.id: Node(t) for t in tasks}
    _place_subs(task_nodes)

    for task in (x for x in task_nodes.values() if x.data.parent_id is None):
        if task.data.section_id:
            section_nodes[task.data.section_id].add_child(task)
        else:
            project_nodes[task.data.project_id].add_child(task)

    return {**project_nodes, **section_nodes, **task_nodes}
