import streamlit as st
import tempfile
import os
from pydub import AudioSegment
import speech_recognition as sr
from openai import OpenAI

openai = OpenAI()(api_key=os.getenv("OPENAI_API_KEY"))

def record_audio():
    audio_bytes = st.audio_recorder()
    if audio_bytes:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            f.write(audio_bytes)
            return f.name
    return None

def convert_audio_to_text(audio_file_path):
    recognizer = sr.Recognizer()
    audio = AudioSegment.from_wav(audio_file_path)
    audio.export("temp.wav", format="wav")
    
    with sr.AudioFile("temp.wav") as source:
        audio_data = recognizer.record(source)
        try:
            text = recognizer.recognize_google(audio_data)
            return text
        except sr.UnknownValueError:
            st.error("Could not understand audio")
            return ""
        except sr.RequestError as e:
            st.error(f"Could not request results from Google Speech Recognition service; {e}")
            return ""

def save_audio_file(audio_bytes):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
        f.write(audio_bytes)
        return f.name

openai.ChatCompletion.create()