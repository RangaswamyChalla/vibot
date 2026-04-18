import os
import json
from openai import OpenAI
from openai.error import OpenAIError

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Initialize OpenAI client
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# Load predefined responses
def load_responses(file_path):
    with open(file_path, 'r') as f:
        return json.load(f)

# Get response from ChatGPT or predefined responses
def get_chatbot_response(user_input):
    if client:
        try:
            response = client.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": user_input}]
            )
            return response.choices[0].message.content
        except OpenAIError as e:
            return f"Error communicating with OpenAI: {e}"
    else:
        responses = load_responses("data/responses.json")
        return responses.get(user_input, "I'm not sure how to respond to that.")