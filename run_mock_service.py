#!/usr/bin/env python3
"""
Quick starter script for the mock service
"""
import uvicorn

if __name__ == "__main__":
    print("🚀 Starting Mock API Service with strategic flaws...")
    print("📍 Service will be available at: http://localhost:8001")
    print("📋 API docs at: http://localhost:8001/docs")
    print("💡 See log_mock_service.md for endpoint documentation")
    
    uvicorn.run(
        "src.mock_service.app:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )