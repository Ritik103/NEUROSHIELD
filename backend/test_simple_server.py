#!/usr/bin/env python3
"""
Simple test server to verify FastAPI functionality
"""

from fastapi import FastAPI
import uvicorn

app = FastAPI(title="Test Server")

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/test")
async def test():
    return {"status": "ok", "message": "Test endpoint working"}

if __name__ == "__main__":
    print("Starting simple test server...")
    uvicorn.run(app, host="0.0.0.0", port=8002, log_level="info")

