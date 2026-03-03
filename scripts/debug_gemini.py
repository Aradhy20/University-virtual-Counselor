
import os
import sys
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv(r"d:\tmu\university_counselor\.env")

api_key = os.getenv("GOOGLE_API_KEY")
print(f"API Key present: {bool(api_key)}")

import google.generativeai as genai

genai.configure(api_key=api_key)

print("--- AVAILABLE MODELS ---")
sys.stdout.flush()
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"Model: {m.name}")
            sys.stdout.flush()
except Exception as e:
    print(f"Error listing models: {e}")
print("--- END MODELS ---")

# try:
#     llm = ChatGoogleGenerativeAI(
#         model="gemini-pro",
#         google_api_key=api_key
#     )
#     print("LLM Initialized")
#     res = llm.invoke("Hi")
#     print(f"Response: {res.content}")
# except Exception as e:
#     print(f"Error invoking model: {e}")

