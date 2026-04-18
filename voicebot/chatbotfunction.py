from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise Exception("OPENAI_API_KEY is missing. Create .env file!")

client = OpenAI(api_key=api_key)


def speech_to_text_conversion(file_path):

    """Converts audio format message to text using OpenAI's Whisper model."""
    audio_file= open(file_path, "rb") # Opening the audio file in binary read mode
    transcription = client.audio.transcriptions.create(
    model="whisper-1",  # Model to use for transcription
    
    file=audio_file  # Audio file to transcribe
    )
    return transcription.text


def text_chat(text):
    # Generate response using OpenAI
    response = client.chat.completions.create(
        model= "gpt-3.5-turbo",
        messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Who won the world series in 2020?"},
        {"role": "assistant", "content": "The Los Angeles Dodgers won the World Series in 2020."},
        {"role": "user", "content": text}
        ])
    return response.choices[0].message.content

def text_to_speech_conversion(text):
    """Converts text to audio format message using OpenAI's text-to-speech model - tts-1."""
    if text:  # Check if converted_text is not empty
        speech_file_path = datetime.datetime.now().strftime("%Y%m%d%H%M%S") + "_speech.webm"
        # print("path--------->")
        response = client.audio.speech.create(
        model="tts-1",# Model to use for text-to-speech conversion
        voice="fable",# Voice to use for speech synthesis
        input=text #Text to convert to speech
        )
        '''response is binary data, when using strean_to_file function, it will write the binary data in a file'''
        response.stream_to_file(speech_file_path) # Streaming synthesized speech to file
        #Read the audio file as binary data
        with open(speech_file_path, "rb") as audio_file:
            audio_data = audio_file.read()
        os.remove(speech_file_path)
        return audio_data
    else:
        print("Error: converted_text is empty")