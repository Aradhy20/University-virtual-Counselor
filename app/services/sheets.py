
import os
import logging
try:
    import gspread
    GSPREAD_AVAILABLE = True
except ImportError:
    gspread = None
    GSPREAD_AVAILABLE = False
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("aditi.sheets")

class GoogleSheetService:
    def __init__(self):
        self.creds_file = os.getenv("GOOGLE_CREDS_JSON", "google_credentials.json")
        self.sheet_id = os.getenv("GOOGLE_SHEET_ID")
        self.client = None
        self.sheet = None
        
        self._connect()

    def _connect(self):
        try:
            if not GSPREAD_AVAILABLE:
                logger.warning("gspread not installed. Google Sheets disabled.")
                return
            if not os.path.exists(self.creds_file):
                logger.warning(f"Google Creds file not found at {self.creds_file}. Sheets Disabled.")
                return
            if not self.sheet_id:
                logger.warning("GOOGLE_SHEET_ID not set in .env. Sheets Disabled.")
                return

            self.client = gspread.service_account(filename=self.creds_file)
            self.sheet = self.client.open_by_key(self.sheet_id).sheet1
            logger.info("Connected to Google Sheets successfully.")
            
        except Exception as e:
            logger.error(f"Google Sheets Connection Failed: {e}")

    def add_lead(self, phone: str, name: str = "", course: str = "", city: str = ""):
        """Appends a lead to the sheet."""
        if not self.sheet:
            logger.warning("Google Sheets not active. Skipping save.")
            return

        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            row = [timestamp, phone, name or "Unknown", course or "Unknown", city or "Unknown", "Pending"]
            self.sheet.append_row(row)
            logger.info(f"Lead saved to Google Sheet: {row}")
        except Exception as e:
            logger.error(f"Failed to append row to sheet: {e}")

# Global Instance
sheet_service = GoogleSheetService()
