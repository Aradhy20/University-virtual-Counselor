"""Update Twilio webhook to new tunnel URL and re-place the call."""
import os
from dotenv import load_dotenv
from twilio.rest import Client

load_dotenv()

TUNNEL_URL = "https://mia-arranged-casio-useful.trycloudflare.com"
ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN  = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE = os.getenv("TWILIO_PHONE_NUMBER")
TARGET_NUMBER = "+917351522153"

client = Client(ACCOUNT_SID, AUTH_TOKEN)

# 1. Update Twilio phone webhook
numbers = client.incoming_phone_numbers.list(phone_number=TWILIO_PHONE)
if numbers:
    updated = numbers[0].update(
        voice_url=f"{TUNNEL_URL}/voice",
        voice_method="POST"
    )
    print(f"[OK] Webhook updated → {TUNNEL_URL}/voice")
else:
    print("[WARN] Could not find Twilio phone number to update webhook")

# 2. Make a fresh call
call = client.calls.create(
    to=TARGET_NUMBER,
    from_=TWILIO_PHONE,
    url=f"{TUNNEL_URL}/voice",
    method="POST",
)
print(f"[OK] Call dispatched → {TARGET_NUMBER} | SID: {call.sid}")
