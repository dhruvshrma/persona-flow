# agent-runner-service/app/clients.py
import requests
import os
import re
import json
from typing import Dict, Any, Optional, Protocol
from pydantic import BaseModel
from typing import List


# Types for request/response handling
class LLMRequest(BaseModel):
    """Standard request format for LLM APIs."""

    prompt: str
    model: str
    temperature: Optional[float] = 1.0
    max_output_tokens: Optional[int] = 65535
    top_p: Optional[float] = 1.0


class LLMResponse(BaseModel):
    """Standard response format from LLM APIs."""

    text: str
    raw_data: Dict[str, Any]


class PersonaSchema(BaseModel):
    """Schema for persona generation - used to create Vertex AI responseSchema."""

    name: str
    system_prompt: str


class PersonaListSchema(BaseModel):
    """Schema for list of personas - root schema for structured output."""

    personas: List[PersonaSchema]


# Vertex AI Schema for persona generation (exact format from user's working playground example)
PERSONA_RESPONSE_SCHEMA = {
    "type": "ARRAY",
    "items": {
        "type": "OBJECT",
        "properties": {
            "name": {
                "type": "STRING",
                "description": "The name of the persona (e.g., 'Budget-Conscious Bob')",
            },
            "system_prompt": {
                "type": "STRING",
                "description": "Detailed system prompt that defines the persona's personality, technical skill, goals, and pain points for use by an AI agent",
            },
        },
        "required": ["name", "system_prompt"],
        "additionalProperties": False,
    },
    "minItems": 1,
    "maxItems": 10,
}


class LLMClient(Protocol):
    """Protocol defining interface for LLM clients."""

    def invoke(self, prompt: str) -> str:
        """Send prompt to LLM and return response text."""
        ...


# Parsing and packaging functions (independent of client implementation)
def clean_json_response(raw_text: str) -> str:
    """Clean JSON response by removing markdown blocks."""
    # Handle ```json blocks - use greedy matching to get complete JSON
    json_match = re.search(r"```json\s*(\{.*\})\s*```", raw_text, re.DOTALL)
    if json_match:
        return json_match.group(1).strip()

    # Handle ``` blocks - use greedy matching to get complete JSON
    json_match = re.search(r"```\s*(\{.*\})\s*```", raw_text, re.DOTALL)
    if json_match:
        return json_match.group(1).strip()

    # Look for JSON pattern - use greedy matching to get complete JSON
    json_match = re.search(r"(\{.*\})", raw_text, re.DOTALL)
    if json_match:
        return json_match.group(1).strip()

    return raw_text.strip()


def parse_vertex_ai_response(response_data: Dict[str, Any]) -> LLMResponse:
    """Parse Google Vertex AI response format into LLMResponse."""
    text = ""

    try:
        # Standard Vertex AI format
        if "candidates" in response_data and response_data["candidates"]:
            candidate = response_data["candidates"][0]
            if "content" in candidate and "parts" in candidate["content"]:
                parts = candidate["content"]["parts"]
                if parts and "text" in parts[0]:
                    # The 'text' field might be a JSON string itself
                    raw_text = parts[0]["text"]
                    try:
                        # Attempt to parse it as JSON
                        parsed_json = json.loads(raw_text)
                        # If successful, we want the string representation of that JSON
                        text = json.dumps(parsed_json, indent=2)
                    except json.JSONDecodeError:
                        # If it's not a valid JSON string, use the text as is
                        text = raw_text

        # Fallback formats
        elif "text" in response_data:
            text = response_data["text"]
        elif "response" in response_data:
            text = response_data["response"]
        else:
            text = str(response_data)
    except Exception as e:
        print(f"Error parsing Vertex AI response: {e}")
        text = str(response_data)  # Return raw data on error

    return LLMResponse(text=text, raw_data=response_data)


def parse_ollama_response(response_data: Dict[str, Any]) -> LLMResponse:
    """Parse Ollama API response format into LLMResponse."""
    text = ""

    if "response" in response_data:
        text = response_data["response"]
    elif "content" in response_data:
        text = response_data["content"]
    else:
        text = str(response_data)

    return LLMResponse(text=clean_json_response(text), raw_data=response_data)


def create_vertex_ai_payload(
    request: LLMRequest,
    response_schema: Optional[Dict[str, Any]] = None,
    system_instruction: Optional[str] = None,
    include_thinking_config: bool = True,
) -> Dict[str, Any]:
    """Create payload for Google Vertex AI format with optional structured output and system instruction."""
    generation_config = {
        "temperature": request.temperature,
        "maxOutputTokens": request.max_output_tokens,
        "topP": request.top_p,
    }

    # Add structured output if schema provided
    if response_schema:
        generation_config["responseMimeType"] = "application/json"
        generation_config["responseSchema"] = response_schema
    
    # Only add thinkingConfig for real Vertex AI, not for Gemma service
    if include_thinking_config:
        generation_config["thinkingConfig"] = {"thinkingBudget": 0}

    payload = {
        "contents": [{"role": "user", "parts": [{"text": request.prompt}]}],
        "generationConfig": generation_config,
        "safetySettings": [
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "OFF"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "OFF"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "OFF"},
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "OFF"},
        ],
    }

    # Add system instruction if provided
    if system_instruction:
        payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

    return payload


def create_ollama_payload(request: LLMRequest) -> Dict[str, Any]:
    """Create payload for Ollama API format."""
    return {"model": request.model, "prompt": request.prompt, "stream": False}


class LLMServiceClient:
    """Client for interacting with the deployed Gemma model using Google ADK pattern."""

    def __init__(self):
        # The URL is configured via environment variables (GEMMA_URL from deployment)
        self.url = os.environ.get("GEMMA_URL") or os.environ.get("LLM_SERVICE_URL")
        if not self.url:
            raise ValueError(
                "GEMMA_URL or LLM_SERVICE_URL environment variable is not set."
            )

        self.gemma_url = self.url.rstrip("/")
        self.model_name = "gemma3:12b"  # Using 12b model as requested

        # Get authentication headers for Cloud Run service-to-service calls
        self.auth_headers = self._get_auth_headers()

    def _get_auth_headers(self):
        """Get authentication headers for Cloud Run service-to-service calls (from starter)."""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "persona-flow-agent/1.0",
        }

        # Try to get identity token for authenticated requests
        try:
            import google.auth.transport.requests
            import google.oauth2.id_token

            auth_req = google.auth.transport.requests.Request()
            id_token = google.oauth2.id_token.fetch_id_token(auth_req, self.gemma_url)
            headers["Authorization"] = f"Bearer {id_token}"
            print(f"Added Authorization header with identity token")
        except Exception as e:
            print(f"Warning: Could not get identity token: {e}")
            # If authentication fails, proceed without auth header (for local testing)
            pass

        return headers

    def invoke(self, prompt: str) -> str:
        """Sends a prompt to the Gemma model using Vertex AI format from hackathon starter."""
        try:
            print(f"Querying Gemma at: {self.gemma_url}")
            print(f"Using model: {self.model_name}")

            # Create typed request
            request = LLMRequest(prompt=prompt, model=self.model_name)

            # Use Vertex AI format as per hackathon starter, but exclude thinkingConfig for Gemma
            payload = create_vertex_ai_payload(request, include_thinking_config=False)
            endpoint_url = (
                f"{self.gemma_url}/v1beta/models/{self.model_name}:generateContent"
            )

            response = requests.post(
                endpoint_url, headers=self.auth_headers, json=payload, timeout=60
            )
            response.raise_for_status()

            # Parse response using typed response
            response_data = response.json()
            llm_response = parse_vertex_ai_response(response_data)

            return llm_response.text

        except Exception as e:
            print(f"ERROR: Could not invoke Gemma service: {e}")
            return '{"error": "Failed to communicate with the Gemma service."}'


class OllamaClient:
    """Alternative client using Ollama API format."""

    def __init__(
        self, ollama_url: Optional[str] = None, model_name: str = "gemma3:12b"
    ):
        self.gemma_url = (ollama_url or os.environ.get("GEMMA_URL", "")).rstrip("/")
        self.model_name = model_name

        if not self.gemma_url:
            raise ValueError("GEMMA_URL must be provided")

        self.auth_headers = self._get_auth_headers()

    def _get_auth_headers(self):
        """Get auth headers for Ollama."""
        headers = {"Content-Type": "application/json"}
        try:
            import google.auth.transport.requests
            import google.oauth2.id_token

            auth_req = google.auth.transport.requests.Request()
            id_token = google.oauth2.id_token.fetch_id_token(auth_req, self.gemma_url)
            headers["Authorization"] = f"Bearer {id_token}"
        except Exception as e:
            print(f"Warning: Could not get identity token: {e}")

        return headers

    def invoke(self, prompt: str) -> str:
        """Send prompt using Ollama format."""
        try:
            # Create typed request
            request = LLMRequest(prompt=prompt, model=self.model_name)

            # Use Ollama format
            payload = create_ollama_payload(request)
            endpoint_url = f"{self.gemma_url}/api/generate"

            response = requests.post(
                endpoint_url, headers=self.auth_headers, json=payload, timeout=60
            )
            response.raise_for_status()

            # Parse response using typed response
            response_data = response.json()
            llm_response = parse_ollama_response(response_data)

            return llm_response.text

        except Exception as e:
            print(f"ERROR: Could not invoke Ollama: {e}")
            return '{"error": "Failed to communicate with Ollama."}'


class VertexAIClient:
    """Client for Google Vertex AI (for Architect agent)."""

    def __init__(
        self,
        project_id: Optional[str] = None,
        location: str = "global",
        model_name: str = "gemini-2.5-flash",
    ):
        self.project_id = (
            project_id
            or os.environ.get("GOOGLE_CLOUD_PROJECT")
            or os.environ.get("HACKATHON_PROJECT_ID")
        )
        self.location = location
        self.model_name = model_name

        if not self.project_id:
            raise ValueError(
                "GOOGLE_CLOUD_PROJECT or HACKATHON_PROJECT_ID must be set for Vertex AI client"
            )

        self.endpoint_url = "https://aiplatform.googleapis.com"

    def invoke(
        self,
        prompt: str,
        response_schema: Optional[Dict[str, Any]] = None,
        system_instruction: Optional[str] = None,
    ) -> str:
        """Send prompt to Vertex AI and return response."""
        try:
            print(f"Querying Vertex AI at: {self.endpoint_url}")
            print(f"Using model: {self.model_name}")

            # Create typed request
            request = LLMRequest(prompt=prompt, model=self.model_name)

            # Use Vertex AI format with optional structured output and system instruction
            payload = create_vertex_ai_payload(
                request, response_schema, system_instruction
            )
            url = f"{self.endpoint_url}/v1/projects/{self.project_id}/locations/{self.location}/publishers/google/models/{self.model_name}:generateContent"

            # Get access token using gcloud
            import subprocess

            try:
                access_token = (
                    subprocess.check_output(
                        ["gcloud", "auth", "print-access-token"],
                        stderr=subprocess.DEVNULL,
                    )
                    .decode()
                    .strip()
                )
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {access_token}",
                }
            except subprocess.CalledProcessError:
                print("Warning: Could not get gcloud access token")
                headers = {"Content-Type": "application/json"}

            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()

            # Parse response using typed response
            response_data = response.json()
            print(f"DEBUG: Vertex AI response: {response_data}")
            llm_response = parse_vertex_ai_response(response_data)

            return llm_response.text

        except Exception as e:
            print(f"ERROR: Could not invoke Vertex AI: {e}")
            return '{"error": "Failed to communicate with Vertex AI."}'


class MockLLMClient:
    """Mock client for testing."""

    def invoke(self, prompt: str) -> str:
        """Return mock response."""
        print(f"\n📤 MOCK LLM PROMPT:\n{'-'*50}")
        print(prompt[:500] + "..." if len(prompt) > 500 else prompt)
        print(f"{'-'*50}")

        return '{"thought": "I need to start by seeing what products are available.", "tool_name": "get_products", "parameters": {}}'


# The Toolbelt class is effectively the client for the mock-api-service.
# By keeping it separate, we maintain a clean design. The Toolbelt uses `requests`
