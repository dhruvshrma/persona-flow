# agent-runner-service/app/architect.py

import json
import os
from pathlib import Path
from typing import List, Dict, Any
from pydantic import BaseModel
from dotenv import load_dotenv
from .clients import (
    VertexAIClient,
    PERSONA_RESPONSE_SCHEMA,
)  # Use the powerful Vertex AI model for advanced tasks
from .personas import Persona

# Load environment variables
root_dir = Path(__file__).parent.parent.parent
dotenv_path = root_dir / ".env"
load_dotenv(dotenv_path=dotenv_path)

# We'll need a data structure for the results
class TestResult(BaseModel):
    persona_name: str
    log: List[Dict[str, Any]]  # The full memory of the agent run
    was_successful: bool


class Architect:
    def __init__(self):
        # Use HACKATHON_PROJECT_ID from environment
        project_id = os.getenv("HACKATHON_PROJECT_ID")
        # Use global location for Vertex AI as per curl example
        self.client = VertexAIClient(project_id=project_id, location="global")

    def generate_personas(
        self, market_segment: str, num_personas: int = 5
    ) -> List[Persona]:

        system_instruction = """You are an expert market researcher and product strategist.
Your task is to generate a certain number of distinct user personas based on the following market segment description provided by the user.

For each persona, you must create a name and a detailed system_prompt that a future AI agent will use.
The system_prompt should encapsulate their personality, technical skill, goals, and pain points.

You MUST respond with ONLY a valid JSON array, where each object in the array that is provided to you."""

        user_prompt = f"""Generate exactly {num_personas} distinct user personas for the market segment: "{market_segment}"

Return them as a JSON array.  Each persona should be unique and represent different aspects of this market segment."""

        try:
            # Use structured output with the exact schema that worked in playground
            response_str = self.client.invoke(
                prompt=user_prompt,
                response_schema=PERSONA_RESPONSE_SCHEMA,
                system_instruction=system_instruction,
            )
            print(f"DEBUG: Raw LLM response: {response_str}")

            # Parse the JSON string into Python objects
            personas_data = json.loads(response_str)
            print(f"DEBUG: Parsed JSON: {personas_data}")
            print(f"DEBUG: Type: {type(personas_data)}")
            print(
                f"DEBUG: Number of personas: {len(personas_data) if isinstance(personas_data, list) else 'Not a list'}"
            )

            # With structured output, should always be an array
            if not isinstance(personas_data, list):
                print("ERROR: Structured output should return array, got single object")
                return []

            return [Persona(**p_data) for p_data in personas_data]
        except json.JSONDecodeError as e:
            print(f"ARCHITECT ERROR: Invalid JSON from LLM: {e}")
            print(f"Raw response was: {response_str}")
            return []
        except Exception as e:
            print(f"ARCHITECT ERROR: Failed to generate personas. {e}")
            return []

    def synthesize_report(self, goal: str, test_results: List[TestResult]) -> str:
        print("ARCHITECT: Synthesizing final report from all test results...")

        raw_logs_text = ""
        for result in test_results:
            raw_logs_text += f"\n--- START LOG: {result.persona_name} (Success: {result.was_successful}) ---\n"
            raw_logs_text += json.dumps(result.log, indent=2)
            raw_logs_text += f"\n--- END LOG: {result.persona_name} ---\n"

        prompt = f"""
        You are a principal product manager analyzing the results of an automated API test.
        The overall goal of the test was: "{goal}"

        Multiple AI agents, each with a different persona, attempted this goal.
        Below are the raw JSON logs of their thought processes and actions.

        <RAW_LOGS>
        {raw_logs_text}
        </RAW_LOGS>

        Your task is to analyze these logs and generate a concise, insightful report for a busy executive.
        The report should be in Markdown format and have the following sections:

        ### Executive Summary
        A 2-3 sentence overview of the test results. Did the agents generally succeed or fail? What was the most significant finding?

        ### Key Findings & Actionable Insights
        A bulleted list of the 3-5 most critical issues discovered across all personas. For each issue, briefly explain the problem and suggest a concrete action for the engineering team.
        Example:
        - **ISSUE:** The `/search` endpoint is case-sensitive.
          **IMPACT:** This frustrated non-technical users like 'Casual Casey' who couldn't find products.
          **ACTION:** Modify the search endpoint to be case-insensitive by default.

        ### Persona Deep Dive
        Briefly summarize the experience of 2-3 key personas, highlighting how their unique personality led to different outcomes.
        """

        report = self.client.invoke(prompt)
        return report
