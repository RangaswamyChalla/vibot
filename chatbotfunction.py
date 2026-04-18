from openai import OpenAI
from dotenv import load_dotenv
import os
import datetime

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise Exception("OPENAI_API_KEY is missing. Create .env file!")

client = OpenAI(api_key=api_key)


FALLBACK_RESPONSES = {
    "life story": "I'm Ranga Swami, someone who has always learned by doing. I grew up in an environment where opportunities had to be created, not given. My passion for technology led me to explore AI, backend development, and full-stack solutions.",
    "superpower": "My superpower is learning and adapting quickly. I can dive into new technologies, APIs, or frameworks and become productive in a short time.",
    "grow": "The top 3 areas I'd like to grow in are: Developing production-ready AI systems, scaling backend systems with optimized performance, and leadership and collaboration skills.",
    "misconception": "People often assume I'm quiet or reserved. While I do observe and analyze before speaking, I am highly collaborative and proactive once engaged.",
    "boundaries": "I deliberately take on projects that challenge me, forcing me to learn new skills, think differently, and step outside my comfort zone.",
    "about me": "I'm Ranga Swami, an AI and backend developer passionate about building intelligent, scalable applications. Skilled in Python, Django, Flask, and FastAPI."
}

FALLBACK_MAPPING = {
    "life story": ["life story", "about your life", "who are you"],
    "superpower": ["superpower", "number one", "best skill"],
    "grow": ["top 3", "areas to grow", "grow in"],
    "misconception": ["misconception", "coworkers"],
    "boundaries": ["push boundaries", "limits", "push your boundaries"],
    "about me": ["about me", "resume", "summary"]
}


def get_fallback_response(text):
    q = text.lower()
    for key, keywords in FALLBACK_MAPPING.items():
        if any(kw in q for kw in keywords):
            return FALLBACK_RESPONSES[key]
    return None


def speech_to_text_conversion(file_path):
    """Converts audio format message to text using OpenAI's Whisper model."""
    try:
        audio_file = open(file_path, "rb")
        transcription = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file
        )
        audio_file.close()
        return transcription.text
    except Exception as e:
        return None


def text_chat(text):
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are Ranga Swami, an AI and backend developer. You respond to questions about: your life story, superpower, top 3 areas to grow in, coworker misconceptions, how you push boundaries, and general about-me questions. Keep answers concise and personable."},
                {"role": "user", "content": text}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        fallback = get_fallback_response(text)
        if fallback:
            return fallback
        return None


def text_to_speech_conversion(text, voice="fable"):
    """Converts text to audio format message using OpenAI's text-to-speech model - tts-1."""
    if not text:
        return None
    try:
        speech_file_path = datetime.datetime.now().strftime("%Y%m%d%H%M%S") + "_speech.webm"
        response = client.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=text
        )
        response.stream_to_file(speech_file_path)
        with open(speech_file_path, "rb") as audio_file:
            audio_data = audio_file.read()
        os.remove(speech_file_path)
        return audio_data
    except Exception as e:
        return None