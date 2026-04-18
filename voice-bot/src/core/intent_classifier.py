"""Two-stage intent classifier: keyword fast-path + LLM classification."""
import re
from dataclasses import dataclass
from typing import Optional

from observability import get_logger
from core.ollama_client import get_ollama_client

logger = get_logger("core.intent")

# Keywords for fast-path intent detection
INTENT_KEYWORDS = {
    "small_talk": [
        "hello", "hi", "hey", "good morning", "good afternoon", "good evening",
        "howdy", "greetings", "what's up", "sup", "yo", "hiya",
        "thanks", "thank you", "thx", "appreciate",
        "bye", "goodbye", "see you", "later", "good night",
        "please", "could you", "would you",
    ],
    "technical": [
        "code", "programming", "python", "javascript", "java", "bug", "debug",
        "api", "database", "sql", "docker", "kubernetes", "git", "github",
        "deploy", "server", "frontend", "backend", "fullstack", "devops",
        "algorithm", "data structure", "performance", "optimize",
    ],
    "kb_query": [
        "what is", "what are", "who is", "who are", "explain", "describe",
        "tell me about", "information about", "details on", "facts about",
        "how do i", "how does", "how to", "what's the difference",
    ],
    "about_me": [
        "life story", "about your life", "who are you", "your background",
        "superpower", "number one", "best skill", "strengths",
        "grow in", "improvements", "weaknesses", "areas to improve",
        "misconception", "coworkers think", "people think",
        "boundaries", "limits", "challenge yourself",
        "your name", "who made you", "your creator",
    ],
}

# Exact phrase matches (higher priority)
INTENT_PHRASES = {
    "about_me": [
        "what should we know about your life story",
        "what's your #1 superpower",
        "what are the top 3 areas you'd like to grow in",
        "what misconception do your coworkers have about you",
        "how do you push your boundaries",
        "tell me about yourself",
        "what is your superpower",
        "what is your life story",
    ],
    "small_talk": [
        "how are you",
        "how's it going",
        "how have you been",
    ],
}


@dataclass
class IntentResult:
    intent: str
    confidence: float
    source: str  # "keyword" or "llm"


class IntentClassifier:
    """Two-stage intent classifier with keyword fast-path."""

    def __init__(self, use_llm_fallback: bool = True):
        self.use_llm_fallback = use_llm_fallback

    async def classify(self, user_input: str) -> IntentResult:
        """Classify user intent using two-stage approach."""
        user_lower = user_input.lower().strip()

        # Stage 1: Exact phrase match (highest priority)
        for intent, phrases in INTENT_PHRASES.items():
            for phrase in phrases:
                if phrase in user_lower:
                    logger.debug(f"Intent '{intent}' matched via phrase")
                    return IntentResult(intent=intent, confidence=1.0, source="keyword")

        # Stage 2: Keyword match
        scores = {}
        for intent, keywords in INTENT_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in user_lower)
            if score > 0:
                scores[intent] = score

        if scores:
            best_intent = max(scores, key=scores.get)
            confidence = min(scores[best_intent] / 2.0, 1.0)  # normalize
            logger.debug(f"Intent '{best_intent}' matched via keywords (confidence={confidence:.2f})")
            return IntentResult(intent=best_intent, confidence=confidence, source="keyword")

        # Stage 3: LLM classification
        if self.use_llm_fallback:
            return await self._llm_classify(user_input)

        return IntentResult(intent="unknown", confidence=0.0, source="default")

    async def _llm_classify(self, user_input: str) -> IntentResult:
        """Use LLM to classify intent."""
        try:
            client = get_ollama_client()
            result = await client.classify_intent(user_input)
            intent = result.get("intent", "unknown")
            confidence = result.get("confidence", 0.5)
            logger.info(f"LLM classified intent: {intent} (confidence={confidence:.2f})")
            return IntentResult(intent=intent, confidence=confidence, source="llm")
        except Exception as e:
            logger.error(f"LLM classification failed: {e}")
            return IntentResult(intent="unknown", confidence=0.0, source="llm_error")


# Singleton
_classifier: Optional[IntentClassifier] = None


def get_intent_classifier() -> IntentClassifier:
    global _classifier
    if _classifier is None:
        _classifier = IntentClassifier()
    return _classifier
