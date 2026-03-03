import os
import json
import httpx
from dotenv import load_dotenv

load_dotenv()

dg_api_key = os.getenv("DEEPGRAM_API_KEY")
file_path = "WhatsApp Audio 2026-03-02 at 10.34.52 AM.mp4"

url = "https://api.deepgram.com/v1/listen?model=nova-2&smart_format=true&language=hi"
headers = {
    "Authorization": f"Token {dg_api_key}",
    "Content-Type": "video/mp4"
}

with open(file_path, "rb") as f:
    response = httpx.post(url, headers=headers, content=f.read(), timeout=120.0)

result = response.json()
with open("transcript_output.json", "w", encoding="utf-8") as out_f:
    json.dump(result, out_f, ensure_ascii=False, indent=2)

print("Transcription saved to transcript_output.json")
