"""Test calls to both numbers."""
import os
from dotenv import load_dotenv
from twilio.rest import Client

load_dotenv()

client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))
TWILIO_PHONE = os.getenv("TWILIO_PHONE_NUMBER")
TUNNEL_URL = os.getenv("TUNNEL_URL", "https://attractions-incomplete-lines-usually.trycloudflare.com")


for number in ["+917351522153"]:
    try:
        call = client.calls.create(
            to=number, from_=TWILIO_PHONE,
            url=f"{TUNNEL_URL}/voice", method="POST",
        )
        print(f"OK  {number} | SID: {call.sid}")
    except Exception as e:
        print(f"ERR {number} | {e}")
