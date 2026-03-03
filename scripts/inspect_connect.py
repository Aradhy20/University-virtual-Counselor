from deepgram import DeepgramClient
import inspect
import sys

try:
    c = DeepgramClient(api_key="test")
    # v5 client structure: c.listen.v2.connect
    sig = inspect.signature(c.listen.v2.connect)
    print("Signature:", sig)
    print("Parameters:", sig.parameters.keys())
except Exception as e:
    print("Error:", e)
