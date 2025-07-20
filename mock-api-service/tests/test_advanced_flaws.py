import pytest
import time
from fastapi.testclient import TestClient


class TestPerformanceFlaws:
    def test_cart_endpoint_is_artificially_slow(self):
        from app.api import app

        client = TestClient(app)

        start_time = time.time()
        response = client.get("/cart")
        duration = time.time() - start_time

        assert response.status_code == 200
        assert duration > 2.0  # Should take at least 2 seconds (artificial delay)

    def test_slow_cart_returns_proper_data(self):
        from app.api import app

        client = TestClient(app)

        response = client.get("/cart")
        data = response.json()
        assert "items" in data
        assert "total" in data


class TestHiddenComplexityFlaws:
    def test_checkout_fails_without_hidden_fields(self):
        from app.api import app

        client = TestClient(app)

        # Simple checkout attempt should fail
        response = client.post("/checkout", json={"payment_method": "card"})
        assert response.status_code == 400

    def test_checkout_error_reveals_hidden_requirements(self):
        from app.api import app

        client = TestClient(app)

        response = client.post("/checkout", json={"payment_method": "card"})
        data = response.json()
        # FastAPI wraps error details in "detail" key
        detail = data["detail"]
        assert "required_fields" in detail
        assert "shipping_address" in detail["required_fields"]
        assert "billing_address" in detail["required_fields"]
        assert "tax_id" in detail["required_fields"]  # Surprise requirement!


class TestDeveloperFrustrationFlaws:
    def test_bulk_operations_not_supported(self):
        from app.api import app

        client = TestClient(app)

        response = client.post("/cart/bulk_add", json={"products": [1, 2, 3]})
        assert response.status_code == 404  # Not implemented!

    def test_no_api_versioning(self):
        from app.api import app

        client = TestClient(app)

        response = client.get("/v2/products")
        assert response.status_code == 404  # No versioning!


class TestSecurityGaps:
    def test_admin_endpoint_has_weak_permissions(self):
        from app.api import app

        client = TestClient(app)

        # Should be protected but isn't properly
        response = client.get("/admin/users")
        assert response.status_code == 403  # Forbidden, but reveals endpoint exists

    def test_admin_error_leaks_information(self):
        from app.api import app

        client = TestClient(app)

        response = client.get("/admin/users")
        data = response.json()
        assert "detail" in data
        # Should leak information about the system
        assert "database" in data["detail"].lower() or "admin" in data["detail"].lower()


class TestPricingFlaws:
    def test_products_hide_additional_fees(self):
        from app.api import app

        client = TestClient(app)

        response = client.get("/products/1/total_cost")
        assert response.status_code == 200
        data = response.json()

        # Hidden fees should be revealed
        assert data["base_price"] != data["total_cost"]
        assert "fees" in data
        assert len(data["fees"]) > 0  # Surprise fees!

    def test_hidden_fees_include_processing_and_handling(self):
        from app.api import app

        client = TestClient(app)

        response = client.get("/products/1/total_cost")
        data = response.json()

        fee_types = [fee["type"] for fee in data["fees"]]
        assert "processing_fee" in fee_types
        assert "handling_fee" in fee_types
        assert "convenience_fee" in fee_types  # The worst kind!
