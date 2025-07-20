import pytest
import json
from app.clients import clean_json_response
from app.agent import LLMResponse


class TestJSONParsing:

    def test_clean_json_response_with_markdown_json_block(self):
        """Test cleaning JSON wrapped in ```json markdown blocks."""
        raw_text = '''```json
{
  "thought": "I need to search for a wireless mouse.",
  "tool_name": "search_products",
  "parameters": {"q": "wireless mouse"}
}
```'''
        
        cleaned = clean_json_response(raw_text)
        
        # Should extract the JSON without the markdown wrapper
        assert '```json' not in cleaned
        assert '```' not in cleaned
        
        # Should be valid JSON
        parsed = json.loads(cleaned)
        assert parsed["thought"] == "I need to search for a wireless mouse."
        assert parsed["tool_name"] == "search_products"
        assert parsed["parameters"]["q"] == "wireless mouse"

    def test_clean_json_response_with_generic_markdown_block(self):
        """Test cleaning JSON wrapped in generic ``` markdown blocks."""
        raw_text = '''```
{
  "thought": "Adding item to cart now.",
  "tool_name": "add_to_cart", 
  "parameters": {"item_id": "2", "quantity": "1"}
}
```'''
        
        cleaned = clean_json_response(raw_text)
        
        # Should extract the JSON without the markdown wrapper
        assert '```' not in cleaned
        
        # Should be valid JSON
        parsed = json.loads(cleaned)
        assert parsed["thought"] == "Adding item to cart now."
        assert parsed["tool_name"] == "add_to_cart"
        assert parsed["parameters"]["item_id"] == "2"

    def test_clean_json_response_plain_json(self):
        """Test that plain JSON (no markdown) passes through unchanged."""
        raw_text = '''{
  "thought": "This is plain JSON.",
  "tool_name": "get_products",
  "parameters": {}
}'''
        
        cleaned = clean_json_response(raw_text)
        
        # Should be unchanged but trimmed
        parsed = json.loads(cleaned)
        assert parsed["thought"] == "This is plain JSON."
        assert parsed["tool_name"] == "get_products"
        assert parsed["parameters"] == {}

    def test_clean_json_response_complex_nested_json(self):
        """Test parsing complex nested JSON with arrays and objects."""
        raw_text = '''```json
{
  "thought": "The cart has multiple items with complex structure.",
  "tool_name": "checkout",
  "parameters": {
    "shipping_address": "123 Main St, City, State",
    "items": [
      {"id": 1, "name": "Laptop", "price": 999.99},
      {"id": 2, "name": "Mouse", "price": 29.99}
    ],
    "options": {
      "express_shipping": true,
      "gift_wrap": false
    }
  }
}
```'''
        
        cleaned = clean_json_response(raw_text)
        parsed = json.loads(cleaned)
        
        assert parsed["thought"] == "The cart has multiple items with complex structure."
        assert parsed["tool_name"] == "checkout"
        assert len(parsed["parameters"]["items"]) == 2
        assert parsed["parameters"]["items"][0]["name"] == "Laptop"
        assert parsed["parameters"]["options"]["express_shipping"] is True

    def test_clean_json_response_with_quotes_in_content(self):
        """Test JSON containing quotes and special characters."""
        raw_text = '''```json
{
  "thought": "I'm confused by this \\"wireless mouse\\" search. It's not working as expected.",
  "tool_name": "search_products",
  "parameters": {"q": "Wireless Mouse"}
}
```'''
        
        cleaned = clean_json_response(raw_text)
        parsed = json.loads(cleaned)
        
        # Should handle escaped quotes properly
        assert "I'm confused" in parsed["thought"]
        assert '"wireless mouse"' in parsed["thought"]
        assert parsed["parameters"]["q"] == "Wireless Mouse"

    def test_clean_json_response_multiline_content(self):
        """Test JSON with multiline content in fields."""
        raw_text = '''```json
{
  "thought": "This is a very long thought that spans multiple lines.\\nI need to think carefully about this.\\nLet me proceed step by step.",
  "tool_name": "get_cart",
  "parameters": {}
}
```'''
        
        cleaned = clean_json_response(raw_text)
        parsed = json.loads(cleaned)
        
        # Should preserve newlines in the content (JSON parser converts \\n to \n)
        assert "\n" in parsed["thought"]
        assert "spans multiple lines" in parsed["thought"]
        assert parsed["tool_name"] == "get_cart"

    def test_llm_response_validation_with_cleaned_json(self):
        """Test that cleaned JSON properly validates with LLMResponse model."""
        raw_gemma_output = '''```json
{
  "thought": "I need to find the wireless mouse product first.",
  "tool_name": "search_products",
  "parameters": {
    "q": "wireless mouse"
  }
}
```'''
        
        # Clean and validate
        cleaned = clean_json_response(raw_gemma_output)
        llm_response = LLMResponse.model_validate_json(cleaned)
        
        # Should create valid LLMResponse object
        assert llm_response.thought == "I need to find the wireless mouse product first."
        assert llm_response.tool_name == "search_products"
        assert llm_response.parameters["q"] == "wireless mouse"

    def test_clean_json_response_edge_cases(self):
        """Test edge cases and malformed inputs."""
        
        # Empty input
        assert clean_json_response("") == ""
        
        # Just markdown blocks (no content inside)
        result = clean_json_response("```json\n```")
        # Since there's no actual JSON content, it falls through to the last pattern
        assert result == "```json\n```"
        
        # No JSON in markdown (but valid ``` block should extract content)
        result = clean_json_response("```\nSome text\n```")
        # Our regex looks for {} patterns, so non-JSON text returns as-is
        assert result == "```\nSome text\n```"
        
        # Multiple JSON blocks (should get the first one)
        multiple_blocks = '''```json
{"first": "block"}
```
Some text
```json
{"second": "block"}
```'''
        cleaned = clean_json_response(multiple_blocks)
        parsed = json.loads(cleaned)
        assert parsed["first"] == "block"
        assert "second" not in parsed

    def test_real_gemma_response_patterns(self):
        """Test with actual response patterns observed from Gemma."""
        
        # Pattern 1: Standard response with proper formatting
        gemma_response_1 = '''{
  "thought": "Okay, I need to find a wireless mouse. The easiest thing to do first is probably just to see what's available. I'm hoping it's a simple list I can browse. I don't want to have to guess at what kinds of search terms to use just yet.",
  "tool_name": "get_products",
  "parameters": {}
}'''
        
        cleaned = clean_json_response(gemma_response_1)
        llm_response = LLMResponse.model_validate_json(cleaned)
        assert "wireless mouse" in llm_response.thought
        assert llm_response.tool_name == "get_products"
        
        # Pattern 2: Response with markdown wrapper
        gemma_response_2 = '''```json
{
"thought": "Okay, the mouse is in my cart. Now I need to check what's in the cart and see the total cost before I do anything else.",
"tool_name": "get_cart",
"parameters": {}
}
```'''
        
        cleaned = clean_json_response(gemma_response_2)
        llm_response = LLMResponse.model_validate_json(cleaned)
        assert "mouse is in my cart" in llm_response.thought
        assert llm_response.tool_name == "get_cart"

    def test_greedy_vs_non_greedy_matching(self):
        """Test that greedy matching captures complete JSON objects."""
        
        # This would fail with non-greedy matching (.*?) but should work with greedy (.*)
        complex_json = '''{
  "thought": "I found a product with nested structure: {\\"id\\": 123, \\"nested\\": {\\"price\\": 29.99}}. Now I need to add it.",
  "tool_name": "add_to_cart",
  "parameters": {
    "item_id": "123",
    "metadata": {
      "source": "search",
      "user_action": "click"
    }
  }
}'''
        
        cleaned = clean_json_response(complex_json)
        parsed = json.loads(cleaned)
        
        # Should capture the complete JSON including nested structures
        assert "nested structure" in parsed["thought"]
        assert parsed["parameters"]["item_id"] == "123"
        assert parsed["parameters"]["metadata"]["source"] == "search"


if __name__ == "__main__":
    # Run tests if executed directly
    import sys
    sys.exit(pytest.main([__file__, "-v"]))