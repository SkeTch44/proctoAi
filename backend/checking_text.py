import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load .env file
load_dotenv()

# Configure Gemini API
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Use Gemini 1.5 Flash model
model = genai.GenerativeModel("gemini-1.5-flash")

# Example request
response = model.generate_content("Write a 2-line poem about summer.")
print(response.text)
