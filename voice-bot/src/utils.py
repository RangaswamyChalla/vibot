def text_to_speech(text, filename):
    from gtts import gTTS
    import os

    tts = gTTS(text=text, lang='en')
    tts.save(filename)
    return filename

def load_json(file_path):
    import json

    with open(file_path, 'r') as f:
        return json.load(f)

def handle_error(error):
    import logging

    logging.error(f"An error occurred: {error}")
    return str(error)

# Single source of truth for fallback responses — imported by voice.py, chat.py, orchestrator.py, chat_service.py
FALLBACK_RESPONSES = {
    "life story": "I'm Ranga Swami, someone who has always learned by doing...",
    "superpower": "My superpower is learning and adapting quickly...",
    "grow": "The top 3 areas I'd like to grow in are...",
    "misconception": "People often assume I'm quiet or reserved...",
    "boundaries": "I deliberately take on projects that challenge me...",
    "about me": "I'm Ranga Swami, an AI and backend developer...",
}

def get_fallback(text: str) -> str | None:
    """Single-source fallback matcher — substring match on lowered text."""
    q = text.lower()
    for key, response in FALLBACK_RESPONSES.items():
        if key in q:
            return response
    return None


def estimate_tokens(text: str) -> int:
    """Estimate token count using ~4 chars-per-token (English average)."""
    return max(1, len(text) // 4)

def truncate_history(messages: list[dict], max_tokens: int = 4096,
                     max_messages: int = 20) -> list[dict]:
    """Truncate conversation history to token budget and message count limits.

    Removes oldest messages first, preserving the most recent turns.
    """
    # Hard cap by message count first
    if len(messages) > max_messages:
        messages = messages[-max_messages:]

    # Then enforce token budget by dropping oldest messages until under budget
    while True:
        total = sum(estimate_tokens(m["content"]) for m in messages)
        if total <= max_tokens or len(messages) <= 1:
            break
        messages = messages[1:]  # drop oldest

    return messages