"""Chat service using OpenAI GPT with fallback responses."""
import os
from openai import OpenAI
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from openai import OpenAI
from core.retry import retry
from core.config import config
from utils import truncate_history
from observability import get_logger

logger = get_logger("services.chat")

FALLBACK_RESPONSES = {
    "life story": "I'm Ranga Swami, someone who has always learned by doing...",
    "superpower": "My superpower is learning and adapting quickly...",
    "grow": "The top 3 areas I'd like to grow in are...",
    "misconception": "People often assume I'm quiet or reserved...",
    "boundaries": "I deliberately take on projects that challenge me...",
    "about me": "I'm Ranga Swami, an AI and backend developer..."
}

FALLBACK_MAPPING = {
    "life story": ["life story", "about your life", "who are you"],
    "superpower": ["superpower", "number one", "best skill"],
    "grow": ["top 3", "areas to grow", "grow in"],
    "misconception": ["misconception", "coworkers"],
    "boundaries": ["push boundaries", "limits"],
    "about me": ["about me", "resume", "summary"]
}

def get_fallback(text: str) -> str | None:
    q = text.lower()
    for key, keywords in FALLBACK_MAPPING.items():
        if any(kw in q for kw in keywords):
            return FALLBACK_RESPONSES[key]
    return None

class ChatService:
    def __init__(self, api_key: str = None):
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))

    @retry(exceptions=(Exception,), max_retries=3, delay=1.0, logger=logger)
    def chat(self, user_input: str, context: list = None) -> str:
        """Send message to GPT and return response with retry logic."""
        logger.info(f"Chat request: {user_input[:50]}...")

        system_prompt = (
            "You are Ranga Swami, an AI and backend developer. You respond to questions "
            "about: your life story, superpower, top 3 areas to grow in, coworker misconceptions, "
            "how you push boundaries, and general about-me questions. Keep answers concise."
        )

        messages = [{"role": "system", "content": system_prompt}]
        if context:
            # Enforce token budget on conversation history before sending to API
            context = truncate_history(
                context,
                max_tokens=config.MAX_TOKEN_BUDGET,
                max_messages=config.MAX_HISTORY_MESSAGES,
            )
            messages.extend(context)
        messages.append({"role": "user", "content": user_input})

        # AXIOM LOCAL-ONLY: Use Ollama exclusively — no external API calls
        try:
            from core.ollama_client import get_ollama_client, ChatMessage
            import asyncio

            def _force_sync(coro):
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        return executor.submit(lambda: asyncio.run(coro)).result()
                else:
                    return loop.run_until_complete(coro)

            client = get_ollama_client()
            ollama_context = [ChatMessage(role=m["role"], content=m["content"]) for m in (context or [])]
            logger.info("Routing to AXIOM (Ollama) — local inference only...")
            ollama_resp = _force_sync(client.chat(message=user_input, context=ollama_context, timeout=120.0))
            logger.info(f"AXIOM response received: {ollama_resp.message[:50]}...")
            return ollama_resp.message

        except Exception as ollama_err:
            logger.warning(f"AXIOM (Ollama) failed: {ollama_err}. Using local keyword fallback only.")

        # Local keyword fallback — NEVER calls external APIs
        fallback = get_fallback(user_input)
        if fallback:
            logger.info("Using local keyword response (offline mode)")
            return fallback

        return "I'm currently running in offline mode. Please ask about my life story, superpower, areas to grow, coworker misconceptions, how I push boundaries, or about me."