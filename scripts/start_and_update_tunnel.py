"""
Starts cloudflared tunnel + auto-updates Twilio webhook and .env TUNNEL_URL.
Run this instead of manually starting the tunnel.
"""
import subprocess
import re
import os
import time
import sys
from dotenv import load_dotenv, set_key

load_dotenv()

ENV_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
CLOUDFLARED = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cloudflared.exe")

def update_twilio_webhook(tunnel_url: str):
    """Update the Twilio phone number webhook to the new tunnel URL."""
    try:
        from twilio.rest import Client
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        phone_number = os.getenv("TWILIO_PHONE_NUMBER")
        
        if not (account_sid and auth_token and phone_number):
            print("[WARN] Twilio creds missing — skipping webhook update")
            return
        
        client = Client(account_sid, auth_token)
        numbers = client.incoming_phone_numbers.list(phone_number=phone_number)
        
        if numbers:
            voice_url = f"{tunnel_url}/voice"
            numbers[0].update(voice_url=voice_url, voice_method="POST")
            print(f"[OK] Twilio webhook updated: {voice_url}")
        else:
            print(f"[WARN] Twilio number {phone_number} not found")
    except Exception as e:
        print(f"[ERR] Failed to update Twilio webhook: {e}")

def main():
    if not os.path.exists(CLOUDFLARED):
        print("[ERR] cloudflared.exe not found! Run from project root.")
        sys.exit(1)

    print("[INFO] Starting cloudflared tunnel...")
    proc = subprocess.Popen(
        [CLOUDFLARED, "tunnel", "--url", "http://localhost:8005"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    tunnel_url = None
    print("[INFO] Waiting for tunnel URL...")
    
    for line in proc.stdout:
        line_stripped = line.strip()
        print(line_stripped)
        
        # Cloudflare prints the URL in the logs
        match = re.search(r'https://[a-z0-9\-]+\.trycloudflare\.com', line_stripped)
        if match and not tunnel_url:
            tunnel_url = match.group(0)
            print(f"\n{'='*50}")
            print(f"  TUNNEL URL: {tunnel_url}")
            print(f"{'='*50}\n")
            
            # Update .env
            set_key(ENV_FILE, "TUNNEL_URL", tunnel_url)
            print(f"[OK] .env TUNNEL_URL updated")
            
            # Update Twilio webhook
            update_twilio_webhook(tunnel_url)
            
            print(f"\n[READY] Backend is live at: {tunnel_url}")
            print(f"[READY] Voice webhook: {tunnel_url}/voice")
            print("[INFO] Keep this window open. Press Ctrl+C to stop.\n")

    proc.wait()

if __name__ == "__main__":
    main()
