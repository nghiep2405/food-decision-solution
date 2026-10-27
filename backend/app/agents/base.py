from typing import Any, Protocol


class Agent(Protocol):
    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Return structured data instead of free-form output."""
        ...
