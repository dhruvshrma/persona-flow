# orchestrator-service/app/clients.py
import requests
import os

class LLMServiceClient:
    """Client for interacting with the deployed Gemma model."""
    def __init__(self):
        # The URL is configured via environment variables (GEMMA_URL from deployment)
        self.url = os.environ.get("GEMMA_URL") or os.environ.get("LLM_SERVICE_URL")
        if not self.url:
            raise ValueError("GEMMA_URL or LLM_SERVICE_URL environment variable is not set.")

    def invoke(self, prompt: str) -> str:
        """Sends a prompt to the Gemma model and gets a structured JSON response."""
        try:
            # Format for Google's pre-packaged Gemma images
            payload = {
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": 200,
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "do_sample": True
                }
            }
            
            response = requests.post(
                f"{self.url}/generate", 
                json=payload, 
                timeout=120,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
            # Extract generated text from Gemma response
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                return result[0].get("generated_text", "")
            elif "generated_text" in result:
                return result["generated_text"]
            else:
                return str(result)
                
        except Exception as e:
            print(f"ERROR: Could not invoke Gemma service: {e}")
            # Return a structured error message that the agent can understand
            return '{"error": "Failed to communicate with the Gemma service."}'


# The Toolbelt class is effectively the client for the mock-api-service.
# By keeping it separate, we maintain a clean design. The Toolbelt uses `requests`
# internally but exposes business logic (e.g., `search_products`) to the agent.

