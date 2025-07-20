"""
Orchestrator Service - Coordinates persona testing
"""
from fastapi import FastAPI
import os

app = FastAPI(
    title="PersonaFlow Orchestrator", description="Coordinates AI persona testing"
)

# Service URLs from environment
MOCK_API_URL = os.getenv("MOCK_API_URL", "http://localhost:8001")
LLM_SERVICE_URL = os.getenv("LLM_SERVICE_URL", "http://localhost:8003")


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "orchestrator",
        "mock_api_url": MOCK_API_URL,
        "llm_service_url": LLM_SERVICE_URL,
    }


@app.get("/")
async def root():
    return {
        "message": "PersonaFlow Orchestrator",
        "description": "Coordinates AI personas testing APIs",
        "endpoints": {
            "health": "/health",
            "generate_personas": "/personas/generate",
            "run_test": "/test/run",
        },
    }


@app.post("/personas/generate")
async def generate_personas():
    # TODO: Call LLM service to generate personas
    return {"message": "Persona generation endpoint", "status": "not_implemented_yet"}


@app.post("/test/run")
async def run_test():
    # TODO: Coordinate testing between personas and mock API
    return {"message": "Test execution endpoint", "status": "not_implemented_yet"}
