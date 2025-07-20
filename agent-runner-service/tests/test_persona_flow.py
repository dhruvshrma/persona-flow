import pytest
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from app.agent import Agent, LLMResponse
from app.personas import CASUAL_SHOPPER, POWER_USER
from app.toolbelt import Toolbelt
from app.clients import LLMServiceClient

# Load environment variables from .env file in root directory
root_dir = Path(__file__).parent.parent.parent
dotenv_path = root_dir / ".env"
load_dotenv(dotenv_path=dotenv_path)


class MockLLMClientForTesting:
    def __init__(self):
        self.call_count = 0

    def invoke(self, prompt: str) -> str:
        self.call_count += 1

        # Return different responses based on call count for testing
        if self.call_count == 1:
            return """
{
  "thought": "I need to search for a wireless mouse since that's my goal.",
  "tool_name": "search_products",
  "parameters": {"q": "wireless mouse"}
}
"""
        elif self.call_count == 2:
            return """
{
  "thought": "The search didn't find anything. Let me try with proper capitalization.",
  "tool_name": "search_products", 
  "parameters": {"q": "Wireless Mouse"}
}
"""
        else:
            return """
{
  "thought": "Great! I found the mouse. Let me add it to my cart.",
  "tool_name": "add_to_cart",
  "parameters": {"item_id": 2, "quantity": 1}
}
"""


class TestPersonaFlow:
    def test_agent_initializes_with_all_components(self):
        persona = CASUAL_SHOPPER
        toolbelt = Toolbelt("https://test-api.com")
        llm_client = MockLLMClientForTesting()

        agent = Agent(persona=persona, toolbelt=toolbelt, llm_client=llm_client)

        assert agent.persona == persona
        assert agent.toolbelt == toolbelt
        assert agent.llm_client == llm_client
        assert agent.memory == []

    def test_agent_creates_proper_prompts(self):
        persona = CASUAL_SHOPPER
        toolbelt = Toolbelt("https://test-api.com")
        llm_client = MockLLMClientForTesting()

        agent = Agent(persona=persona, toolbelt=toolbelt, llm_client=llm_client)

        goal = "Find a wireless mouse"
        prompt = agent._create_prompt(goal)

        # Should include persona information
        assert "Casey" in prompt
        assert "casual online shopper" in prompt

        # Should include goal
        assert goal in prompt

        # Should include tool descriptions
        assert "search_products" in prompt
        assert "get_products" in prompt

        # Should request JSON format
        assert "JSON format" in prompt

    def test_llm_response_validation(self):
        # Valid response should work
        valid_response = {
            "thought": "I need to search for products",
            "tool_name": "search_products",
            "parameters": {"q": "mouse"},
        }

        response = LLMResponse.model_validate(valid_response)
        assert response.thought == "I need to search for products"
        assert response.tool_name == "search_products"
        assert response.parameters == {"q": "mouse"}

        # Invalid response should fail
        with pytest.raises(Exception):
            LLMResponse.model_validate({"invalid": "data"})

    def test_agent_single_step_with_mock_llm(self):
        persona = CASUAL_SHOPPER
        toolbelt = Toolbelt("https://test-api.com")
        llm_client = MockLLMClientForTesting()

        # Mock the toolbelt method for testing
        def mock_search(q):
            return {"results": [], "query": q, "total": 0}

        toolbelt.search_products = mock_search

        agent = Agent(persona=persona, toolbelt=toolbelt, llm_client=llm_client)

        goal = "Find a wireless mouse"
        prompt = agent._create_prompt(goal)

        llm_output = llm_client.invoke(prompt)

        # Should get valid JSON
        assert "thought" in llm_output
        assert "tool_name" in llm_output
        assert "search_products" in llm_output

    def test_persona_flow_with_real_mock_api(self):
        mock_api_url = os.environ.get("MOCK_API_URL")
        if not mock_api_url:
            pytest.skip("MOCK_API_URL not set - skipping real API integration test")

        persona = CASUAL_SHOPPER
        toolbelt = Toolbelt(api_base_url=mock_api_url)
        llm_client = MockLLMClientForTesting()

        agent = Agent(persona=persona, toolbelt=toolbelt, llm_client=llm_client)

        # Test that agent can interact with real API
        goal = "Find a wireless mouse"

        # Simulate one step of the agent loop manually
        prompt = agent._create_prompt(goal)
        llm_output = llm_client.invoke(prompt)

        llm_response = LLMResponse.model_validate_json(llm_output)
        print(f"LLM wants to use: {llm_response.tool_name}")

        # Execute the tool against real API
        tool_result = toolbelt.use_tool(llm_response.tool_name, llm_response.parameters)
        print(f"Tool result: {tool_result[:200]}...")

        # Should get real response from mock API
        assert tool_result is not None
        assert len(tool_result) > 0

    def test_persona_discovers_case_sensitivity_flaw(self):
        mock_api_url = os.environ.get("MOCK_API_URL")
        if not mock_api_url:
            pytest.skip("MOCK_API_URL not set - skipping flaw discovery test")

        toolbelt = Toolbelt(api_base_url=mock_api_url)

        # Simulate persona discovering the flaw through different searches
        # Note: toolbelt methods return dict, use_tool returns JSON string
        lowercase_data = toolbelt.search_products("wireless mouse")
        capitalized_data = toolbelt.search_products("Wireless Mouse")

        print(f"Lowercase search: {len(lowercase_data['results'])} results")
        print(f"Capitalized search: {len(capitalized_data['results'])} results")

        # The flaw: different results for same logical search
        assert len(lowercase_data["results"]) != len(capitalized_data["results"])

        # Specifically, lowercase should return 0 (the strategic flaw)
        assert len(lowercase_data["results"]) == 0

    def test_persona_discovers_cart_inconsistency_flaw(self):
        mock_api_url = os.environ.get("MOCK_API_URL")
        if not mock_api_url:
            pytest.skip("MOCK_API_URL not set - skipping cart inconsistency test")

        toolbelt = Toolbelt(api_base_url=mock_api_url)

        # Simulate persona adding items to cart multiple times
        # Note: toolbelt methods return dict directly
        first_data = toolbelt.add_to_cart(item_id=1, quantity=1)
        second_data = toolbelt.add_to_cart(item_id=2, quantity=1)

        print(f"First add response keys: {list(first_data.keys())}")
        print(f"Second add response keys: {list(second_data.keys())}")

        # The flaw: inconsistent response structure
        assert "cart" in first_data
        assert "cart" not in second_data  # Inconsistent!

    def test_raw_gemma_response_structure(self):
        ## Need this to see what the raw response looks like.
        mock_api_url = os.environ.get("MOCK_API_URL")
        gemma_url = os.environ.get("GEMMA_URL")

        if not mock_api_url:
            pytest.skip("MOCK_API_URL not set - skipping raw response analysis")
        if not gemma_url:
            pytest.skip("GEMMA_URL not set - skipping raw response analysis")

        persona = CASUAL_SHOPPER
        toolbelt = Toolbelt(api_base_url=mock_api_url)  # Use REAL Mock API
        llm_client = LLMServiceClient()

        agent = Agent(persona=persona, toolbelt=toolbelt, llm_client=llm_client)

        goal = "Find a wireless mouse"

        # Get full prompt and response
        prompt = agent._create_prompt(goal)
        print(f"\nPROMPT SENT:\n{'-'*50}")
        print(prompt[:500] + "..." if len(prompt) > 500 else prompt)
        print(f"{'-'*50}")
        raw_response = llm_client.invoke(prompt)
        print(f"\nRAW GEMMA RESPONSE:\n{'-'*50}")
        print(raw_response)  # Print the ENTIRE response
        print(f"{'-'*50}")

        # Analyze structure
        print(f"\n RESPONSE ANALYSIS:")
        print(f"Total length: {len(raw_response)} characters")
        print(f"Contains '```json': {'```json' in raw_response}")
        print(f"Contains '```': {'```' in raw_response}")
        print(f"Contains 'thought': {'thought' in raw_response}")
        print(f"Contains 'tool_name': {'tool_name' in raw_response}")
        print(f"Contains narrative text: {not raw_response.strip().startswith('{')}")

        # Try to identify JSON boundaries
        import re

        json_matches = list(re.finditer(r"\{.*?\}", raw_response, re.DOTALL))
        print(f"JSON blocks found: {len(json_matches)}")

        for i, match in enumerate(json_matches):
            print(f"JSON block {i+1}: characters {match.start()}-{match.end()}")
            print(f"Content: {match.group()[:]}..")

    def test_full_agent_run_with_deployed_services(self):
        mock_api_url = os.environ.get("MOCK_API_URL")
        gemma_url = os.environ.get("GEMMA_URL")

        if not mock_api_url:
            pytest.skip("MOCK_API_URL not set - skipping full integration test")

        persona = CASUAL_SHOPPER
        toolbelt = Toolbelt(api_base_url=mock_api_url)

        if gemma_url:
            print("Using real Gemma model")
            llm_client = LLMServiceClient()
        else:
            print("Using mock LLM client")
            llm_client = MockLLMClientForTesting()

        agent = Agent(persona=persona, toolbelt=toolbelt, llm_client=llm_client)

        goal = "Buy a wireless mouse and check out"
        print(f"Running {persona.name} with goal: {goal}")

        prompt = agent._create_prompt(goal)
        llm_output = llm_client.invoke(prompt)

        print(f" LLM Response: {llm_output[:]}...")

        llm_response = LLMResponse.model_validate_json(llm_output)
        tool_result = toolbelt.use_tool(llm_response.tool_name, llm_response.parameters)

        print(f" Tool: {llm_response.tool_name}")
        print(f"Result: {tool_result[:200]}...")

        assert tool_result is not None
        assert len(tool_result) > 0
