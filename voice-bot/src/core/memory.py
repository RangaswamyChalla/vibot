"""Long-term memory for user preferences and history."""
import json
import os
from typing import Dict, Any

from core.config import config
from observability import get_logger

logger = get_logger("core.memory")

class UserMemory:
    """Manages persistent memory for individual users."""
    
    def __init__(self, storage_dir: str = "data/memory"):
        self.storage_dir = storage_dir
        if not os.path.isabs(storage_dir):
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.storage_dir = os.path.join(project_root, storage_dir)
            
        os.makedirs(self.storage_dir, exist_ok=True)

    def _get_path(self, user_id: str) -> str:
        return os.path.join(self.storage_dir, f"{user_id}.json")

    def get_memory(self, user_id: str) -> Dict[str, Any]:
        """Load user memory from disk."""
        path = self._get_path(user_id)
        if not os.path.exists(path):
            return {}
            
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load memory for {user_id}: {e}")
            return {}

    def set_preference(self, user_id: str, key: str, value: Any):
        """Update a specific preference for a user."""
        memory = self.get_memory(user_id)
        memory[key] = value
        
        path = self._get_path(user_id)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(memory, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save memory for {user_id}: {e}")

# Global memory instance
_user_memory = UserMemory()

def get_user_memory() -> UserMemory:
    return _user_memory
