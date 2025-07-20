#!/usr/bin/env python3
"""
LLM Service Entry Point
"""
import uvicorn
from app.llm import app

if __name__ == "__main__":
    # For local development
    uvicorn.run(app, host="0.0.0.0", port=8003, reload=True)
else:
    # For production/Cloud Run
    # This module will be imported by uvicorn
    pass
