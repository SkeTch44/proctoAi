
import os
import sys
from dotenv import load_dotenv
import google.generativeai as genai

# Load env vars
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("No API Key found")
    sys.exit(1)

print(f"Using API Key: {api_key[:5]}...")

try:
    genai.configure(api_key=api_key)
    print("Listing models...")
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name}")
except Exception as e:
    print(f"Error listing models: {e}")
