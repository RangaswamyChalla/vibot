FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    espeak-ng \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY voice-bot/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Create data directories
RUN mkdir -p voice-bot/data voice-bot/conversations

# Expose ports (FastAPI and Streamlit)
EXPOSE 8000
EXPOSE 8501

# Default command for API
CMD ["uvicorn", "voice-bot.src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
