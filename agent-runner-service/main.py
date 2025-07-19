# agent-runner-service/main.py
from app.agent import Agent
from app.personas import CASUAL_SHOPPER, POWER_USER
from app.toolbelt import Toolbelt
from app.clients import LLMServiceClient
import os

# --- MOCK LLM CLIENT FOR LOCAL TESTING ---
# Keep this for local development/testing
class MockLLMClient:
    def invoke(self, prompt: str) -> str:
        print("--- PROMPT TO LLM ---\n", prompt, "\n---------------------")
        response = input("Enter mock LLM JSON response: ")
        return response

# --- Configuration ---
MOCK_API_URL = os.environ.get("MOCK_API_URL", "http://127.0.0.1:8001")  # Mock API service
GOAL = "Find the 'Wireless Mouse', check its total cost, add it to the cart, and check out."
USE_REAL_LLM = os.environ.get("USE_REAL_LLM", "false").lower() == "true"

# --- Execution ---
if __name__ == "__main__":
    
    # 1. Choose your persona
    persona_to_run = CASUAL_SHOPPER
    print(f"🎭 Running as: {persona_to_run.name}")
    
    # 2. Set up the components
    toolbelt = Toolbelt(api_base_url=MOCK_API_URL)
    
    # 3. Choose LLM client based on environment
    if USE_REAL_LLM:
        print("🧠 Using real Gemma model")
        llm_client = LLMServiceClient()
    else:
        print("🤖 Using mock LLM client (manual input)")
        llm_client = MockLLMClient()
    
    agent = Agent(persona=persona_to_run, toolbelt=toolbelt, llm_client=llm_client)
    
    # 4. Run the agent
    agent.run(goal=GOAL)