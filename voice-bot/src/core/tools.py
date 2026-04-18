"""Tool registry for agentic actions."""
import asyncio
from typing import Callable, Dict, Any, Optional
from observability import get_logger

logger = get_logger("core.tools")

class ToolRegistry:
    """Registry for tools that the LLM can invoke."""
    
    def __init__(self):
        self._tools: Dict[str, Dict[str, Any]] = {}

    def register_tool(self, name: str, description: str, func: Callable):
        """Register a new tool."""
        self._tools[name] = {
            "description": description,
            "func": func
        }
        logger.info(f"Tool registered: {name}")

    def get_tool_descriptions(self) -> str:
        """Get a string representation of available tools for prompt injection."""
        if not self._tools:
            return "No tools available."
            
        lines = []
        for name, info in self._tools.items():
            lines.append(f"- {name}: {info['description']}")
        return "\n".join(lines)

    async def execute_tool(self, name: str, **kwargs) -> Any:
        """Execute a tool by name."""
        if name not in self._tools:
            raise ValueError(f"Tool {name} not found.")
            
        logger.info(f"Executing tool: {name} with args: {kwargs}")
        func = self._tools[name]["func"]
        
        try:
            if asyncio.iscoroutinefunction(func):
                return await func(**kwargs)
            return func(**kwargs)
        except Exception as e:
            logger.error(f"Tool execution failed: {name}, error: {e}")
            return f"Error executing {name}: {str(e)}"

# Singleton registry
_registry = ToolRegistry()

def get_tool_registry() -> ToolRegistry:
    return _registry

# Example tool: Get current time
def get_current_time():
    import datetime
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

_registry.register_tool(
    "get_current_time", 
    "Returns the current date and time.", 
    get_current_time
)
