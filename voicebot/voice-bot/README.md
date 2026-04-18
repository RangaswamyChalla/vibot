# Voice Bot Project

This project is a voice bot application built using Streamlit, designed to respond to user queries using ChatGPT's API or any other free alternative. The bot can handle audio input, transcribe it to text, and generate responses based on predefined questions and answers.

## Project Structure

```
voice-bot
├── src
│   ├── main.py          # Entry point of the application
│   ├── config.py        # Configuration settings and environment variables
│   ├── chatbot.py       # Chatbot logic and API interaction
│   ├── audio_handler.py  # Audio recording and processing
│   └── utils.py         # Utility functions for various tasks
├── data
│   └── responses.json    # Predefined responses for specific questions
├── requirements.txt      # Project dependencies
├── .env.example          # Template for environment variables
├── .streamlit
│   └── config.toml      # Streamlit configuration settings
└── README.md             # Project documentation
```

## Setup Instructions

1. **Clone the Repository**
   ```bash
   git clone <repository-url>
   cd voice-bot
   ```

2. **Create a Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**
   - Copy `.env.example` to `.env` and fill in the required API keys and settings.

5. **Run the Application**
   ```bash
   streamlit run src/main.py
   ```

## Usage Guidelines

- Once the application is running, you can interact with the voice bot by asking questions.
- The bot is designed to respond to specific queries, such as:
  - What should we know about your life story in a few sentences?
  - What’s your #1 superpower?
  - What are the top 3 areas you’d like to grow in?
  - What misconception do your coworkers have about you?
  - How do you push your boundaries and limits?

## Features

- Voice input for user queries.
- Transcription of audio to text.
- Responses generated using ChatGPT's API or predefined responses.
- User-friendly interface built with Streamlit.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any enhancements or bug fixes.

## License

This project is licensed under the MIT License. See the LICENSE file for details.