from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import redis.asyncio as redis
import os, json

app = FastAPI(title="SmartNet Backend")

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