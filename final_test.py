#!/usr/bin/env python3
"""Final verification test for the proxy browser"""
import requests
import sys

print("=" * 60)
print("PROXY BROWSER - FINAL VERIFICATION TEST")
print("=" * 60)

tests_passed = 0
tests_failed = 0

def test(name, url, expected_status=200, check_content=None):
    global tests_passed, tests_failed
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == expected_status:
            if check_content is None or check_content in resp.text:
                print(f"✓ {name}")
                tests_passed += 1
                return True
            else:
                print(f"✗ {name} - Content check failed")
                tests_failed += 1
                return False
        else:
            print(f"✗ {name} - Status {resp.status_code} (expected {expected_status})")
            tests_failed += 1
            return False
    except Exception as e:
        print(f"✗ {name} - Error: {e}")
        tests_failed += 1
        return False

# Run tests
test("Health Check", "http://localhost:5000/health", check_content="healthy")
test("Main Page (/)", "http://localhost:5000/", check_content="Proxy Browser")
test("Catch-all Route (/test)", "http://localhost:5000/test", check_content="Proxy Browser")
test("Catch-all Route (/foo/bar)", "http://localhost:5000/foo/bar", check_content="Proxy Browser")
test("Proxy example.com", "http://localhost:5000/proxy/https%3A%2F%2Fexample.com", check_content="Example Domain")
test("Proxy info.cern.ch", "http://localhost:5000/proxy/https%3A%2F%2Finfo.cern.ch", check_content="first website")

print("=" * 60)
print(f"RESULTS: {tests_passed} passed, {tests_failed} failed")
print("=" * 60)

if tests_failed == 0:
    print("\n✅ ALL TESTS PASSED! Proxy browser is fully functional.")
    sys.exit(0)
else:
    print(f"\n❌ {tests_failed} test(s) failed.")
    sys.exit(1)
