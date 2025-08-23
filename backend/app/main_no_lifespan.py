from fastapi import FastAPI, Request, HTTPException, WebSocket
from pydantic import BaseModel, Field
from typing import Optional
import redis.asyncio as redis
import os, json
import logging

from app.routers import actions, predict, dashboard
from app.ws import websocket_endpoint

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app WITHOUT lifespan
app = FastAPI(title="NEUROSHIELD Backend")

# Include routers
app.include_router(actions.router)
app.include_router(predict.router)
app.include_router(dashboard.router)

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_main(websocket: WebSocket):
    await websocket_endpoint(websocket)

# Simple test endpoint
@app.get("/")
async def root():
    return {"message": "NEUROSHIELD Backend is running"}

@app.get("/health")
async def health():
    return {"status": "healthy", "message": "Backend is operational"}

# Redis config
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
QUEUE_KEY = os.getenv("QUEUE_KEY", "telegraf:metrics")

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

