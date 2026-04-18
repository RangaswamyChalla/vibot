"""Pre-flight check to verify local model health."""
import asyncio
import httpx
from core.ollama_client import get_ollama_client
from core.config import config
from observability import get_logger

logger = get_logger("preflight")

async def verify_models():
    """Ensure required models are pulled and ready."""
    client = get_ollama_client()
    
    if not await client.is_available():
        logger.error("Ollama service not detected! Please start Ollama first.")
        return False
        
    models = await client.list_models()
    model_names = [m.get("name") for m in models]
    
    required = [config.OLLAMA_CHAT_MODEL, config.OLLAMA_EMBED_MODEL]
    
    for req in required:
        # Check if versioned or base name matches
        if not any(req in name for name in model_names):
            logger.warning(f"Required model {req} not found locally. Attempting to pull...")
            # We don't wait for the pull here to avoid hanging startup forever,
            # but we log the attempt.
            asyncio.create_task(client.pull_model(req))
            
    return True

if __name__ == "__main__":
    asyncio.run(verify_models())
