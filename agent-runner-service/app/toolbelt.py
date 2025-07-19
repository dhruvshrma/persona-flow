# agent-orchestrator/app/toolbelt.py
import requests
import json
from typing import List, Dict, Any

class Toolbelt:
    """A collection of tools that the agent can use to interact with the API."""
    def __init__(self, api_base_url: str):
        self.base_url = api_base_url.rstrip('/')
    
    def get_tool_descriptions(self) -> str:
        """Generates a string describing the available tools for the LLM prompt."""
        descriptions = [
            "get_products(): Lists all available products.",
            "search_products(q: str): Searches for products by a query string.",
            "add_to_cart(item_id: int, quantity: int): Adds a specific product to the cart.",
            "get_cart(): Retrieves the current contents of the shopping cart.",
            "get_product_total_cost(product_id: int): Gets the full cost of a single product, including all fees.",
            "checkout(shipping_address: str, billing_address: str): Attempts to complete the purchase."
            # We intentionally OMIT tools for flawed endpoints like /admin/users to see if the agent discovers them.
        ]
        return "\n".join(descriptions)

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """A robust wrapper for making API calls."""
        try:
            response = requests.request(method, f"{self.base_url}{endpoint}", **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            return {"error": "HTTPError", "status_code": e.response.status_code, "details": e.response.text}
        except Exception as e:
            return {"error": "Exception", "details": str(e)}

    # --- The actual tools the LLM can call ---
    
    def get_products(self) -> Dict[str, Any]:
        return self._make_request("GET", "/products")
        
    def search_products(self, q: str) -> Dict[str, Any]:
        return self._make_request("GET", "/search", params={"q": q})
        
    def add_to_cart(self, item_id: int, quantity: int) -> Dict[str, Any]:
        return self._make_request("POST", "/cart/add", json={"item_id": item_id, "quantity": quantity})

    def get_cart(self) -> Dict[str, Any]:
        return self._make_request("GET", "/cart")

    def get_product_total_cost(self, product_id: int) -> Dict[str, Any]:
        return self._make_request("GET", f"/products/{product_id}/total_cost")

    def checkout(self, shipping_address: str, billing_address: str) -> Dict[str, Any]:
        # Note: The agent doesn't know about tax_id yet. This will cause a failure.
        data = {"shipping_address": shipping_address, "billing_address": billing_address}
        return self._make_request("POST", "/checkout", json=data)

    def use_tool(self, tool_name: str, parameters: Dict[str, Any]) -> str:
        """The single entry point for the agent to use a tool."""
        if not hasattr(self, tool_name):
            return json.dumps({"error": f"Tool '{tool_name}' not found."})
            
        tool_function = getattr(self, tool_name)
        result = tool_function(**parameters)
        return json.dumps(result, indent=2)