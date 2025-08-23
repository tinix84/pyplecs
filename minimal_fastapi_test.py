#!/usr/bin/env python3
"""
Minimal FastAPI test to verify the server works
"""

from fastapi import FastAPI
import uvicorn

app = FastAPI(title="Simple Test API")

@app.get("/")
async def root():
    return {"message": "Hello World", "status": "working"}

@app.get("/health")
async def health():
    return {"status": "healthy", "message": "API is working"}

@app.get("/test")
async def test():
    return {"message": "This is a test endpoint", "data": [1, 2, 3, 4, 5]}

if __name__ == "__main__":
    print("🚀 Starting minimal FastAPI test server...")
    print("📍 API will be available at: http://127.0.0.1:8003")
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8003,
        log_level="info"
    )
