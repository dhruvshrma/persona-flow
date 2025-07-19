#!/usr/bin/env python3
"""
Orchestrator Service Entry Point
"""
import uvicorn
from app.orchestrator import app

if __name__ == "__main__":
    # For local development
    uvicorn.run(app, host="0.0.0.0", port=8002, reload=True)
else:
    # For production/Cloud Run
    # This module will be imported by uvicorn
    pass