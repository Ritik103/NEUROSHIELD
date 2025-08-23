from fastapi import FastAPI, Request
import os, json
import redis.asyncio as redis

app = FastAPI(title="SmartNet Backend")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
QUEUE_KEY = os.getenv("QUEUE_KEY", "telegraf:metrics")

r = redis.from_url(REDIS_URL, decode_responses=True)

@app.post("/api/ingest")
async def ingest(request: Request):
    # Telegraf will POST JSON; we push it straight into Redis
    payload = await request.json()
    # Telegraf can send one metric or a list of metrics; store uniformly as JSON string
    await r.rpush(QUEUE_KEY, json.dumps(payload))
    return {"status": "queued", "items": (len(payload) if isinstance(payload, list) else 1)}
