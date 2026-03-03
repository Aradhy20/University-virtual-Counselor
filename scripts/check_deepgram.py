import deepgram
print(f"Deepgram SDK Version: {deepgram.__version__}")
print("Dir(deepgram):", dir(deepgram))

try:
    from deepgram import LiveOptions
    print("SUCCESS: from deepgram import LiveOptions")
except ImportError as e:
    print(f"ERROR: {e}")
    try:
        from deepgram.clients.live.v1 import LiveOptions
        print("SUCCESS 2: from deepgram.clients.live.v1 import LiveOptions")
    except ImportError as e2:
        print(f"ERROR 2: {e2}")

