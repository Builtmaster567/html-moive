#!/usr/bin/env python3
import requests

# Test the proxy
print("Testing proxy server...")
print("=" * 50)

# Test 1: Health check
try:
    resp = requests.get("http://localhost:5000/health")
    print(f"✓ Health check: {resp.json()}")
except Exception as e:
    print(f"✗ Health check failed: {e}")

# Test 2: Main page
try:
    resp = requests.get("http://localhost:5000/")
    print(f"✓ Main page loads: {len(resp.text)} bytes")
except Exception as e:
    print(f"✗ Main page failed: {e}")

# Test 3: Proxy example.com
try:
    resp = requests.get("http://localhost:5000/proxy/https%3A%2F%2Fexample.com")
    print(f"✓ Proxy works: {len(resp.text)} bytes, status {resp.status_code}")
    if "Example Domain" in resp.text:
        print("✓ Content correct!")
except Exception as e:
    print(f"✗ Proxy failed: {e}")

print("=" * 50)
print("All tests completed!")
