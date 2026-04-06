# Fixture for SVC-002: ChattyIntegration
import requests


# BAD: 4 sequential HTTP calls in one function
def sync_user_profile(user_id, base_url):
    user = requests.get(f"{base_url}/users/{user_id}", timeout=5)
    orders = requests.get(f"{base_url}/orders?user={user_id}", timeout=5)
    prefs = requests.get(f"{base_url}/preferences/{user_id}", timeout=5)
    history = requests.get(f"{base_url}/history/{user_id}", timeout=5)
    return {**user.json(), **orders.json(), **prefs.json(), **history.json()}


# GOOD: single call
def get_user(user_id, base_url):
    return requests.get(f"{base_url}/users/{user_id}", timeout=5)
