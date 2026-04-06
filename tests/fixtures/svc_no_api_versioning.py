# Fixture for SVC-003: NoAPIVersioning
from fastapi import FastAPI

app = FastAPI()

# BAD: no version prefix
@app.get("/users")
async def list_users():
    return []

# BAD: no version prefix
@app.post("/orders")
async def create_order():
    return {}

# GOOD: versioned
@app.get("/v1/products")
async def list_products():
    return []

# GOOD: health check exempt
@app.get("/health")
async def health():
    return {"status": "ok"}

