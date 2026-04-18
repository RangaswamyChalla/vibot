# Voice Bot Project

This project is a voice bot application built using Streamlit, designed to respond to user queries using ChatGPT's API. The bot handles audio input end-to-end: transcribe → LLM response → TTS audio reply.

## Project Structure

```
voice-bot/
├── src/
│   ├── main.py          # Streamlit UI entry point
│   ├── config.py        # Configuration settings
│   ├── chatbot.py       # Chatbot logic (deprecated, use chatbotfunction.py)
│   ├── audio_handler.py # Audio recording and processing
│   └── utils.py         # Utility functions
├── data/
│   └── responses.json   # Fallback responses
├── .streamlit/
│   └── config.toml      # Streamlit theme & config
├── requirements.txt     # Dependencies
├── .env.example         # Template for .env
└── README.md
```

## Features

- **Voice mode** — record audio, transcribe with Whisper-1, get GPT response, hear TTS reply
- **Text mode** — type questions, still get voice reply
- **5 TTS voices** — Fable, Echo, Onyx, Nova, Alloy
- **Fallback responses** — keyword-matched answers when OpenAI quota is exceeded
- **Conversation history** — chat bubbles + clear button
- **UX polish** — loading spinners, error handling, audio duration validation

## Setup

1. **Clone and install**
   ```bash
   git clone <repo>
   cd voice-bot
   pip install -r requirements.txt
   ```

2. **Configure**
   ```bash
   cp .env.example .env
   # Edit .env and add your OPENAI_API_KEY
   ```

3. **Run**
   ```bash
   streamlit run src/main.py
   ```

## Deployment

### Streamlit Cloud

1. Push to GitHub
2. Connect repo at [share.streamlit.io](https://share.streamlit.io)
3. Select `voice-bot/src/main.py` as main file
4. Add secret: `OPENAI_API_KEY` = your key

### VPS

```bash
cd voice-bot
pip install -r requirements.txt
streamlit run src/main.py --server.port 8501
```

## Usage

Ask questions like:
- What should we know about your life story?
- What's your #1 superpower?
- What are the top 3 areas you'd like to grow in?
- What misconception do your coworkers have about you?
- How do you push your boundaries?
