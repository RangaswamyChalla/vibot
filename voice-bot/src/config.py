import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration settings
class Config:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    HUGGINGFACE_MODEL_NAME = "mosaicml/mpt-7b-chat"  # Example model name
    AUDIO_TRANSCRIPTION_MODEL = "whisper-1"  # Example transcription model
    TTS_LANGUAGE = "en"  # Language for text-to-speech
    MAX_TOKENS = 150  # Maximum tokens for responses
    DEFAULT_RESPONSES_FILE = "data/responses.json"  # Path to predefined responses file

config = Config()