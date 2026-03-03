import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

def transcribe_audio(file_path):
    print(f"Transcribing: {file_path}")
    dg_key = os.getenv("DEEPGRAM_API_KEY")
    if not dg_key:
        print("ERROR: DEEPGRAM_API_KEY not found in env.")
        return
        
    url = "https://api.deepgram.com/v1/listen?model=nova-2&smart_format=true"
    headers = {
        "Authorization": f"Token {dg_key}",
        "Content-Type": "audio/mpeg"
    }
    
    with open(file_path, "rb") as audio:
        response = requests.post(url, headers=headers, data=audio)
    
    if response.status_code == 200:
        transcript = response.json()["results"]["channels"][0]["alternatives"][0]["transcript"]
        print("\n--- TRANSCRIPT ---")
        print(transcript)
        print("------------------\n")
    else:
        print(f"Failed: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    transcribe_audio(r"c:\tmu\university_counselor\International Call-2603021652.mp3.mpeg")
