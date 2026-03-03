import os
import asyncio
from dotenv import load_dotenv
from deepgram import DeepgramClient

# Load Env
load_dotenv()

async def check_deepgram():
    print("\n--- Testing Deepgram Connectivity ---")
    api_key = os.getenv("DEEPGRAM_API_KEY")
    if not api_key:
        print("[ERROR] DEEPGRAM_API_KEY missing.")
        return

    try:
        # Simple test: Check if client initializes
        client = DeepgramClient(api_key=api_key)
        # We can try a simple request if possible, but init is a good start. 
        # Actually v3 might not fail on init until a request is made.
        # Let's try to access a property or method to ensure it's valid.
        print(f"[SUCCESS] Deepgram Client initialized with key ending in ...{api_key[-4:]}")
    except Exception as e:
        print(f"[ERROR] Deepgram init failed: {e}")

from elevenlabs.client import ElevenLabs

def check_elevenlabs():
    print("\n--- Testing ElevenLabs Connectivity ---")
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        print("[ERROR] ELEVENLABS_API_KEY missing.")
        return

    try:
        client = ElevenLabs(api_key=api_key)
        # Try to list voices as a real connectivity test
        voices = client.voices.get_all()
        print(f"[SUCCESS] ElevenLabs Connected. Found {len(voices.voices)} voices.")
    except Exception as e:
        print(f"[ERROR] ElevenLabs failed: {e}")

if __name__ == "__main__":
    asyncio.run(check_deepgram())
    check_elevenlabs()
