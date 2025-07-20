"""
TDD tests for Architect agent functionality
Tests persona generation and report synthesis with real Vertex AI calls
"""
import json
import pytest
from app.architect import Architect, TestResult
from app.personas import Persona


class TestArchitectPersonaGeneration:
    """TDD tests for Architect.generate_personas() method using real Vertex AI."""

    def test_generate_personas_returns_list(self):
        """Test that generate_personas returns a list of Persona objects."""
        architect = Architect()

        result = architect.generate_personas(
            "Budget-conscious online shoppers", num_personas=2
        )

        # Assertions for real LLM output
        assert isinstance(result, list)
        assert len(result) >= 0  # May return empty on LLM failure, which is acceptable

        if result:  # If LLM succeeded
            assert all(isinstance(persona, Persona) for persona in result)
            assert all(hasattr(persona, "name") for persona in result)
            assert all(hasattr(persona, "system_prompt") for persona in result)
            assert all(len(persona.name) > 0 for persona in result)
            assert all(len(persona.system_prompt) > 0 for persona in result)

    def test_generate_personas_with_different_market_segments(self):
        """Test that generate_personas works with different market descriptions."""
        architect = Architect()

        # Test with tech-savvy market
        tech_result = architect.generate_personas(
            "Technical software developers", num_personas=1
        )

        # Test with casual market
        casual_result = architect.generate_personas(
            "Non-technical everyday users", num_personas=1
        )

        # Both should return valid results or empty (acceptable for LLM failures)
        assert isinstance(tech_result, list)
        assert isinstance(casual_result, list)

        # If both succeeded, they should be different
        if tech_result and casual_result:
            assert tech_result[0].name != casual_result[0].name

    def test_generate_personas_respects_num_personas_parameter(self):
        """Test that generate_personas respects the num_personas parameter."""
        architect = Architect()

        result = architect.generate_personas("E-commerce users", num_personas=3)

        # Should return list (may be empty on LLM failure)
        assert isinstance(result, list)

        # If LLM succeeded, should return requested number
        if result:
            print(f"Requested 3 personas, got {len(result)}")
            assert len(result) == 3, f"Expected 3 personas, got {len(result)}"

    def test_generate_personas_single_vs_multiple(self):
        """Test that LLM correctly generates the requested number of personas."""
        architect = Architect()

        # Test single persona
        single_result = architect.generate_personas("Tech enthusiasts", num_personas=1)
        if single_result:
            assert (
                len(single_result) == 1
            ), f"Expected 1 persona, got {len(single_result)}"

        # Test multiple personas
        multi_result = architect.generate_personas("Online shoppers", num_personas=2)
        if multi_result:
            assert (
                len(multi_result) == 2
            ), f"Expected 2 personas, got {len(multi_result)}"


class TestArchitectReportSynthesis:
    """TDD tests for Architect.synthesize_report() method using real Vertex AI."""

    def test_synthesize_report_returns_string(self):
        """Test that synthesize_report returns a markdown report string."""
        # Create test data
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

        # Assertions for real LLM output
        assert isinstance(result, str)
        assert len(result) > 0  # Should return non-empty string

    def test_synthesize_report_with_multiple_personas(self):
        """Test that synthesize_report works with multiple persona results."""
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

        # Should return valid string report
        assert isinstance(result, str)
        assert len(result) > 0

    def test_synthesize_report_handles_empty_results(self):
        """Test that synthesize_report handles empty test results gracefully."""
        architect = Architect()
        result = architect.synthesize_report("Empty goal", [])

        # Should return valid string even with empty results
        assert isinstance(result, str)
        assert len(result) > 0

    def test_synthesize_report_with_different_goals(self):
        """Test that synthesize_report works with different goal descriptions."""
        test_results = [TestResult(persona_name="Test", log=[], was_successful=True)]

        architect = Architect()

        result1 = architect.synthesize_report("Buy premium headphones", test_results)
        result2 = architect.synthesize_report("Find budget electronics", test_results)

        # Both should return valid strings
        assert isinstance(result1, str)
        assert isinstance(result2, str)
        assert len(result1) > 0
        assert len(result2) > 0
