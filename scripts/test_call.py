import os
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

# Get credentials from .env
account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
twilio_number = os.getenv("TWILIO_PHONE_NUMBER")

# Get the live Cloudflare tunnel URL updated by start_and_update_tunnel.py
TUNNEL_URL = os.getenv("TUNNEL_URL")
if not TUNNEL_URL:
    print("[ERROR] TUNNEL_URL missing from .env! Run start_and_update_tunnel.py first.")
    exit(1)

client = Client(account_sid, auth_token)

print("[INFO] Initiating test call to +917351522153...")
print(f"[INFO] Using webhook: {TUNNEL_URL}/voice")

try:
    call = client.calls.create(
        url=f"{TUNNEL_URL}/voice",  # Your AI agent endpoint
        to="+917351522153",
        from_=twilio_number
    )
    
    print(f"[SUCCESS] Call initiated!")
    print(f"[INFO] Call SID: {call.sid}")
    print(f"[INFO] Status: {call.status}")
    print(f"[INFO] The phone should ring shortly...")
    
except Exception as e:
    print(f"[ERROR] Failed to initiate call: {e}")
