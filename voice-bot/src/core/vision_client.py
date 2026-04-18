"""Client for Ollama vision models."""
import base64
import httpx
from typing import Optional, List
from core.config import config
from observability import get_logger

logger = get_logger("core.vision")

class VisionClient:
    """Client for performing VQA using Ollama vision models."""
    
    def __init__(self, base_url: str = None, model: str = "moondream"):
        self.base_url = base_url or config.OLLAMA_BASE_URL
        self.model = model
        self.timeout = httpx.Timeout(60.0)

    async def analyze_image(self, image_bytes: bytes, prompt: str = "Describe this image.") -> str:
        """Analyze an image with a prompt."""
        encoded_image = base64.b64encode(image_bytes).decode('utf-8')
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "images": [encoded_image]
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(f"{self.base_url}/api/generate", json=payload)
                response.raise_for_status()
                data = response.json()
                return data.get("response", "No vision response received.")
        except Exception as e:
            logger.error(f"Vision analysis failed: {e}")
            return f"Error analyzing image: {str(e)}"

_vision_client = None

def get_vision_client() -> VisionClient:
    global _vision_client
    if _vision_client is None:
        _vision_client = VisionClient()
    return _vision_client
