import streamlit as st
import tempfile
import os
import time
import base64
import httpx
import asyncio
from audio_recorder_streamlit import audio_recorder
from dotenv import load_dotenv

from services.stt_service import STTService
from services.chat_service import ChatService
from services.tts_service import TTSService
from services.storage_service import StorageService
from core.config import config
from observability import get_logger

load_dotenv()
logger = get_logger("main")

# Initialize services
stt_service = STTService()
chat_service = ChatService()
tts_service = TTSService()
storage_service = StorageService()

st.set_page_config(page_title="VoiceBot AXIOM", layout="wide", page_icon="🤖")

# --- Custom Styling ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600&display=swap');
    html, body, [class*="css"] { font-family: 'Outfit', sans-serif; }
    .main { background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%); }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: rgba(255,255,255,0.05); border-radius: 10px; padding: 10px 20px; color: white; }
    .stTabs [aria-selected="true"] { background-color: rgba(255,255,255,0.15); border-bottom: 2px solid #3498db; }
</style>
""", unsafe_allow_html=True)

# --- Sidebar ---
st.sidebar.title("Axiom Console")
backend_mode = st.sidebar.selectbox("Brain Engine", ["AXIOM (Local Ollama)", "Legacy (OpenAI)"])
selected_voice = st.sidebar.selectbox("Voice", ["fable", "alloy", "echo", "nova", "shimmer"])

# --- App State ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- Helper Functions ---
async def axiome_chat(message: str):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/api/chat",
                json={"message": message},
                headers={"X-API-Key": config.VOICEBOT_API_KEY},
                timeout=60.0
            )
            return response.json() if response.status_code == 200 else None
    except Exception as e:
        logger.error(f"AXIOM API error: {e}")
        return None

# --- Main UI ---
st.title("🤖 VoiceBot AXIOM")
st.caption("Next-Gen Multi-Agent Productivity Suite")

tab1, tab2, tab3 = st.tabs(["🎙️ Voice", "💬 Text", "👁️ Vision"])

# History block
if st.session_state.messages:
    with st.expander("Conversation History", expanded=True):
        for msg in st.session_state.messages:
            st.chat_message(msg["role"]).write(msg["content"])

with tab1:
    audio_bytes = audio_recorder(text="Speak to AXIOM", icon_size="2x")
    if audio_bytes:
        with st.spinner("Processing voice..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
                f.write(audio_bytes)
                path = f.name
            user_text = stt_service.transcribe(path)
            if user_text:
                st.session_state.messages.append({"role": "user", "content": user_text})
                if backend_mode == "AXIOM (Local Ollama)":
                    res = asyncio.run(axiome_chat(user_text))
                    bot_reply = res.get("reply") if res else "API Offline"
                else:
                    bot_reply = chat_service.chat(user_text)
                
                st.session_state.messages.append({"role": "assistant", "content": bot_reply})
                audio_res = tts_service.synthesize(bot_reply, selected_voice)
                if audio_res:
                    st.audio(audio_res)
                st.rerun()

with tab2:
    q = st.text_input("Message AXIOM...")
    if st.button("Submit") and q:
        st.session_state.messages.append({"role": "user", "content": q})
        with st.spinner("Thinking..."):
            if backend_mode == "AXIOM (Local Ollama)":
                res = asyncio.run(axiome_chat(q))
                bot_reply = res.get("reply") if res else "Backend Offline"
            else:
                bot_reply = chat_service.chat(q)
        st.session_state.messages.append({"role": "assistant", "content": bot_reply})
        st.audio(tts_service.synthesize(bot_reply, selected_voice))
        st.rerun()

with tab3:
    st.subheader("Visual Analysis")
    img_file = st.file_uploader("Upload an image...", type=["jpg", "png", "jpeg"])
    prompt = st.text_input("Analysis prompt", value="Describe this image in detail.")
    if img_file and st.button("Analyze Image"):
        with st.spinner("Analyzing with AXIOM Vision..."):
            try:
                files = {"file": (img_file.name, img_file.getvalue(), img_file.type)}
                data = {"prompt": prompt}
                headers = {"X-API-Key": config.VOICEBOT_API_KEY}
                async def run_vision():
                    async with httpx.AsyncClient() as client:
                        return await client.post("http://localhost:8000/api/vision/analyze", 
                                               files=files, data=data, headers=headers)
                res = asyncio.run(run_vision())
                if res.status_code == 200:
                    st.success(res.json()["analysis"])
                else:
                    st.error(f"Vision Error: {res.text}")
            except Exception as e:
                st.error(f"Connection Error: {e}")

if st.button("Reset Session"):
    st.session_state.messages = []
    st.rerun()
