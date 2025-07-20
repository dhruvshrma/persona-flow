#!/usr/bin/env python3
"""
Mock API Service Entry Point
"""
import uvicorn
from app.api import app
from fastapi.staticfiles import StaticFiles

app.mount("/ui", StaticFiles(directory="mock-ui", html=True), name="ui")

if __name__ == "__main__":
    # For local development
    uvicorn.run("server:app", host="0.0.0.0", port=8001, reload=True)
else:
    # For production/Cloud Run
    # This module will be imported by uvicorn
    pass
