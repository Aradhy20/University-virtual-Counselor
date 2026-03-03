"""Transcribe a call recording using Deepgram pre-recorded API."""
import os
import sys
import json
import httpx
from pathlib import Path
from dotenv import load_dotenv

sys.path.append(str(Path(__file__).parent.parent))
load_dotenv()

api_key = os.getenv("DEEPGRAM_API_KEY")
audio_path = r"d:\tmu\university_counselor\WhatsApp Audio 2026-02-16 at 4.26.55 PM.mpeg"

with open(audio_path, "rb") as f:
    audio_data = f.read()

print(f"Audio file size: {len(audio_data)} bytes")

url = "https://api.deepgram.com/v1/listen"
params = {
    "model": "nova-2",
    "language": "en-IN",
    "smart_format": "true",
    "punctuate": "true",
    "diarize": "true",
    "utterances": "true",
}
headers = {
    "Authorization": f"Token {api_key}",
    "Content-Type": "audio/mpeg",
}

print("Sending to Deepgram for transcription...")
response = httpx.post(url, params=params, headers=headers, content=audio_data, timeout=60.0)
print(f"Status: {response.status_code}")

result = response.json()

# Save full result
with open("call_transcript.json", "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

# Print utterances with speaker labels
if "results" in result:
    utterances = result["results"].get("utterances", [])
    if utterances:
        print(f"\n=== CALL TRANSCRIPT ({len(utterances)} utterances) ===\n")
        for u in utterances:
            spk = u.get("speaker", "?")
            text = u["transcript"]
            start = round(u["start"], 1)
            print(f"[{start}s] Speaker {spk}: {text}")
    else:
        # Fallback to full transcript
        channels = result["results"].get("channels", [])
        if channels:
            transcript = channels[0]["alternatives"][0]["transcript"]
            print(f"\n=== FULL TRANSCRIPT ===\n{transcript}")
else:
    print("No results in response:")
    print(json.dumps(result, indent=2))
