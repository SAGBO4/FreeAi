"""Base Agent abstraction."""

import abc
import logging
from typing import Dict, Any, List
from app.tools.gateway import ToolGateway

logger = logging.getLogger("agent")


class BaseAgent(abc.ABC):
    def __init__(self, name: str, role: str, tool_gateway: ToolGateway):
        self.name = name
        self.role = role
        self.tool_gateway = tool_gateway

    @abc.abstractmethod
    async def execute_task(self, task_description: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Executes a specialized task and returns a structured outcome."""
        pass
