
import os
from twilio.rest import Client
from dotenv import load_dotenv
import sys

load_dotenv()

sid = sys.argv[1] if len(sys.argv) > 1 else None

if not sid:
    print("Usage: python check_call_status.py <SID>")
    sys.exit(1)

try:
    client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))
    call = client.calls(sid).fetch()
    print(f"Call SID: {sid}")
    print(f"Status: {call.status}")
    print(f"Duration: {call.duration}")
    print(f"To: {call.to}")
except Exception as e:
    print(f"Error: {e}")
