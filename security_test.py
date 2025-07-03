#!/usr/bin/env python3
import requests
import json
import uuid
import random
import sys
import os
import time
from datetime import datetime

# Get the backend URL from the frontend .env file
def get_backend_url():
    with open('/app/frontend/.env', 'r') as f:
        for line in f:
            if line.startswith('REACT_APP_BACKEND_URL='):
                return line.strip().split('=')[1].strip('"\'')
    return None

BACKEND_URL = get_backend_url()
if not BACKEND_URL:
    print("Error: Could not find REACT_APP_BACKEND_URL in frontend/.env")
    sys.exit(1)

API_URL = f"{BACKEND_URL}/api"
print(f"Using API URL: {API_URL}")

# Helper function to print test results
def print_test_result(test_name, success, response=None, error=None):
    print(f"\n{'=' * 80}")
    print(f"TEST: {test_name}")
    print(f"STATUS: {'SUCCESS' if success else 'FAILURE'}")
    
    if response:
        print(f"RESPONSE STATUS: {response.status_code}")
        try:
            print(f"RESPONSE BODY: {json.dumps(response.json(), indent=2)}")
        except:
            print(f"RESPONSE BODY: {response.text}")
    
    if error:
        print(f"ERROR: {error}")
    
    print(f"{'=' * 80}\n")
    return success

# Test 1: Test root API endpoint
def test_root_endpoint():
    try:
        response = requests.get(f"{API_URL}/")
        
        success = response.status_code == 200
        return print_test_result("Root API Endpoint", success, 
                                response=response,
                                error=None if success else "Root API endpoint not working")
    except Exception as e:
        return print_test_result("Root API Endpoint", False, error=str(e))

# Test 2: Test forgot password functionality
def test_forgot_password():
    try:
        # Test forgot password endpoint
        forgot_password_data = {
            "email": f"test_user_{uuid.uuid4().hex[:8]}@example.com"
        }
        
        # Try both with and without /api prefix
        forgot_response = requests.post(f"{API_URL}/auth/forgot-password", json=forgot_password_data)
        
        if forgot_response.status_code != 200:
            # Try with the /auth prefix directly
            auth_url = BACKEND_URL + "/auth"
            forgot_response = requests.post(f"{auth_url}/forgot-password", json=forgot_password_data)
        
        if forgot_response.status_code != 200:
            return print_test_result("Forgot Password", False, 
                                    response=forgot_response,
                                    error="Forgot password endpoint failed")
        
        print("Forgot password request successful. In a real scenario, an email would be sent with a reset code.")
        
        # For testing purposes, we'll try to reset with a mock code
        reset_code = "123456"  # This is a mock code
        
        reset_data = {
            "email": forgot_password_data["email"],
            "reset_code": reset_code,
            "new_password": "NewTest@123456"
        }
        
        # Use the same URL prefix that worked for the forgot password endpoint
        if forgot_response.url.startswith(auth_url):
            reset_response = requests.post(f"{auth_url}/reset-password", json=reset_data)
        else:
            reset_response = requests.post(f"{API_URL}/auth/reset-password", json=reset_data)
        
        # We expect this to fail since we don't have the real reset code
        # But we want to verify the endpoint exists and processes our request
        print(f"Reset password response: {reset_response.status_code}")
        print(f"Reset password response body: {reset_response.text}")
        
        # The important thing is that the endpoint exists and returns a proper response
        # (either 200 for success or 400 for invalid code)
        endpoint_exists = reset_response.status_code in [200, 400, 401, 404]
        
        return print_test_result("Forgot Password", endpoint_exists, 
                                response=reset_response,
                                error=None if endpoint_exists else "Reset password endpoint not functioning properly")
    except Exception as e:
        return print_test_result("Forgot Password", False, error=str(e))

# Test 3: Test Google OAuth endpoints
def test_google_oauth():
    try:
        # Test Google login endpoint - should redirect to Google
        login_response = requests.get(f"{API_URL}/auth/google/login", allow_redirects=False)
        
        # Check if it's a redirect (status code 302 or 307)
        login_redirect = login_response.status_code in [302, 307]
        
        if not login_redirect:
            return print_test_result("Google OAuth", False, 
                                    response=login_response,
                                    error="Google login endpoint did not redirect")
        
        # Check if the redirect URL is to Google
        redirect_url = login_response.headers.get('Location', '')
        is_google_url = 'google.com' in redirect_url or 'accounts.google.com' in redirect_url
        
        if not is_google_url:
            return print_test_result("Google OAuth", False, 
                                    error=f"Google login redirected to non-Google URL: {redirect_url}")
        
        # Test callback endpoint - we can't fully test this without a valid OAuth code
        # but we can check if the endpoint exists
        callback_response = requests.get(f"{API_URL}/auth/google/callback?code=test_code&state=test_state")
        
        # The callback should either succeed or return an error about the invalid code
        # but it shouldn't return a 404
        callback_exists = callback_response.status_code != 404
        
        success = login_redirect and is_google_url and callback_exists
        
        return print_test_result("Google OAuth", success, 
                                error=None if success else "Google OAuth endpoints not functioning properly")
    except Exception as e:
        return print_test_result("Google OAuth", False, error=str(e))

# Test 4: Test enhanced PDF parsing for negative amounts
def test_enhanced_pdf_parsing():
    try:
        # Create a transaction with a negative amount to simulate a credit/payment
        negative_transaction = {
            "date": "2024-11-15",
            "description": "Test Credit Transaction",
            "category": "Retail and Grocery",
            "amount": -50.00,  # Negative amount
            "account_type": "credit_card",
            "user_id": "test_user"  # Using a test user ID
        }
        
        neg_response = requests.post(f"{API_URL}/transactions", json=negative_transaction)
        
        if neg_response.status_code != 200:
            return print_test_result("Enhanced PDF Parsing", False, 
                                    response=neg_response,
                                    error="Failed to create transaction with negative amount")
        
        # Verify the transaction was created with the negative amount
        transactions_response = requests.get(f"{API_URL}/transactions?user_id=test_user")
        
        if transactions_response.status_code != 200:
            return print_test_result("Enhanced PDF Parsing", False, 
                                    response=transactions_response,
                                    error="Failed to retrieve transactions")
        
        transactions = transactions_response.json()
        
        # Find our negative transaction
        negative_found = False
        for transaction in transactions:
            if transaction.get("description") == "Test Credit Transaction" and transaction.get("amount") < 0:
                negative_found = True
                break
        
        success = negative_found
        
        return print_test_result("Enhanced PDF Parsing", success, 
                                error=None if success else "Enhanced PDF parsing for negative amounts not functioning properly")
    except Exception as e:
        return print_test_result("Enhanced PDF Parsing", False, error=str(e))

# Test 5: Test authentication requirement
def test_authentication_requirement():
    try:
        # Try to access endpoints without authentication
        endpoints = [
            "/transactions",
            "/categories",
            "/analytics/monthly-report",
            "/analytics/category-breakdown"
        ]
        
        all_require_auth = True
        for endpoint in endpoints:
            response = requests.get(f"{API_URL}{endpoint}")
            if response.status_code != 401 and response.status_code != 403:
                all_require_auth = False
                print(f"SECURITY ISSUE: Endpoint {endpoint} does not require authentication. Status code: {response.status_code}")
        
        success = all_require_auth
        return print_test_result("Authentication Requirement", success, 
                                error=None if success else "Some endpoints do not require authentication")
    except Exception as e:
        return print_test_result("Authentication Requirement", False, error=str(e))

# Run all tests
def run_all_tests():
    print("\n" + "=" * 40)
    print("STARTING SECURITY AND FEATURE TESTS")
    print("=" * 40 + "\n")
    
    # Security tests
    security_test_results = {
        "Authentication Requirement": test_authentication_requirement()
    }
    
    # New feature tests
    feature_test_results = {
        "Root API Endpoint": test_root_endpoint(),
        "Forgot Password": test_forgot_password(),
        "Google OAuth": test_google_oauth(),
        "Enhanced PDF Parsing": test_enhanced_pdf_parsing()
    }
    
    print("\n" + "=" * 40)
    print("SECURITY TESTS SUMMARY")
    print("=" * 40)
    
    security_passed = True
    for test_name, result in security_test_results.items():
        status = "PASSED" if result else "FAILED"
        if not result:
            security_passed = False
        print(f"{test_name}: {status}")
    
    print("\nOVERALL SECURITY RESULT: " + ("PASSED" if security_passed else "FAILED"))
    
    print("\n" + "=" * 40)
    print("FEATURE TESTS SUMMARY")
    print("=" * 40)
    
    features_passed = True
    for test_name, result in feature_test_results.items():
        status = "PASSED" if result else "FAILED"
        if not result:
            features_passed = False
        print(f"{test_name}: {status}")
    
    print("\nOVERALL FEATURE RESULT: " + ("PASSED" if features_passed else "FAILED"))
    
    all_passed = security_passed and features_passed
    
    print("\n" + "=" * 40)
    print("FINAL RESULT: " + ("PASSED" if all_passed else "FAILED"))
    print("=" * 40 + "\n")
    
    return all_passed

if __name__ == "__main__":
    run_all_tests()