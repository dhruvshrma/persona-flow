import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoint:
    def test_health_check_returns_200(self):
        from app.api import app

        client = TestClient(app)

        response = client.get("/health")
        assert response.status_code == 200

    def test_health_check_returns_proper_json(self):
        from app.api import app

        client = TestClient(app)

        response = client.get("/health")
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
        assert "service" in data
        assert data["service"] == "mock-api"


class TestProductsEndpoint:
    def test_products_returns_200(self):
        from app.api import app

        client = TestClient(app)

        response = client.get("/products")
        assert response.status_code == 200

    def test_products_returns_well_structured_data(self):
        from app.api import app

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
    def test_search_works_with_exact_case(self):
        from app.api import app

        client = TestClient(app)

        response = client.get("/search?q=Laptop")
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) > 0

    def test_search_fails_with_wrong_case(self):
        from app.api import app

        client = TestClient(app)

        # This should return no results due to case sensitivity flaw
        response = client.get("/search?q=laptop")  # lowercase
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 0  # The flaw!


class TestCartEndpoint:
    def test_first_cart_add_returns_full_cart(self):
        from app.api import app

        client = TestClient(app)

        response = client.post("/cart/add", json={"product_id": 1, "quantity": 1})
        assert response.status_code == 200
        data = response.json()
        assert "cart" in data  # First call returns full cart
        assert "items" in data["cart"]

    def test_subsequent_cart_add_returns_just_message(self):
        from app.api import app

        client = TestClient(app)

        # First add
        client.post("/cart/add", json={"product_id": 1, "quantity": 1})

        # Second add - should return different format (the flaw!)
        response = client.post("/cart/add", json={"product_id": 2, "quantity": 1})
        assert response.status_code == 200
        data = response.json()
        assert "cart" not in data  # Inconsistent! No cart object
        assert "message" in data
