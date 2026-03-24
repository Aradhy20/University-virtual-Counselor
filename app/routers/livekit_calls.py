from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import random
import json
from livekit import api
import logging

logger = logging.getLogger("riya.api.livekit")
router = APIRouter(prefix="/livekit", tags=["LiveKit Voice Agent"])

class LiveKitCallRequest(BaseModel):
    phone: str

@router.post("/call")
async def make_livekit_call(request: LiveKitCallRequest):
    """
    Trigger an outbound call using the LiveKit Voice Agent.
    Requires the agent process to be running separately (`python agent.py start`).
    """
    phone_number = request.phone.strip()
    if not phone_number.startswith("+"):
        raise HTTPException(status_code=400, detail="Phone number must start with '+' and country code.")

    url = os.getenv("LIVEKIT_URL")
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")

    if not (url and api_key and api_secret):
        logger.error("LiveKit credentials missing in environment.")
        raise HTTPException(status_code=500, detail="LiveKit credentials missing in environment.")

    lk_api = api.LiveKitAPI(url=url, api_key=api_key, api_secret=api_secret)

    # Create a unique room for this call
    room_name = f"call-{phone_number.replace('+', '')}-{random.randint(1000, 9999)}"
    logger.info(f"Initiating call to {phone_number} in room {room_name}...")

    try:
        dispatch_request = api.CreateAgentDispatchRequest(
            agent_name="outbound-caller", # Must match agent.py
            room=room_name,
            metadata=json.dumps({"phone_number": phone_number})
        )
        dispatch = await lk_api.agent_dispatch.create_dispatch(dispatch_request)
        
        logger.info(f"✅ Call Dispatched Successfully! Dispatch ID: {dispatch.id}")
        return {
            "status": "success",
            "message": f"Call Dispatched to {phone_number}",
            "room": room_name,
            "dispatch_id": dispatch.id
        }
    except Exception as e:
        logger.error(f"Error dispatching LiveKit call: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error dispatching call: {str(e)}")
    finally:
        await lk_api.aclose()
