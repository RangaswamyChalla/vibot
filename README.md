<div align="center">
  <img src="assets/banner.png" alt="ViBot Banner" width="100%"/>
  <br>
  <h1>🎙️ ViBot: Ranga Swami - Voice Bot</h1>
  <p><b>An interactive, AI-driven voice and text bot designed to showcase backend engineering, rapid learning, and intelligent problem-solving.</b></p>
</div>

<hr>

## 🚀 Overview

**ViBot** is a dynamic, multi-modal application built using **Streamlit**. It elegantly handles end-to-end interactions by blending speech-to-text integration, keyword-based conversational logic, AI-fallback inference via Hugging Face, and Text-to-Speech (TTS) synthesis. 

This project perfectly demonstrates how to build functional and responsive voice assistants capable of both handling specific scripted interactions and flexibly falling back to AI language models.

---

## ✨ Features

- **🗣️ Audio & Voice Input:** Record audio directly in the browser. Transcribes the input cleanly for logic processing.
- **⌨️ Text Fallback User Input:** Seamless option to type your question directly if voice isn't accessible.
- **🧠 Authoritative Knowledge Graph:** Maps exact intents to pre-defined responses ensuring polished communication (e.g. "superpower", "areas to grow", "life story").
- **🫂 Hugging Face AI Fallback:** Utilizes the Hugging Face API to confidently inference open-ended generic responses when out-of-scope inquiries are made.
- **🔊 Text-to-Speech Synthesis:** Transforms the final text-based answer back into high-quality audio using `gTTS`.
- **🎨 Glassmorphic & Modern UX:** Highly polished setup utilizing Streamlit's robust UI elements like spinners, custom audio players, and interactive banners.

---

## 🛠️ Architecture and Stack

- **Frontend:** [Streamlit](https://streamlit.io/)
- **Voice Recording:** `audio_recorder_streamlit`
- **Speech Recognition:** `SpeechRecognition` module (Google Web Speech API / configurable)
- **Text-to-Speech:** `gTTS` (Google Text-to-Speech)
- **AI Inference:** Hugging Face API (`gpt2` or custom LLM fallback)

---

## ⚙️ Setup and Installation

### 1. Clone the Repository
```bash
git clone https://github.com/RangaswamyChalla/vibot.git
cd vibot
```

### 2. Install Dependencies
Make sure you have Python 3.8+ installed. Using a virtual environment is recommended.
```bash
python -m venv venv
source venv/bin/activate  # On Windows use: .\venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Environment Variables
To enable the AI Fallback via Hugging Face, register for a free token.
```bash
# Create your configuration file
cp .env.example .env
```
Edit the `.env` file and insert:
```
HF_API_TOKEN=your_hugging_face_token_here
```

### 4. Run the Application
```bash
streamlit run main.py
```
*The app will automatically pop up in your default web browser.*

---

## 💡 Usage

ViBot is specially programmed to answer core professional questions. Try asking:

* **"What is your life story?"**
* **"What is your #1 superpower?"**
* **"What are the top 3 areas you'd like to grow in?"**
* **"What misconception do your coworkers have about you?"**
* **"How do you push your boundaries?"**
* **"Tell me about yourself" (Resume summary)**

If an unknown query is asked, the bot will intelligently try to rely on HuggingFace for an AI-generated fallback response.

---

> *"I deliberately take on projects or tasks that challenge me, forcing me to learn new skills, think differently, and step outside my comfort zone." — Ranga Swami*
