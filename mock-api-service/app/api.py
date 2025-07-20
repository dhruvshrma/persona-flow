from fastapi import FastAPI, HTTPException
from typing import List, Dict, Any
import time

app = FastAPI(title="Mock API Service", description="API with strategic flaws for persona testing")

# In-memory storage for cart state tracking
cart_add_count = 0
cart_items = []

# Mock product data
PRODUCTS = [
    {
        "id": 1,
        "name": "Gaming Laptop",
        "price": 1299.99,
        "description": "High-performance gaming laptop with RTX graphics",
        "category": "Electronics"
    },
    {
        "id": 2,
        "name": "Wireless Mouse",
        "price": 29.99,
        "description": "Ergonomic wireless mouse with precision tracking",
        "category": "Accessories"
    },
    {
        "id": 3,
        "name": "Mechanical Keyboard",
        "price": 149.99,
        "description": "RGB mechanical keyboard with tactile switches",
        "category": "Accessories"
    },
    {
        "id": 4,
        "name": "4K Monitor",
        "price": 399.99,
        "description": "27-inch 4K UHD monitor with HDR support",
        "category": "Electronics"
    },
    {
        "id": 5,
        "name": "USB-C Hub",
        "price": 79.99,
        "description": "Multi-port USB-C hub with HDMI and Ethernet",
        "category": "Accessories"
    }
]


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "mock-api"
    }


@app.get("/products")
async def get_products():
    return {
        "products": PRODUCTS,
        "total": len(PRODUCTS),
        "page": 1,
        "per_page": 10
    }


@app.get("/search")
async def search_products(q: str):
    # INTENTIONAL FLAW: Case-sensitive search
    results = [
        product for product in PRODUCTS
        if q in product["name"]  # No .lower() - case sensitive!
    ]
    
    return {
        "results": results,
        "query": q,
        "total": len(results)
    }


@app.post("/cart/add")
async def add_to_cart(item: Dict[str, Any]):
    """FLAWED endpoint - inconsistent response format (confuses developers)"""
    global cart_add_count, cart_items
    
    cart_add_count += 1
    cart_items.append(item)
    
    if cart_add_count == 1:
        # FIRST CALL: Return full cart object
        return {
            "cart": {
                "items": cart_items,
                "total_items": len(cart_items)
            }
        }
    else:
        # SUBSEQUENT CALLS: Return just a message (INCONSISTENT!)
        return {
            "message": "Item added to cart successfully"
        }


@app.get("/cart")
async def get_cart():
    # INTENTIONAL FLAW: Artificial delay
    time.sleep(2.5)  # Frustratingly slow!
    
    return {
        "items": cart_items,
        "total": len(cart_items),
        "message": "Cart loaded successfully"
    }


@app.post("/checkout")
async def checkout(checkout_data: Dict[str, Any]):
    # Intentional flaw: Required fields not documented in API spec. 
    required_fields = ["shipping_address", "billing_address", "tax_id"]
    missing_fields = []
    
    for field in required_fields:
        if field not in checkout_data:
            missing_fields.append(field)
    
    if missing_fields:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Missing required fields",
                "required_fields": required_fields,
                "missing": missing_fields
            }
        )
    
    return {"message": "Checkout successful", "order_id": "12345"}


@app.get("/admin/users")
async def admin_users():
    # Intentional flaw: Accessible endpoint that reveals system info in error
    raise HTTPException(
        status_code=403,
        detail="Access denied. Admin database connection requires elevated privileges. Contact system administrator for user table access."
    )


@app.get("/products/{product_id}/total_cost")
async def get_product_total_cost(product_id: int):
    # Intentional flaw: Reveals hidden fees (frustrates budget-conscious users)
    product = next((p for p in PRODUCTS if p["id"] == product_id), None)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    base_price = product["price"]
    
    # Intentional flaw: Hidden fees revealed only when explicitly requested
    fees = [
        {"type": "processing_fee", "amount": base_price * 0.03},
        {"type": "handling_fee", "amount": 5.99},
        {"type": "convenience_fee", "amount": 2.50}  # The worst!
    ]
    
    total_fees = sum(fee["amount"] for fee in fees)
    
    return {
        "product_id": product_id,
        "base_price": base_price,
        "fees": fees,
        "total_cost": base_price + total_fees
    }