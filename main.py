# main.py
import os
import tempfile
import re
import streamlit as st
from audio_recorder_streamlit import audio_recorder
from gtts import gTTS
from dotenv import load_dotenv
import speech_recognition as sr

# Load environment
load_dotenv()

# Exact, authoritative responses for the 5 questions + resume summary
RESPONSES = {
    "life story": "I’m Ranga Swami, someone who has always learned by doing. I grew up in an environment where opportunities had to be created, not given. My passion for technology led me to explore AI, backend development, and full-stack solutions, constantly experimenting, learning, and solving problems. Every project has strengthened my problem-solving skills, resilience, and ability to adapt to new challenges.",
    "superpower": "My superpower is learning and adapting quickly. I can dive into new technologies, APIs, or frameworks and become productive in a short time. Whether it’s debugging complex code or designing AI solutions, I can break problems down logically and deliver results efficiently.",
    "grow": "The top 3 areas I'd like to grow in are: Developing production-ready AI systems that are robust, intelligent, and user-friendly; scaling backend systems with optimized performance, fault-tolerance, and low latency; and leadership and collaboration skills to guide teams, communicate effectively, and contribute to product strategy.",
    "misconception": "People often assume I’m quiet or reserved. While I do observe and analyze before speaking, I am highly collaborative and proactive once engaged. Many of my strongest contributions come from thoughtful planning and problem-solving, which sometimes surprises coworkers at first.",
    "boundaries": "I deliberately take on projects or tasks that challenge me, forcing me to learn new skills, think differently, and step outside my comfort zone. I constantly experiment, set personal deadlines, and explore innovative solutions to ensure growth and improvement.",
    "about me": "I’m Ranga Swami, an AI and backend developer passionate about building intelligent, scalable applications. Skilled in Python, Django, Flask, and FastAPI, I specialize in creating AI-driven solutions like voice bots and video/image processing tools. Curious and results-driven, I thrive on solving complex problems, learning fast, and delivering practical, high-impact solutions."
}

# Streamlit UI
st.set_page_config(page_title="Ranga Swami - Voice Bot", layout="centered")
st.title("🎙️ Ranga Swami - Voice Bot")
st.write("Ask one of these: life story, superpower, top 3 areas to grow, misconception coworkers have, how I push boundaries, or 'about me' for resume summary.")

# Record Audio
audio_bytes = audio_recorder(text="🎤 Click to record", icon_size="2x")

def transcribe_file(path):
    try:
        r = sr.Recognizer()
        with sr.AudioFile(path) as source:
            audio = r.record(source)
        return r.recognize_google(audio)
    except sr.UnknownValueError:
        return ""
    except Exception:
        return ""

if audio_bytes:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
        f.write(audio_bytes)
        audio_path = f.name

    st.audio(audio_path, format="audio/wav")
    user_text = transcribe_file(audio_path)
    if not user_text:
        user_text = st.text_input("Type your question (or paste):")

    if user_text:
        st.info(f"Question: {user_text}")
        q = user_text.lower()

        # Advanced Regex conditional rule mapping
        chosen = None
        mapping = {
            "life story": r"\b(life\s*story|about\s*your\s*life|about\s*you|who\s*are\s*you)\b",
            "superpower": r"\b(superpower|number\s*one|best\s*skill|strongest)\b",
            "grow": r"\b(top\s*3|areas?(?:.*)(?:grow|improve)|grow(ing)?\s*in|weakness)\b",
            "misconception": r"\b(misconception|coworkers?|colleagues?|assume)\b",
            "boundaries": r"\b(push(?:ing)?.*?boundaries|limits|comfort\s*zone)\b",
            "about me": r"\b(about\s*me|resume|linkedin|summary)\b"
        }
        
        for key, pattern in mapping.items():
            if re.search(pattern, q):
                chosen = RESPONSES[key]
                break

        # Strictly secure local fallback without API leakage
        if not chosen:
            chosen = "Sorry, for complete data security, I am strictly programmed to answer specific profile questions locally. You can ask me about my life story, my superpower, areas I want to grow in, coworker misconceptions, how I push boundaries, or ask for a resume summary."

        st.success(f"Answer: {chosen}")

        # TTS
        try:
            tts = gTTS(text=chosen, lang="en")
            tfile = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
            tts.save(tfile.name)
            st.audio(tfile.name, format="audio/mp3")
        except Exception as e:
            st.warning("TTS failed: " + str(e))
