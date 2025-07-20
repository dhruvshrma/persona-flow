# agent-runner-service/app/clients.py
import requests
import os


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
        """Sends a prompt to the Gemma model using Ollama API format."""
        try:
            print(f"Querying Gemma at: {self.gemma_url}")
            print(f"Using model: {self.model_name}")

            # Use Ollama API format (discovered service is running Ollama)
            payload = {"model": self.model_name, "prompt": prompt, "stream": False}

            # Use Ollama endpoint format
            endpoint_url = f"{self.gemma_url}/api/generate"
            response = requests.post(
                endpoint_url, headers=self.auth_headers, json=payload, timeout=60
            )

            response.raise_for_status()

            # Parse response using Ollama format
            response_data = response.json()

            # Extract text from Ollama response format
            raw_response = ""
            if "response" in response_data:
                raw_response = response_data["response"]
            elif "content" in response_data:
                raw_response = response_data["content"]
            else:
                # Fallback: return raw response if structure doesn't match
                return str(response_data)

            # Clean up markdown code blocks if present
            if raw_response.startswith("```json"):
                # Remove ```json from start and ``` from end
                raw_response = (
                    raw_response.replace("```json", "").replace("```", "").strip()
                )
            elif raw_response.startswith("```"):
                # Remove ``` from start and end
                raw_response = raw_response.replace("```", "").strip()

            return raw_response

        except Exception as e:
            print(f"ERROR: Could not invoke Gemma service: {e}")
            # Return a structured error message that the agent can understand
            return '{"error": "Failed to communicate with the Gemma service."}'
