from deepgram import DeepgramClient, LiveOptions
import os
from dotenv import load_dotenv

load_dotenv()

def test_conn():
    dg_client = DeepgramClient(os.getenv("DEEPGRAM_API_KEY"))
    try:
        # V5 syntax
        # try 1: kwds
        print("Testing connect with kwds...")
        conn = dg_client.listen.v2.connect(
             model="nova-2",
             encoding="mulaw",
             sample_rate=8000
        )
        if conn.start_listening():
             print("SUCCESS!")
             conn.finish()
        else:
             print("FAILED start")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    try:
        from deepgram import LiveOptions
        print("LiveOptions imported from top level")
    except ImportError:
        print("LiveOptions NOT at top level")
    
    test_conn()
