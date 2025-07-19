"""
Advanced strategic flaws for testing different persona types
"""
import pytest
import time
from fastapi.testclient import TestClient


class TestPerformanceFlaws:
    """Test endpoints with performance issues - frustrates efficiency-focused users"""
    
    def test_cart_endpoint_is_artificially_slow(self):
        """FLAW: Cart endpoint should be slow (tests patience)"""
        from app.api import app
        client = TestClient(app)
        
        start_time = time.time()
        response = client.get("/cart")
        duration = time.time() - start_time
        
        assert response.status_code == 200
        assert duration > 2.0  # Should take at least 2 seconds (artificial delay)
        
    def test_slow_cart_returns_proper_data(self):
        """Cart should return proper data despite being slow"""
        from app.api import app
        client = TestClient(app)
        
        response = client.get("/cart")
        data = response.json()
        assert "items" in data
        assert "total" in data


class TestHiddenComplexityFlaws:
    """Test endpoints with hidden required fields - blocks task completion"""
    
    def test_checkout_fails_without_hidden_fields(self):
        """FLAW: Checkout requires undocumented fields"""
        from app.api import app
        client = TestClient(app)
        
        # Simple checkout attempt should fail
        response = client.post("/checkout", json={"payment_method": "card"})
        assert response.status_code == 400
        
    def test_checkout_error_reveals_hidden_requirements(self):
        """Error should reveal the hidden required fields"""
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
    """Test missing features that frustrate developer-type users"""
    
    def test_bulk_operations_not_supported(self):
        """FLAW: No bulk cart operations (developers expect this)"""
        from app.api import app
        client = TestClient(app)
        
        response = client.post("/cart/bulk_add", json={"products": [1, 2, 3]})
        assert response.status_code == 404  # Not implemented!
        
    def test_no_api_versioning(self):
        """FLAW: No API versioning support"""
        from app.api import app
        client = TestClient(app)
        
        response = client.get("/v2/products")
        assert response.status_code == 404  # No versioning!


class TestSecurityGaps:
    """Test security issues that security-minded users will discover"""
    
    def test_admin_endpoint_has_weak_permissions(self):
        """FLAW: Admin endpoint accessible without proper auth"""
        from app.api import app
        client = TestClient(app)
        
        # Should be protected but isn't properly
        response = client.get("/admin/users")
        assert response.status_code == 403  # Forbidden, but reveals endpoint exists
        
    def test_admin_error_leaks_information(self):
        """Security flaw: Error messages leak system information"""
        from app.api import app
        client = TestClient(app)
        
        response = client.get("/admin/users")
        data = response.json()
        assert "detail" in data
        # Should leak information about the system
        assert "database" in data["detail"].lower() or "admin" in data["detail"].lower()


class TestPricingFlaws:
    """Test hidden costs that frustrate budget-conscious users"""
    
    def test_products_hide_additional_fees(self):
        """FLAW: Products don't show total cost with fees"""
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
        """Budget users discover multiple hidden fees"""
        from app.api import app
        client = TestClient(app)
        
        response = client.get("/products/1/total_cost")
        data = response.json()
        
        fee_types = [fee["type"] for fee in data["fees"]]
        assert "processing_fee" in fee_types
        assert "handling_fee" in fee_types
        assert "convenience_fee" in fee_types  # The worst kind!