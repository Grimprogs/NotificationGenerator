import requests
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

res = requests.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}")
data = res.json()

for model in data.get("models", []):
    print(model["name"], "-", model.get("supportedGenerationMethods", []))
