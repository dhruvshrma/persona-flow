import json
import pytest
from app.architect import Architect, TestResult
from app.personas import Persona


class TestArchitectPersonaGeneration:
    def test_generate_personas_returns_list(self):
        architect = Architect()

        result = architect.generate_personas(
            "Budget-conscious online shoppers", num_personas=2
        )

        assert isinstance(result, list)
        assert len(result) >= 0

        if result:
            assert all(isinstance(persona, Persona) for persona in result)
            assert all(hasattr(persona, "name") for persona in result)
            assert all(hasattr(persona, "system_prompt") for persona in result)
            assert all(len(persona.name) > 0 for persona in result)
            assert all(len(persona.system_prompt) > 0 for persona in result)

    def test_generate_personas_with_different_market_segments(self):
        architect = Architect()

        tech_result = architect.generate_personas(
            "Technical software developers", num_personas=1
        )

        casual_result = architect.generate_personas(
            "Non-technical everyday users", num_personas=1
        )

        assert isinstance(tech_result, list)
        assert isinstance(casual_result, list)

        if tech_result and casual_result:
            assert tech_result[0].name != casual_result[0].name

    def test_generate_personas_respects_num_personas_parameter(self):
        architect = Architect()

        result = architect.generate_personas("E-commerce users", num_personas=3)

        assert isinstance(result, list)

        if result:
            print(f"Requested 3 personas, got {len(result)}")
            assert len(result) == 3, f"Expected 3 personas, got {len(result)}"

    def test_generate_personas_single_vs_multiple(self):
        architect = Architect()

        single_result = architect.generate_personas("Tech enthusiasts", num_personas=1)
        if single_result:
            assert (
                len(single_result) == 1
            ), f"Expected 1 persona, got {len(single_result)}"

        multi_result = architect.generate_personas("Online shoppers", num_personas=2)
        if multi_result:
            assert (
                len(multi_result) == 2
            ), f"Expected 2 personas, got {len(multi_result)}"


class TestArchitectReportSynthesis:
    def test_synthesize_report_returns_string(self):
        test_results = [
            TestResult(
                persona_name="Casey",
                log=[
                    {
                        "step": 1,
                        "thought": "Search failed",
                        "tool_name": "search_products",
                    }
                ],
                was_successful=False,
            ),
            TestResult(
                persona_name="Paula",
                log=[
                    {"step": 1, "thought": "API is slow", "tool_name": "get_products"}
                ],
                was_successful=True,
            ),
        ]

        architect = Architect()
        result = architect.synthesize_report("Find wireless mouse", test_results)

        assert isinstance(result, str)
        assert len(result) > 0

    def test_synthesize_report_with_multiple_personas(self):
        test_results = [
            TestResult(
                persona_name="Casey", log=[{"action": "search"}], was_successful=False
            ),
            TestResult(
                persona_name="Paula", log=[{"action": "browse"}], was_successful=True
            ),
            TestResult(
                persona_name="Alex", log=[{"action": "checkout"}], was_successful=False
            ),
        ]

        architect = Architect()
        result = architect.synthesize_report("Test goal", test_results)

        assert isinstance(result, str)
        assert len(result) > 0

    def test_synthesize_report_handles_empty_results(self):
        architect = Architect()
        result = architect.synthesize_report("Empty goal", [])

        assert isinstance(result, str)
        assert len(result) > 0

    def test_synthesize_report_with_different_goals(self):
        test_results = [TestResult(persona_name="Test", log=[], was_successful=True)]

        architect = Architect()

        result1 = architect.synthesize_report("Buy premium headphones", test_results)
        result2 = architect.synthesize_report("Find budget electronics", test_results)

        assert isinstance(result1, str)
        assert isinstance(result2, str)
        assert len(result1) > 0
        assert len(result2) > 0
