from fastapi import FastAPI, Request, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
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

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

# Global Redis connection (will be initialized lazily)
redis_connection = None

async def get_redis_connection():
    """Get Redis connection with error handling"""
    global redis_connection
    try:
        if redis_connection is None:
            redis_connection = redis.from_url(REDIS_URL, decode_responses=True)
            # Test connection
            await redis_connection.ping()
            logger.info("Redis connection established")
        return redis_connection
    except Exception as e:
        logger.warning(f"Redis not available: {e}")
        return None

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
    Ingests a batch of router logs into Redis.
    """
    try:
        # Get Redis connection
        r = await get_redis_connection()
        if not r:
            # Fallback: store in database directly
            from app.services.db import db_service
            payloads = [log.dict(by_alias=True) for log in logs]
            for payload in payloads:
                await db_service.add_router_log(payload)
            return {"status": "stored_directly", "items": len(payloads), "message": "Redis not available, stored in database"}
        
        # Convert validated logs into dicts with original field names
        payloads = [log.dict(by_alias=True) for log in logs]
        for p in payloads:
            await r.rpush(QUEUE_KEY, json.dumps(p))
        return {"status": "queued", "items": len(payloads)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

