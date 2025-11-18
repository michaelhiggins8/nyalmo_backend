#!/usr/bin/env python3
"""Test script for fetch_rulings endpoint"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_routes():
    """Test that the fetch_rulings route is registered"""
    routes = [route.path for route in app.routes]
    print("Registered routes:")
    for route in sorted(routes):
        print(f"  {route}")
    
    if "/fetch_rulings" in routes:
        print("\n✓ /fetch_rulings route is registered")
    else:
        print("\n✗ /fetch_rulings route is NOT registered")

def test_endpoint_without_auth():
    """Test endpoint without authentication (should return 401)"""
    print("\nTesting /fetch_rulings without authentication:")
    response = client.get("/fetch_rulings")
    print(f"  Status code: {response.status_code}")
    print(f"  Response: {response.json()}")

if __name__ == "__main__":
    test_routes()
    test_endpoint_without_auth()

