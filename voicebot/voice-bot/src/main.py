import streamlit as st
import tempfile
from audio_recorder_streamlit import audio_recorder
from gtts import gTTS
from dotenv import load_dotenv
import os
from src.chatbot import get_bot_response

# Load environment variables
load_dotenv()

# --- Streamlit UI ---
st.title("🎙️ Voice Bot Demo")
st.write("Ask questions like:\n- What should we know about your life story in a few sentences?\n- What’s your #1 superpower?\n- What are the top 3 areas you’d like to grow in?\n- What misconception do your coworkers have about you?\n- How do you push your boundaries and limits?")

# --- Record Audio ---
audio_bytes = audio_recorder()
if audio_bytes:
    # Save audio
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
        f.write(audio_bytes)
        audio_file_path = f.name
    st.audio(audio_file_path, format="audio/wav")

    # --- Convert audio to text ---
    user_text = get_bot_response(audio_file_path)

    if user_text:
        st.text(f"Your question: {user_text}")

        # --- Get Bot Reply ---
        bot_reply = get_bot_response(user_text)
        st.text(f"Bot reply: {bot_reply}")

        # --- Convert Bot Reply to Speech ---
        tts = gTTS(bot_reply)
        tts_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tts.save(tts_file.name)
        st.audio(tts_file.name, format="audio/mp3")