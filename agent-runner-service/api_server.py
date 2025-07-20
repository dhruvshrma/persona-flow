#!/usr/bin/env python3
"""
FastAPI server for PersonaFlow UI integration
Provides REST endpoints for persona generation and testing
"""
import os
import json
import uuid
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
root_dir = Path(__file__).parent.parent
dotenv_path = root_dir / ".env"
load_dotenv(dotenv_path=dotenv_path)

from app.architect import Architect, TestResult
from app.agent import Agent
from app.toolbelt import Toolbelt
from app.clients import LLMServiceClient
from app.personas import Persona

# FastAPI app
app = FastAPI(
    title="PersonaFlow API",
    description="AI-Powered API Testing with Personas",
    version="1.0.0"
)

# CORS middleware for UI integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific UI domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response Models
class PersonaRequest(BaseModel):
    market_segment: str
    num_personas: int = 3

class PersonaResponse(BaseModel):
    name: str
    system_prompt: str

class TestRequest(BaseModel):
    personas: List[PersonaResponse]
    test_goal: str
    api_url: str
    max_steps: int = 8

class TestSessionResponse(BaseModel):
    session_id: str
    status: str

class LogMessage(BaseModel):
    timestamp: str
    session_id: str
    persona_name: Optional[str] = None
    type: str  # "info", "thinking", "acting", "observing", "error", "complete"
    message: str
    data: Optional[Dict[str, Any]] = None

# In-memory storage for demo (in production, use Redis/DB)
active_sessions: Dict[str, Dict] = {}
session_logs: Dict[str, List[LogMessage]] = {}

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]

    async def send_log(self, session_id: str, log: LogMessage):
        if session_id in self.active_connections:
            try:
                print(f"Sending log via WebSocket to {session_id}")
                await self.active_connections[session_id].send_text(log.model_dump_json())
            except Exception as e:
                print(f"WebSocket send error for {session_id}: {e}")
                self.disconnect(session_id)
        else:
            print(f"No WebSocket connection for session {session_id} (active: {list(self.active_connections.keys())})")

manager = ConnectionManager()

# Utility functions
def create_log(session_id: str, type: str, message: str, persona_name: str = None, data: Dict = None) -> LogMessage:
    """Create a structured log message."""
    log = LogMessage(
        timestamp=datetime.now().isoformat(),
        session_id=session_id,
        persona_name=persona_name,
        type=type,
        message=message,
        data=data
    )
    
    # Store log
    if session_id not in session_logs:
        session_logs[session_id] = []
    session_logs[session_id].append(log)
    
    return log

async def broadcast_log(session_id: str, type: str, message: str, persona_name: str = None, data: Dict = None):
    """Create and broadcast a log message."""
    log = create_log(session_id, type, message, persona_name, data)
    print(f"Broadcasting log to {session_id}: {type} - {message[:50]}...")
    await manager.send_log(session_id, log)

# API Endpoints

@app.get("/")
async def root():
    return {
        "service": "PersonaFlow API",
        "status": "running",
        "version": "1.0.0",
        "endpoints": {
            "generate_personas": "/api/generate-personas",
            "run_tests": "/api/run-tests", 
            "websocket_logs": "/api/test-sessions/{session_id}/logs"
        }
    }

@app.post("/api/generate-personas")
async def generate_personas(request: PersonaRequest):
    try:
        print(f"Generating {request.num_personas} personas for: {request.market_segment}")
        
        # Initialize Architect
        architect = Architect()
        
        # Generate personas
        personas = architect.generate_personas(
            request.market_segment, 
            request.num_personas
        )
        
        if not personas:
            raise HTTPException(status_code=500, detail="Failed to generate personas")
        
        # Convert to response format
        response_personas = [
            PersonaResponse(name=p.name, system_prompt=p.system_prompt) 
            for p in personas
        ]
        
        print(f"Generated {len(response_personas)} personas successfully")
        return {"personas": response_personas}
        
    except Exception as e:
        print(f"Error generating personas: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate personas: {str(e)}")

@app.post("/api/run-tests")
async def start_test_session(request: TestRequest):
    try:
        session_id = str(uuid.uuid4())
        
        # Store session info
        active_sessions[session_id] = {
            "status": "started",
            "personas": request.personas,
            "test_goal": request.test_goal,
            "api_url": request.api_url,
            "max_steps": request.max_steps,
            "created_at": datetime.now().isoformat()
        }
        
        # Start background testing task with user-friendly delay
        asyncio.create_task(delayed_test_session(session_id, request))
        
        print(f"Started test session {session_id} with {len(request.personas)} personas")
        return TestSessionResponse(session_id=session_id, status="started")
        
    except Exception as e:
        print(f" Error starting test session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start test session: {str(e)}")

@app.get("/api/test-sessions/{session_id}")
async def get_session_status(session_id: str):
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = active_sessions[session_id]
    logs = session_logs.get(session_id, [])
    
    return {
        "session_id": session_id,
        "status": session["status"],
        "personas": session["personas"],
        "test_goal": session["test_goal"],
        "log_count": len(logs),
        "created_at": session["created_at"]
    }

@app.websocket("/api/test-sessions/{session_id}/logs")
async def websocket_logs(websocket: WebSocket, session_id: str):
    print(f"🔌 WebSocket connection attempt for session: {session_id}")
    
    # Check if session exists
    if session_id not in active_sessions:
        print(f"Session {session_id} not found in active_sessions")
        await websocket.close(code=4004, reason="Session not found")
        return
    
    await manager.connect(websocket, session_id)
    print(f"WebSocket connected for session: {session_id}")
    
    try:
        # Send existing logs if any
        if session_id in session_logs:
            print(f"Sending {len(session_logs[session_id])} existing logs to WebSocket")
            for log in session_logs[session_id]:
                await websocket.send_text(log.model_dump_json())
        else:
            print(f"No existing logs for session {session_id}")
        
        # Keep connection alive
        while True:
            await websocket.receive_text()  # Wait for client messages
            
    except WebSocketDisconnect:
        manager.disconnect(session_id)
        print(f"WebSocket disconnected for session {session_id}")

# Delayed start to allow WebSocket connection
async def delayed_test_session(session_id: str, request: TestRequest):
    try:
        # Give immediate feedback that we're preparing
        await broadcast_log(session_id, "info", "Preparing test environment...")
        await asyncio.sleep(0.5)  # Brief pause for WebSocket to connect
        
        await broadcast_log(session_id, "info", "Initializing AI agents...")
        await asyncio.sleep(0.5)  # Another brief pause
        
        await broadcast_log(session_id, "info", "Ready to start persona testing!")
        await asyncio.sleep(0.5)  # Final pause
        
        # Now start the actual testing
        await run_test_session(session_id, request)
        
    except Exception as e:
        await broadcast_log(session_id, "error", f"Failed to start testing: {str(e)}")
        active_sessions[session_id]["status"] = "failed"

# Background task for running persona tests
async def run_test_session(session_id: str, request: TestRequest):
    try:
        await broadcast_log(session_id, "info", f"Starting test session with {len(request.personas)} personas")
        
        # Update session status
        active_sessions[session_id]["status"] = "testing"
        
        # Check environment
        mock_api_url = request.api_url
        gemma_url = os.environ.get("GEMMA_URL")
        
        await broadcast_log(session_id, "info", f"Environment check:")
        await broadcast_log(session_id, "info", f"   MOCK_API_URL: {mock_api_url}")
        await broadcast_log(session_id, "info", f"   GEMMA_URL: {gemma_url}")
        await broadcast_log(session_id, "info", f"   HACKATHON_PROJECT_ID: {os.environ.get('HACKATHON_PROJECT_ID')}")
        
        if not gemma_url:
            await broadcast_log(session_id, "error", "GEMMA_URL not configured")
            active_sessions[session_id]["status"] = "failed"
            return
        
        # Initialize components
        toolbelt = Toolbelt(api_base_url=mock_api_url)
        llm_client = LLMServiceClient()
        test_results = []
        
        # Run each persona
        for i, persona_data in enumerate(request.personas):
            persona_name = persona_data.name
            await broadcast_log(session_id, "info", f"Starting tests for {persona_name} ({i+1}/{len(request.personas)})")
            
            # Convert to Persona object
            persona = Persona(name=persona_data.name, system_prompt=persona_data.system_prompt)
            
            # Run persona test
            result = await run_persona_test_async(
                session_id, persona, request.test_goal, toolbelt, llm_client, request.max_steps
            )
            
            if result:
                test_results.append(result)
                status = "Success" if result.was_successful else "Failed"
                await broadcast_log(session_id, "info", f"{persona_name} completed: {status}")
            else:
                await broadcast_log(session_id, "error", f"{persona_name} failed to complete")
        
        # Generate final report using Architect
        await broadcast_log(session_id, "info", "Generating final report...")
        architect = Architect()
        final_report = architect.synthesize_report(request.test_goal, test_results)
        
        # Store final results
        active_sessions[session_id].update({
            "status": "completed",
            "test_results": [r.model_dump() for r in test_results],
            "final_report": final_report,
            "completed_at": datetime.now().isoformat()
        })
        
        await broadcast_log(session_id, "complete", "All persona tests completed!", data={
            "report": final_report,
            "results": [r.model_dump() for r in test_results]
        })
        
    except Exception as e:
        await broadcast_log(session_id, "error", f"Test session failed: {str(e)}")
        active_sessions[session_id]["status"] = "failed"

async def run_persona_test_async(session_id: str, persona: Persona, goal: str, toolbelt: Toolbelt, llm_client: LLMServiceClient, max_steps: int = 8) -> Optional[TestResult]:
    try:
        persona_name = persona.name
        await broadcast_log(session_id, "thinking", f"{persona_name} is analyzing the goal: {goal}", persona_name)
        
        # Create agent
        agent = Agent(persona=persona, toolbelt=toolbelt, llm_client=llm_client)
        
        # Run agent steps
        for step in range(max_steps):
            try:
                # Create prompt
                prompt = agent._create_prompt(goal)
                
                # Get LLM response
                await broadcast_log(session_id, "thinking", f"{persona_name} is thinking (step {step + 1})...", persona_name)
                await broadcast_log(session_id, "info", f"🔄 Calling Gemma service for {persona_name}...")
                
                try:
                    llm_output_str = llm_client.invoke(prompt)
                    await broadcast_log(session_id, "info", f"Gemma service responded for {persona_name} (length: {len(llm_output_str)})")
                except Exception as llm_error:
                    await broadcast_log(session_id, "error", f"Gemma service error for {persona_name}: {str(llm_error)}", persona_name)
                    raise llm_error
                
                # Parse response
                from app.clients import clean_json_response
                from app.agent import LLMResponse
                
                cleaned_json = clean_json_response(llm_output_str)
                llm_response = LLMResponse.model_validate_json(cleaned_json)
                
                # Log thought
                await broadcast_log(session_id, "thinking", f"{persona_name}: \"{llm_response.thought}\"", persona_name)
                
                # Add to memory
                agent.memory.append(
                    {"role": "assistant", "content": llm_response.model_dump_json()}
                )
                
                # Execute tool
                await broadcast_log(session_id, "acting", f"{persona_name} is using: {llm_response.tool_name}", persona_name, {
                    "tool": llm_response.tool_name,
                    "parameters": llm_response.parameters
                })
                
                await broadcast_log(session_id, "info", f"🔧 Calling API tool: {llm_response.tool_name} with {llm_response.parameters}")
                
                try:
                    tool_result = toolbelt.use_tool(llm_response.tool_name, llm_response.parameters)
                    await broadcast_log(session_id, "info", f"API tool responded (length: {len(str(tool_result))})")
                except Exception as tool_error:
                    await broadcast_log(session_id, "error", f"API tool error: {str(tool_error)}")
                    raise tool_error
                
                # Log observation
                await broadcast_log(session_id, "observing", f"{persona_name} observed: {tool_result[:200]}...", persona_name, {
                    "full_result": tool_result
                })
                
                # Add observation to memory
                agent.memory.append(
                    {"role": "tool_observation", "content": tool_result}
                )
                
                # Check for completion
                if "Checkout successful" in tool_result or "ORDER CONFIRMED" in tool_result:
                    await broadcast_log(session_id, "info", f"{persona_name} completed the goal successfully!", persona_name)
                    break
                    
            except Exception as e:
                await broadcast_log(session_id, "error", f"{persona_name} encountered error at step {step + 1}: {str(e)}", persona_name)
                break
        
        # Determine success
        was_successful = any(
            "Checkout successful" in entry.get("content", "") or 
            "ORDER CONFIRMED" in entry.get("content", "")
            for entry in agent.memory
        )
        
        return TestResult(
            persona_name=persona.name,
            log=agent.memory,
            was_successful=was_successful
        )
        
    except Exception as e:
        await broadcast_log(session_id, "error", f"Failed to run {persona.name}: {str(e)}", persona.name)
        return None

if __name__ == "__main__":
    import uvicorn
    print("Starting PersonaFlow API Server")
    print("API will be available at: http://localhost:8000")
    print("API docs at: http://localhost:8000/docs")
    print("WebSocket logs at: ws://localhost:8000/api/test-sessions/{session_id}/logs")
    
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )