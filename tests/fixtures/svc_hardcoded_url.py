# Fixture for SVC-001: HardcodedServiceURL
import requests

# BAD: hardcoded localhost URL
def fetch_users():
    return requests.get("http://localhost:8080/api/users", timeout=5)

# BAD: hardcoded 127.0.0.1
def fetch_orders():
    return requests.get("http://127.0.0.1:3000/orders", timeout=5)

# GOOD: URL from config
def fetch_products(base_url):
    return requests.get(f"{base_url}/products", timeout=5)

