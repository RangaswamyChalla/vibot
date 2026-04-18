# main.py
import os
import tempfile
import requests
import streamlit as st
from audio_recorder_streamlit import audio_recorder
from gtts import gTTS
from dotenv import load_dotenv
import speech_recognition as sr

# Load environment
load_dotenv()

HF_API_TOKEN = os.getenv("HF_API_TOKEN")  # optional; set on the host if you want AI fallback (NOT required)

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

def hf_fallback_prompt(text):
    if not HF_API_TOKEN:
        return ""
    # small, simple HF inference call; used only for non-matching queries
    API_URL = "https://api-inference.huggingface.co/models/gpt2"  # optional; host must set HF_API_TOKEN if desired
    headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}
    payload = {"inputs": text, "parameters": {"max_new_tokens": 150}}
    try:
        resp = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and data and "generated_text" in data[0]:
                return data[0]["generated_text"]
            if isinstance(data, dict) and "error" in data:
                return ""
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

        # direct keyword mapping for exact 5 questions + about me
        chosen = None
        mapping = {
            "life story": ["life story", "about your life", "about you", "who are you"],
            "superpower": ["superpower", "number one", "#1 superpower", "best skill"],
            "grow": ["top 3", "areas you'd like to grow", "areas to grow", "grow in", "top 3 areas"],
            "misconception": ["misconception", "coworkers", "what do coworkers", "what do your coworkers"],
            "boundaries": ["push your boundaries", "push boundaries", "limits", "how do you push"],
            "about me": ["about me", "resume", "linkedin", "summary"]
        }
        for key, kws in mapping.items():
            if any(kw in q for kw in kws):
                chosen = RESPONSES[key]
                break

        # If not matched, try HF fallback (optional) or generic reply
        if not chosen:
            chosen = hf_fallback_prompt(user_text)
            if not chosen:
                chosen = "I can answer: life story, superpower, top 3 areas to grow, coworker misconception, how I push boundaries, or 'about me' for resume. Ask one of those."

        st.success(f"Answer: {chosen}")

        # TTS
        try:
            tts = gTTS(text=chosen, lang="en")
            tfile = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
            tts.save(tfile.name)
            st.audio(tfile.name, format="audio/mp3")
        except Exception as e:
            st.warning("TTS failed: " + str(e))
