from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any


ToolHandler = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


@dataclass(frozen=True, slots=True)
class AgentTool:
    name: str
    description: str
    handler: ToolHandler
