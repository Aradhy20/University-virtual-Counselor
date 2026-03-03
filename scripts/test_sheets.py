
import os
import sys
from pathlib import Path
import gspread

# Add project root
sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

def test_sheets():
    creds_file = "d:/tmu/university_counselor/google_credentials.json"
    sheet_id = "1qinO_9LGC4SBFubrIlq88HQIO72QaeCJzLEx7x_EirA" # Hardcoded user ID

    if not os.path.exists(creds_file):
        print(f"[FAIL] Credentials file not found at: {creds_file}")
        return

    print(f"[INFO] Found credentials at: {creds_file}")
    
    try:
        print("[INFO] Attempting to authenticate...")
        client = gspread.service_account(filename=creds_file)
        
        print(f"[INFO] Attempting to open sheet: {sheet_id}")
        sheet = client.open_by_key(sheet_id).sheet1
        
        print(f"[SUCCESS] Connected to Sheet: {sheet.title}")
        print(f"[INFO] Current Row Count: {len(sheet.get_all_values())}")
        
    except Exception as e:
        print(f"[ERROR] Connection Failed: {e}")
        # Print file content preview if it looks like invalid JSON
        try:
            with open(creds_file, "r") as f:
                content = f.read(100)
                print(f"[DEBUG] File start: {content}...")
        except:
            pass

if __name__ == "__main__":
    test_sheets()
