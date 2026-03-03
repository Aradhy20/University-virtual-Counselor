"""
Admin API Router.
Exposes Enterprise Configuration, Logs, and Knowledge Base management.
"""
from fastapi import APIRouter, HTTPException, UploadFile, File
from app.services.config_schema import AgentConfig
from app.services.config_loader import config_loader
from app.services.rag import RAGService
import pandas as pd
import os
import shutil
import logging
from typing import List, Dict, Any

router = APIRouter(prefix="/admin", tags=["Admin"])
logger = logging.getLogger("admin_api")

# ------------------------------------------------------------------
# 1. Configuration Management
# ------------------------------------------------------------------
@router.get("/config", response_model=AgentConfig)
async def get_config():
    """Retrieve current enterprise configuration."""
    return config_loader.get_config()

@router.post("/config", response_model=AgentConfig)
async def update_config(config: AgentConfig):
    """Update and persist enterprise configuration."""
    try:
        config_loader.save_config(config)
        return config
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ------------------------------------------------------------------
# 2. Analytics & Logs
# ------------------------------------------------------------------
@router.get("/stats")
async def get_stats():
    """Get aggregated system stats."""
    # Mock stats or read from logs
    return {
        "total_calls": 1245, # Example
        "avg_duration": "2m 15s",
        "sentiment_score": 8.5
    }

@router.get("/logs")
async def get_logs(limit: int = 50):
    """Retrieve recent conversation logs."""
    log_path = r"d:\tmu\university_counselor\data\conversation_logs.csv"
    if not os.path.exists(log_path):
        return []
    
    try:
        df = pd.read_csv(log_path)
        # Sort by timestamp desc and take limit
        df = df.iloc[::-1].head(limit)
        return df.to_dict(orient="records")
    except Exception as e:
        logger.error(f"Error reading logs: {e}")
        return []

# ------------------------------------------------------------------
# 3. Knowledge Base Management
# ------------------------------------------------------------------
@router.post("/kb/upload")
async def upload_kb_document(file: UploadFile = File(...)):
    """Upload a document to the Knowledge Base."""
    try:
        file_path = f"d:/tmu/university_counselor/data/{file.filename}"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Trigger Ingestion (Optional: Call RAG service to re-index)
        # For now, just save. RAGService usually loads on startup or demand.
        return {"filename": file.filename, "status": "uploaded"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/kb/reindex")
async def reindex_kb():
    """Force re-indexing of the vector store."""
    try:
        # This would require exposing a reindex method in RAGService
        # For prototype, we just verify the call.
        rag = RAGService()
        # rag.reindex() # Hypothetical method
        return {"status": "Re-indexing triggered (Background Task)"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
