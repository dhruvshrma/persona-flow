"""
TDD tests for mock service - testing both excellent and flawed behaviors
"""
import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """Test the excellent health check endpoint"""
    
    def test_health_check_returns_200(self):
        """Health endpoint should return 200 OK - this is our 'excellent' endpoint"""
        from src.mock_service.app import app
        client = TestClient(app)
        
        response = client.get("/health")
        assert response.status_code == 200
        
    def test_health_check_returns_proper_json(self):
        """Health check should return well-structured JSON"""
        from src.mock_service.app import app
        client = TestClient(app)
        
        response = client.get("/health")
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
        assert "service" in data
        assert data["service"] == "mock-api"


class TestProductsEndpoint:
    """Test the excellent products endpoint - should work beautifully"""
    
    def test_products_returns_200(self):
        """Products endpoint should work perfectly"""
        from src.mock_service.app import app
        client = TestClient(app)
        
        response = client.get("/products")
        assert response.status_code == 200
        
    def test_products_returns_well_structured_data(self):
        """Products should return clean, consistent JSON structure"""
        from src.mock_service.app import app
        client = TestClient(app)
        
        response = client.get("/products")
        data = response.json()
        
        # Should have good structure
        assert "products" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data
        
        # Should have some products
        assert len(data["products"]) > 0
        
        # Each product should have consistent fields
        product = data["products"][0]
        assert "id" in product
        assert "name" in product
        assert "price" in product
        assert "description" in product
        assert "category" in product


class TestSearchEndpoint:
    """Test the strategically flawed search endpoint"""
    
    def test_search_works_with_exact_case(self):
        """Search should work when case matches exactly"""
        from src.mock_service.app import app
        client = TestClient(app)
        
        response = client.get("/search?q=Laptop")
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) > 0
        
    def test_search_fails_with_wrong_case(self):
        """FLAW: Search should be case-sensitive, frustrating casual users"""
        from src.mock_service.app import app
        client = TestClient(app)
        
        # This should return no results due to case sensitivity flaw
        response = client.get("/search?q=laptop")  # lowercase
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 0  # The flaw!


class TestCartEndpoint:
    """Test the inconsistent cart endpoint"""
    
    def test_first_cart_add_returns_full_cart(self):
        """FLAW: First add to cart returns full cart object"""
        from src.mock_service.app import app
        client = TestClient(app)
        
        response = client.post("/cart/add", json={"product_id": 1, "quantity": 1})
        assert response.status_code == 200
        data = response.json()
        assert "cart" in data  # First call returns full cart
        assert "items" in data["cart"]
        
    def test_subsequent_cart_add_returns_just_message(self):
        """FLAW: Subsequent adds return different format - inconsistent API!"""
        from src.mock_service.app import app
        client = TestClient(app)
        
        # First add
        client.post("/cart/add", json={"product_id": 1, "quantity": 1})
        
        # Second add - should return different format (the flaw!)
        response = client.post("/cart/add", json={"product_id": 2, "quantity": 1})
        assert response.status_code == 200
        data = response.json()
        assert "cart" not in data  # Inconsistent! No cart object
        assert "message" in data   # Just a message instead