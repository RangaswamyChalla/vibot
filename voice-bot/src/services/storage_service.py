"""Storage service for conversation persistence."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
import os
import time
from datetime import datetime
from typing import List
from observability import get_logger

logger = get_logger("services.storage")

class StorageService:
    def __init__(self, base_dir: str = None):
        self.base_dir = base_dir or "conversations"
        os.makedirs(self.base_dir, exist_ok=True)

    def save(self, messages: list) -> str:
        """Save conversation to JSON file."""
        if not messages:
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"conv_{timestamp}.json"
        filepath = os.path.join(self.base_dir, filename)

        data = {"messages": messages, "saved_at": timestamp}
        with open(filepath, "w") as f:
            json.dump(data, f)

        logger.info(f"Conversation saved: {filename}")
        return filepath

    def load_all(self) -> List[dict]:
        """Load all saved conversations, newest first."""
        start = time.perf_counter()
        try:
            files = sorted(
                [f for f in os.listdir(self.base_dir)
                 if f.startswith("conv_") and f.endswith(".json")],
                reverse=True
            )
            conversations = []
            for fname in files:
                try:
                    with open(os.path.join(self.base_dir, fname), "r") as f:
                        conversations.append(json.load(f))
                except Exception:
                    pass
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.info(
                "load_all completed: files=%s conversations=%s latency_ms=%.2f",
                len(files),
                len(conversations),
                elapsed_ms,
            )
            return conversations
        except Exception as e:
            logger.error(f"Failed to load conversations: {e}")
            return []

    def delete(self, timestamp: str) -> bool:
        """Delete a conversation by timestamp."""
        fname = f"conv_{timestamp}.json"
        filepath = os.path.join(self.base_dir, fname)
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.info(f"Deleted conversation: {fname}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete {fname}: {e}")
            return False

    def load_by_timestamp(self, timestamp: str) -> dict | None:
        """Load a specific conversation."""
        fname = f"conv_{timestamp}.json"
        filepath = os.path.join(self.base_dir, fname)
        try:
            if os.path.exists(filepath):
                with open(filepath, "r") as f:
                    return json.load(f)
        except Exception:
            pass
        return None