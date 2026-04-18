def text_to_speech(text, filename):
    from gtts import gTTS
    import os

    tts = gTTS(text=text, lang='en')
    tts.save(filename)
    return filename

def load_json(file_path):
    import json

    with open(file_path, 'r') as f:
        return json.load(f)

def handle_error(error):
    import logging

    logging.error(f"An error occurred: {error}")
    return str(error)