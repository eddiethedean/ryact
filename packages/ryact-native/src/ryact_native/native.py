from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class NativeNode:
    parent: Optional["NativeView"] = None


@dataclass
class NativeText(NativeNode):
    text: str = ""


@dataclass
class NativeView(NativeNode):
    name: str = "View"
    props: Dict[str, Any] = field(default_factory=dict)
    children: List[NativeNode] = field(default_factory=list)

    def append_child(self, node: NativeNode) -> None:
        node.parent = self
        self.children.append(node)


@dataclass
class NativeContainer:
    root: NativeView = field(default_factory=lambda: NativeView(name="Root"))

