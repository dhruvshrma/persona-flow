"""
LLM Service - GPU-powered model for persona generation
"""
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict, Any

app = FastAPI(
    title="PersonaFlow LLM Service",
    description="GPU-powered LLM for persona generation",
)


class PersonaRequest(BaseModel):
    context: str
    count: int = 3


class AgentRequest(BaseModel):
    persona: Dict[str, Any]
    context: str
    goal: str


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "llm-service",
        "model": "gemma3:1b",  # Will integrate with your ollama backend
        "gpu_available": True,
    }


@app.post("/generate/personas")
async def generate_personas(request: PersonaRequest):
    # TODO: Integrate with your existing ollama-backend
    # For now, return mock personas
    return {
        "personas": [
            {
                "name": "Emma",
                "background": "Art student, first time buying textbooks online",
                "technical_skill": "Beginner",
                "primary_motivation": "price",
            },
            {
                "name": "Marcus",
                "background": "Computer Science major, API-savvy developer",
                "technical_skill": "Expert",
                "primary_motivation": "efficiency",
            },
            {
                "name": "Sarah",
                "background": "Budget-conscious graduate student",
                "technical_skill": "Intermediate",
                "primary_motivation": "value",
            },
        ],
        "status": "mock_implementation",
    }


@app.post("/generate/agent_decision")
async def generate_agent_decision(request: AgentRequest):
    # TODO: Integrate with your existing ollama-backend
    return {
        "thought": "I need to find affordable textbooks for my classes",
        "api_call": "GET /products?category=textbooks&max_price=50",
        "expected_outcome": "List of affordable textbooks",
        "status": "mock_implementation",
    }
