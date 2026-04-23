from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class Node:
    parent: Optional["ElementNode"] = None


@dataclass
class TextNode(Node):
    text: str = ""


@dataclass
class SyntheticEvent:
    type: str
    target: "ElementNode"
    current_target: Optional["ElementNode"] = None
    _stopped: bool = False

    def stop_propagation(self) -> None:
        self._stopped = True


@dataclass
class ElementNode(Node):
    tag: str = "div"
    props: Dict[str, Any] = field(default_factory=dict)
    children: List[Node] = field(default_factory=list)
    _listeners: Dict[str, List[Callable[[SyntheticEvent], None]]] = field(default_factory=dict)

    def append_child(self, node: Node) -> None:
        node.parent = self
        self.children.append(node)

    def add_event_listener(self, type_: str, listener: Callable[[SyntheticEvent], None]) -> None:
        self._listeners.setdefault(type_, []).append(listener)

    def dispatch_event(self, type_: str) -> None:
        event = SyntheticEvent(type=type_, target=self)
        # Bubble from target up to root.
        node = self  # type: Optional[ElementNode]
        while node is not None:
            event.current_target = node
            for listener in node._listeners.get(type_, []):
                listener(event)
                if event._stopped:
                    return
            node = node.parent


@dataclass
class Container:
    root: ElementNode = field(default_factory=lambda: ElementNode(tag="root"))

