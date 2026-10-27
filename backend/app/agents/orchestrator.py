from typing import Any

from app.agents.base import Agent


class AgentOrchestrator:
    """Thin boundary for an agent implementation selected in a later WP."""

    def __init__(self, agent: Agent):
        self._agent = agent

    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        return await self._agent.run(input_data)
