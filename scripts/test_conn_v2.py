from deepgram import DeepgramClient
import os
from dotenv import load_dotenv
from websockets.exceptions import InvalidStatus

load_dotenv()

def test():
    api_key = os.getenv("DEEPGRAM_API_KEY")
    client = DeepgramClient(api_key=api_key)

    msg_options = [
        {"model": "nova-2"},
        {"model": "nova-2-general"},
        {"model": "nova"},
        {"encoding": "linear16", "sample_rate": 8000}, # Missing model?
        {"model": "nova-2", "encoding": "mulaw", "sample_rate": 8000},
    ]

    for opt in msg_options:
        print(f"\nTesting with options: {opt}")
        try:
            with client.listen.v2.connect(**opt) as conn:
                if conn.start_listening():
                     print("SUCCESS! Connected.")
                else:
                     print("FAILED start_listening")
        except InvalidStatus as e:
            print(f"FAILED with InvalidStatus: {e}")
            try:
                # e.response is likely a httpx Response or similar? No, websockets handshake response.
                # websockets.http.Response
                print(f"FAILURE DETAILS: {type(e.response)}")
                # Depending on version: .body or .content
                if hasattr(e.response, 'body'):
                    print(f"Body: {e.response.body.decode('utf-8')}")
                elif hasattr(e.response, 'content'):
                    print(f"Content: {e.response.content.decode('utf-8')}")
            except Exception as inner:
                print(f"Error reading response body: {inner}")
        except Exception as e:
            print(f"FAILED with error: {e}")

if __name__ == "__main__":
    test()
