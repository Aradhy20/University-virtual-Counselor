from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import List, Dict
from app.services.campaign_service import campaign_service
import logging

router = APIRouter(prefix="/campaign", tags=["Campaign"])
logger = logging.getLogger("aditi.api.campaign")

class Contact(BaseModel):
    name: str = "Student"
    phone: str

class StartCampaignRequest(BaseModel):
    contacts: List[Contact]

@router.post("/upload")
async def upload_csv(file: UploadFile = File(...)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a CSV.")
    
    try:
        content = await file.read()
        contacts = await campaign_service.parse_csv(content)
        return {"contacts": contacts, "count": len(contacts)}
    except Exception as e:
        logger.error(f"Error parsing CSV: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/start")
async def start_campaign(request: StartCampaignRequest):
    contacts_dict = [c.dict() for c in request.contacts]
    result = await campaign_service.start_campaign(contacts_dict)
    return result
