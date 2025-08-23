from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import os, json
import logging

from app.routers import actions, dashboard
from app.routers.predict_simple import router as predict_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="NEUROSHIELD Backend")

# Include routers
app.include_router(predict_router)
app.include_router(dashboard.router)
app.include_router(actions.router)

# Simple test endpoint
@app.get("/")
async def root():
    return {"message": "NEUROSHIELD Backend is running"}

@app.get("/health")
async def health():
    return {"status": "healthy", "message": "Backend is operational"}

# ✅ Define the Router Log Schema
class RouterLog(BaseModel):
    Timestamp: str
    Device_Name: str = Field(..., alias="Device Name")
    Source_IP: str = Field(..., alias="Source IP")
    Destination_IP: str = Field(..., alias="Destination IP")
    Traffic_Volume: float = Field(..., alias="Traffic Volume (MB/s)")
    Latency: float = Field(..., alias="Latency (ms)")
    Bandwidth_Allocated: float = Field(..., alias="Bandwidth Allocated (MB/s)")
    Bandwidth_Used: float = Field(..., alias="Bandwidth Used (MB/s)")
    Congestion_Flag: str = Field(..., alias="Congestion Flag")  # "Yes"/"No"
    Log_Text: Optional[str] = Field(None, alias="Log Text")

@app.post("/api/ingest")
async def ingest(logs: list[RouterLog]):
    """
    Ingests a batch of router logs.
    """
    try:
        # Convert validated logs into dicts with original field names
        payloads = [log.dict(by_alias=True) for log in logs]
        
        # For now, just return success without Redis
        return {"status": "received", "items": len(payloads), "message": "Logs received successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

