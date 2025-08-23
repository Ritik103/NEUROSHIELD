from fastapi import FastAPI, Request, HTTPException, WebSocket
from pydantic import BaseModel, Field
from typing import Optional
import redis.asyncio as redis
import os, json
import asyncio
import logging
from contextlib import asynccontextmanager

from app.routers import actions, predict, dashboard
from app.ws import websocket_endpoint

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting NEUROSHIELD Backend...")
    
                # Initialize services
            try:
                from app.services.broadcaster import initialize_broadcaster
                from app.services.network_automation import initialize_automation_service
                from app.services.redis_processor import initialize_redis_processor
                
                await initialize_broadcaster()
                await initialize_automation_service()
                await initialize_redis_processor()
                logger.info("All services initialized successfully")
            except Exception as e:
                logger.error(f"Error initializing services: {e}")
    
    yield
    
                # Shutdown
            logger.info("Shutting down NEUROSHIELD Backend...")
            try:
                from app.services.broadcaster import broadcaster
                from app.services.network_automation import automation_service
                from app.services.redis_processor import stop_redis_processor
                
                await broadcaster.stop()
                await automation_service.stop()
                await stop_redis_processor()
                logger.info("All services stopped")
            except Exception as e:
                logger.error(f"Error stopping services: {e}")

app = FastAPI(title="NEUROSHIELD Backend", lifespan=lifespan)

# Include routers
app.include_router(actions.router)
app.include_router(predict.router)
app.include_router(dashboard.router)

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_main(websocket: WebSocket):
    await websocket_endpoint(websocket)

# Redis config
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
QUEUE_KEY = os.getenv("QUEUE_KEY", "telegraf:metrics")
r = redis.from_url(REDIS_URL, decode_responses=True)


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
        # Convert validated logs into dicts with original field names
        payloads = [log.dict(by_alias=True) for log in logs]
        for p in payloads:
            await r.rpush(QUEUE_KEY, json.dumps(p))
        return {"status": "queued", "items": len(payloads)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))