import pytest
import os
import json
from app.toolbelt import Toolbelt
import time


class TestToolbeltIntegration:
    def test_toolbelt_requires_api_url(self):
        api_url = "https://test-mock-api.run.app"
        toolbelt = Toolbelt(api_base_url=api_url)
        assert toolbelt.base_url == api_url

    def test_toolbelt_strips_trailing_slash(self):
        api_url = "https://test-mock-api.run.app/"
        toolbelt = Toolbelt(api_base_url=api_url)
        assert toolbelt.base_url == "https://test-mock-api.run.app"

    def test_toolbelt_has_required_methods(self):
        api_url = "https://test-mock-api.run.app"
        toolbelt = Toolbelt(api_base_url=api_url)

        # Check all required methods exist
        assert hasattr(toolbelt, "get_products")
        assert hasattr(toolbelt, "search_products")
        assert hasattr(toolbelt, "add_to_cart")
        assert hasattr(toolbelt, "get_cart")
        assert hasattr(toolbelt, "get_product_total_cost")
        assert hasattr(toolbelt, "checkout")
        assert hasattr(toolbelt, "use_tool")

    def test_toolbelt_get_tool_descriptions(self):
        api_url = "https://test-mock-api.run.app"
        toolbelt = Toolbelt(api_base_url=api_url)

        descriptions = toolbelt.get_tool_descriptions()

        assert isinstance(descriptions, str)
        assert "get_products" in descriptions
        assert "search_products" in descriptions
        assert "add_to_cart" in descriptions
        # Should intentionally omit admin endpoints
        assert "/admin" not in descriptions

    def test_toolbelt_use_tool_with_valid_tool(self):
        api_url = "https://test-mock-api.run.app"
        toolbelt = Toolbelt(api_base_url=api_url)

        def mock_get_products():
            return {"test": "data"}

        original_method = toolbelt.get_products
        toolbelt.get_products = mock_get_products

        try:
            result = toolbelt.use_tool("get_products", {})

            # Should return JSON string
            assert isinstance(result, str)
            parsed = json.loads(result)
            assert parsed["test"] == "data"
        finally:
            toolbelt.get_products = original_method

    def test_toolbelt_use_tool_with_parameters(self):
        api_url = "https://test-mock-api.run.app"
        toolbelt = Toolbelt(api_base_url=api_url)

        def mock_search_products(q):
            return {"query": q, "results": []}

        original_method = toolbelt.search_products
        toolbelt.search_products = mock_search_products

        try:
            result = toolbelt.use_tool("search_products", {"q": "test mouse"})

            parsed = json.loads(result)
            assert parsed["query"] == "test mouse"
        finally:
            toolbelt.search_products = original_method

    def test_toolbelt_use_tool_handles_invalid_tool(self):
        api_url = "https://test-mock-api.run.app"
        toolbelt = Toolbelt(api_base_url=api_url)

        result = toolbelt.use_tool("invalid_tool", {})

        parsed = json.loads(result)
        assert "error" in parsed
        assert "Tool 'invalid_tool' not found" in parsed["error"]

    def test_toolbelt_with_real_mock_api_health(self):
        mock_api_url = os.environ.get("MOCK_API_URL")
        if not mock_api_url:
            pytest.skip("MOCK_API_URL not set - skipping real integration test")

        toolbelt = Toolbelt(api_base_url=mock_api_url)

        health_result = toolbelt._make_request("GET", "/health")

        assert "status" in health_result
        assert health_result["status"] == "healthy"
        assert health_result["service"] == "mock-api"
        print(f"Health check: {health_result}")

    def test_toolbelt_with_real_mock_api_products(self):
        mock_api_url = os.environ.get("MOCK_API_URL")
        if not mock_api_url:
            pytest.skip("MOCK_API_URL not set - skipping real integration test")

        toolbelt = Toolbelt(api_base_url=mock_api_url)

        products_result = toolbelt.get_products()

        assert "products" in products_result
        assert "total" in products_result
        assert len(products_result["products"]) > 0

        product = products_result["products"][0]
        assert "id" in product
        assert "name" in product
        assert "price" in product

        print(f"Products: {len(products_result['products'])} found")

    def test_toolbelt_discovers_case_sensitivity_flaw(self):
        mock_api_url = os.environ.get("MOCK_API_URL")
        if not mock_api_url:
            pytest.skip("MOCK_API_URL not set - skipping real integration test")

        toolbelt = Toolbelt(api_base_url=mock_api_url)

        search_caps = toolbelt.search_products("Laptop")
        print(f"Search 'Laptop': {len(search_caps['results'])} results")

        search_lower = toolbelt.search_products("laptop")
        print(f"Search 'laptop': {len(search_lower['results'])} results")

        assert len(search_caps["results"]) != len(search_lower["results"])
        assert len(search_lower["results"]) == 0

    def test_toolbelt_discovers_cart_inconsistency_flaw(self):
        mock_api_url = os.environ.get("MOCK_API_URL")
        if not mock_api_url:
            pytest.skip("MOCK_API_URL not set - skipping real integration test")

        toolbelt = Toolbelt(api_base_url=mock_api_url)

        first_add = toolbelt.add_to_cart(item_id=1, quantity=1)
        print(f"First add result keys: {list(first_add.keys())}")

        second_add = toolbelt.add_to_cart(item_id=2, quantity=1)
        print(f"Second add result keys: {list(second_add.keys())}")

        assert "cart" in first_add
        assert "cart" not in second_add
        assert "message" in second_add

    def test_toolbelt_discovers_slow_endpoint_flaw(self):
        mock_api_url = os.environ.get("MOCK_API_URL")
        if not mock_api_url:
            pytest.skip("MOCK_API_URL not set - skipping real integration test")

        toolbelt = Toolbelt(api_base_url=mock_api_url)

        start_time = time.time()

        cart_result = toolbelt.get_cart()

        duration = time.time() - start_time
        print(f"Cart endpoint took: {duration:.2f} seconds")

        assert duration > 2.0

        assert "items" in cart_result
        assert "total" in cart_result
