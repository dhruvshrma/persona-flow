import json
from pydantic import BaseModel, Field
from typing import List, Dict, Any
from .toolbelt import Toolbelt
from .clients import LLMClient
from .personas import Persona


class LLMResponse(BaseModel):
    thought: str = Field(description="Your reasoning and critique about the last step.")
    tool_name: str = Field(description="The name of the single tool to use next.")
    parameters: Dict[str, Any] = Field(
        description="The parameters for the chosen tool."
    )


class Agent:
    def __init__(self, persona: Persona, toolbelt: Toolbelt, llm_client: LLMClient):
        self.persona = persona
        self.toolbelt = toolbelt
        self.llm_client = llm_client
        self.memory: List[Dict[str, str]] = []

    def _create_prompt(self, goal: str) -> str:
        system_prompt = self.persona.system_prompt

        tool_descriptions = self.toolbelt.get_tool_descriptions()

        history = "\n".join(
            [f"{msg['role']}:\n{msg['content']}" for msg in self.memory]
        )

        prompt = f"""
                    {system_prompt}

                    Your ultimate goal is: "{goal}"

                    You have the following tools available:
                    {tool_descriptions}

                    This is the history of your actions and observations so far:
                    <history>
                    {history if history else "No actions taken yet."}
                    </history>

                    Based on your persona, the goal, and the history, what is your next step?
                    You MUST respond in the following JSON format:
                    {{
                    "thought": "Your detailed thought process and critique of the last observation.",
                    "tool_name": "The single tool you will use next.",
                    "parameters": {{ "param_name": "param_value" }}
                    }}
                """
        return prompt

    def run(self, goal: str, max_steps: int = 10):
        print(f"--- Starting run for {self.persona.name} with goal: {goal} ---")

        for step in range(max_steps):
            print(f"\n--- Step {step + 1} ---")

            # 1. REASON: Create the prompt
            prompt = self._create_prompt(goal)

            # 2. PLAN: Get the next action from the LLM
            llm_output_str = self.llm_client.invoke(prompt)

            try:
                llm_response = LLMResponse.model_validate_json(llm_output_str)
            except Exception as e:
                print(f"ERROR: LLM output failed validation: {e}")
                print(f"LLM Raw Output:\n{llm_output_str}")
                break

            # Log the thought process
            print(f"Thought: {llm_response.thought}")
            self.memory.append(
                {"role": "assistant", "content": llm_response.model_dump_json()}
            )

            # 3. ACT: Use the chosen tool
            print(f"Action: {llm_response.tool_name}({llm_response.parameters})")
            tool_result = self.toolbelt.use_tool(
                llm_response.tool_name, llm_response.parameters
            )

            # 4. OBSERVE: Log the result
            print(f"Observation:\n{tool_result}")
            self.memory.append({"role": "tool_observation", "content": tool_result})

            # A simple check for goal completion
            if "Checkout successful" in tool_result:
                print("\n--- GOAL ACHIEVED! ---")
                break

        print("\n--- Run Finished ---")
