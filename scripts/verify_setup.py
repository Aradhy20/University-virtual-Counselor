import os
import sys
from dotenv import load_dotenv
from supabase.client import create_client
from deepgram import DeepgramClient
from openai import OpenAI

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

load_dotenv()

def verify():
    print("[INFO] Verifying Setup...")
    
    # 1. Check OpenAI
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        try:
            client = OpenAI(api_key=openai_key)
            # Simple call to verify key valid
            client.models.list()
            print("[SUCCESS] OpenAI API: Connected")
        except Exception as e:
            print(f"[ERROR] OpenAI API Error: {e}")
    else:
        print("[ERROR] OpenAI API Key Missing")

    # 2. Check Supabase
    supa_url = os.getenv("SUPABASE_URL")
    supa_key = os.getenv("SUPABASE_SERVICE_KEY")
    if supa_url and supa_key:
        try:
            supabase = create_client(supa_url, supa_key)
            print("[SUCCESS] Supabase: Client Initialized")
        except Exception as e:
            print(f"[ERROR] Supabase Error: {e}")
    else:
        print("[WARN] Supabase Credentials Missing (Using FAISS)")

    # 3. Check Deepgram
    dg_key = os.getenv("DEEPGRAM_API_KEY")
    if dg_key:
        try:
            dg = DeepgramClient(api_key=dg_key)
            print("[SUCCESS] Deepgram: Client Initialized")
        except Exception as e:
            print(f"[ERROR] Deepgram Error: {e}")
    else:
        print("[ERROR] Deepgram API Key Missing")

    print("[INFO] Verification Complete!")

if __name__ == "__main__":
    verify()
