#!/usr/bin/env python3
"""
Minimal test server to isolate startup issues
"""

from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/test")
def test():
    return {"status": "ok"}

if __name__ == "__main__":
    print("Starting minimal test server on localhost:8000...")
    try:
        uvicorn.run(app, host="localhost", port=8000, log_level="info")
    except Exception as e:
        print(f"Error starting server: {e}")
        import traceback
        traceback.print_exc()

