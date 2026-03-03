import inspect
from deepgram import DeepgramClient

def probe():
    print("--- Deepgram SDK Probe ---")
    try:
        c = DeepgramClient(api_key="test")
        print(f"Client: {c}")
        print(f"Client dir: {[m for m in dir(c) if not m.startswith('_')]}")
        
        if hasattr(c, "listen"):
            print(f"\nListen: {c.listen}")
            print(f"Listen dir: {[m for m in dir(c.listen) if not m.startswith('_')]}")
            
            if hasattr(c.listen, "live"):
                print(f"\nListen.live: {c.listen.live}")
                print(f"Listen.live dir: {[m for m in dir(c.listen.live) if not m.startswith('_')]}")
            else:
                print("\n[WARN] Listen.live MISSING")

            if hasattr(c.listen, "v1"):
                print(f"\nListen.v1: {c.listen.v1}")
                print(f"Listen.v1 dir: {[m for m in dir(c.listen.v1) if not m.startswith('_')]}")
            
            if hasattr(c.listen, "websocket"):
                 print(f"\nListen.websocket FOUND!")
            else:
                 print("\n[WARN] Listen.websocket MISSING")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    probe()
