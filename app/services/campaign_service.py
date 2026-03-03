import csv
import io
import os
import logging
from typing import List, Dict
from dotenv import load_dotenv
from twilio.rest import Client

load_dotenv()
logger = logging.getLogger("aditi.campaign")

class CampaignService:
    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.from_number = os.getenv("TWILIO_PHONE_NUMBER")
        self.tunnel_url = os.getenv("TUNNEL_URL") 
        
        if self.account_sid and self.auth_token:
            self.client = Client(self.account_sid, self.auth_token)
        else:
            logger.warning("Twilio credentials missing. Campaign service will not make real calls.")
            self.client = None

    async def parse_csv(self, file_content: bytes) -> List[Dict]:
        """
        Parses CSV content and extracts 'name' and 'phone' columns.
        Returns a list of dicts: {'name': '...', 'phone': '...'}
        """
        decoded_content = file_content.decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(decoded_content))
        
        contacts = []
        for row in csv_reader:
            # Normalize keys to lowercase to be flexible
            row_lower = {k.lower(): v for k, v in row.items()}
            
            name = row_lower.get('name') or row_lower.get('student name') or "Student"
            phone = row_lower.get('phone') or row_lower.get('mobile') or row_lower.get('number')
            
            if phone:
                # Basic validation/cleanup could happen here
                contacts.append({"name": name, "phone": phone})
        
        return contacts

    async def start_campaign(self, contacts: List[Dict]) -> Dict:
        """
        Triggers outbound calls for a list of contacts.
        """
        if not self.client:
            return {"status": "error", "message": "Twilio client not initialized"}
        
        if not self.tunnel_url:
             return {"status": "error", "message": "TUNNEL_URL not found in environment"}

        results = {"total": len(contacts), "queued": 0, "failed": 0, "details": []}

        for contact in contacts:
            try:
                # Webhook URL for the agent to handle the call
                # We append header info if needed, or just rely on standard flow
                # For simplicity, we point to /voice
                
                # NOTE: In a real campaign, we might pass custom params in the URL query string
                # e.g. /voice?name=Rahul
                
                webhook_url = f"{self.tunnel_url}/voice"
                
                call = self.client.calls.create(
                    to=contact['phone'],
                    from_=self.from_number,
                    url=webhook_url,
                    method="POST"
                )
                
                results["queued"] += 1
                results["details"].append({"phone": contact['phone'], "status": "queued", "sid": call.sid})
                logger.info(f"Queued call to {contact['phone']} (SID: {call.sid})")
                
            except Exception as e:
                results["failed"] += 1
                results["details"].append({"phone": contact['phone'], "status": "failed", "error": str(e)})
                logger.error(f"Failed to call {contact['phone']}: {e}")
                
        return results

campaign_service = CampaignService()
