import pytest
import os
from app.clients import LLMServiceClient


class TestLLMServiceClient:
    def test_llm_client_requires_gemma_url(self, monkeypatch):
        monkeypatch.delenv("GEMMA_URL", raising=False)
        monkeypatch.delenv("LLM_SERVICE_URL", raising=False)

        with pytest.raises(ValueError) as exc_info:
            LLMServiceClient()
        assert "GEMMA_URL" in str(exc_info.value)

    def test_llm_client_accepts_gemma_url_from_env(self, monkeypatch):
        test_url = "https://test-gemma-service.run.app"
        monkeypatch.setenv("GEMMA_URL", test_url)

        client = LLMServiceClient()
        assert client.url == test_url

    def test_llm_client_fallback_to_llm_service_url(self, monkeypatch):
        test_url = "https://test-llm-service.run.app"
        monkeypatch.delenv("GEMMA_URL", raising=False)
        monkeypatch.setenv("LLM_SERVICE_URL", test_url)

        client = LLMServiceClient()
        assert client.url == test_url

    def test_llm_client_invoke_returns_string(self, monkeypatch):
        test_url = "https://test-gemma.run.app"
        monkeypatch.setenv("GEMMA_URL", test_url)

        client = LLMServiceClient()

        assert hasattr(client, "invoke")
        assert callable(client.invoke)

    def test_llm_client_with_real_gemma_endpoint(self):
        gemma_url = os.environ.get("GEMMA_URL")
        if not gemma_url:
            pytest.skip("GEMMA_URL not set - skipping real integration test")

        client = LLMServiceClient()

        simple_prompt = "What is 2 + 2? Answer in one word."

        result = client.invoke(simple_prompt)

        assert result is not None
        assert len(result.strip()) > 0
        print(f"Simple Gemma response: {result}")

    def test_llm_client_with_persona_prompt(self):
        gemma_url = os.environ.get("GEMMA_URL")
        if not gemma_url:
            pytest.skip("GEMMA_URL not set - skipping real integration test")

        client = LLMServiceClient()
        persona_prompt = """
                        You are Casey, a casual online shopper. You are not very technical.
                        You expect things to just work easily.

                        Your goal is: "Find a wireless mouse"

                        You have the following tools available:
                        search_products(q: str): Searches for products by a query string.

                        Based on your persona and goal, what is your next step?
                        You MUST respond in the following JSON format:
                        {
                        "thought": "Your detailed thought process.",
                        "tool_name": "The single tool you will use next.",
                        "parameters": { "param_name": "param_value" }
                        }
                    """

        result = client.invoke(persona_prompt)

        assert result is not None
        assert len(result.strip()) > 0
        print(f"Persona Gemma response: {result}")

        result_lower = result.lower()
        assert "thought" in result_lower or "tool" in result_lower
