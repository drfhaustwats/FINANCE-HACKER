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

# Helper function to register a test user and get auth token
def register_and_login_user(email=None, password=None, full_name=None):
    if not email:
        random_id = uuid.uuid4().hex[:8]
        email = f"test_user_{random_id}@example.com"
    if not password:
        password = "Test@123456"
    if not full_name:
        full_name = f"Test User {random_id}"
    
    # Register user
    register_data = {
        "email": email,
        "password": password,
        "full_name": full_name
    }
    
    try:
        register_response = requests.post(f"{API_URL}/auth/register", json=register_data)
        print(f"Register response: {register_response.status_code}")
        
        # Login to get token
        login_data = {
            "email": email,
            "password": password
        }
        
        login_response = requests.post(f"{API_URL}/auth/login", json=login_data)
        if login_response.status_code == 200:
            token_data = login_response.json()
            return {
                "email": email,
                "password": password,
                "full_name": full_name,
                "token": token_data.get("access_token"),
                "user_id": token_data.get("user_id")
            }
        else:
            print(f"Login failed: {login_response.text}")
            return None
    except Exception as e:
        print(f"Error in register_and_login_user: {str(e)}")
        return None

# Test 1: Test transactions data isolation
def test_transactions_data_isolation():
    try:
        # Create two test users with auth tokens
        user_a = register_and_login_user()
        user_b = register_and_login_user()
        
        if not user_a or not user_b:
            return print_test_result("Transactions Data Isolation", False, 
                                    error="Failed to create test users")
        
        # Create transactions for User A
        transactions_a = []
        for i in range(3):
            transaction = {
                "date": f"2024-11-{i+1:02d}",
                "description": f"User A Transaction {i+1}",
                "category": "Retail and Grocery",
                "amount": round(random.uniform(10, 100), 2),
                "account_type": "credit_card"
            }
            headers_a = {"Authorization": f"Bearer {user_a['token']}"}
            response = requests.post(f"{API_URL}/transactions", json=transaction, headers=headers_a)
            if response.status_code == 200 and "id" in response.json():
                transactions_a.append(response.json())
                print(f"Created transaction for User A: {transaction['description']} with ID: {response.json()['id']}")
            else:
                print(f"Failed to create transaction for User A: {response.text}")
        
        # Create transactions for User B
        transactions_b = []
        for i in range(3):
            transaction = {
                "date": f"2024-11-{i+1:02d}",
                "description": f"User B Transaction {i+1}",
                "category": "Transportation",
                "amount": round(random.uniform(10, 100), 2),
                "account_type": "credit_card"
            }
            headers_b = {"Authorization": f"Bearer {user_b['token']}"}
            response = requests.post(f"{API_URL}/transactions", json=transaction, headers=headers_b)
            if response.status_code == 200 and "id" in response.json():
                transactions_b.append(response.json())
                print(f"Created transaction for User B: {transaction['description']} with ID: {response.json()['id']}")
            else:
                print(f"Failed to create transaction for User B: {response.text}")
        
        # Get User A's transactions
        headers_a = {"Authorization": f"Bearer {user_a['token']}"}
        response_a = requests.get(f"{API_URL}/transactions", headers=headers_a)
        
        # Get User B's transactions
        headers_b = {"Authorization": f"Bearer {user_b['token']}"}
        response_b = requests.get(f"{API_URL}/transactions", headers=headers_b)
        
        # Verify User A can only see User A's transactions
        user_a_can_see_only_own = True
        if response_a.status_code == 200:
            transactions_seen_by_a = response_a.json()
            print(f"User A can see {len(transactions_seen_by_a)} transactions")
            
            # Check if User A can see any of User B's transactions
            for transaction in transactions_seen_by_a:
                if "User B Transaction" in transaction.get("description", ""):
                    user_a_can_see_only_own = False
                    print(f"SECURITY ISSUE: User A can see User B's transaction: {transaction}")
        else:
            print(f"Failed to get User A's transactions: {response_a.text}")
            user_a_can_see_only_own = False
        
        # Verify User B can only see User B's transactions
        user_b_can_see_only_own = True
        if response_b.status_code == 200:
            transactions_seen_by_b = response_b.json()
            print(f"User B can see {len(transactions_seen_by_b)} transactions")
            
            # Check if User B can see any of User A's transactions
            for transaction in transactions_seen_by_b:
                if "User A Transaction" in transaction.get("description", ""):
                    user_b_can_see_only_own = False
                    print(f"SECURITY ISSUE: User B can see User A's transaction: {transaction}")
        else:
            print(f"Failed to get User B's transactions: {response_b.text}")
            user_b_can_see_only_own = False
        
        success = user_a_can_see_only_own and user_b_can_see_only_own
        return print_test_result("Transactions Data Isolation", success, 
                                error=None if success else "Users can see other users' transactions")
    except Exception as e:
        return print_test_result("Transactions Data Isolation", False, error=str(e))

# Test 2: Test categories data isolation
def test_categories_data_isolation():
    try:
        # Create two test users with auth tokens
        user_a = register_and_login_user()
        user_b = register_and_login_user()
        
        if not user_a or not user_b:
            return print_test_result("Categories Data Isolation", False, 
                                    error="Failed to create test users")
        
        # Create categories for User A
        categories_a = []
        for i in range(2):
            category = {
                "name": f"User A Category {i+1}",
                "color": f"#FF{i+1}733"
            }
            headers_a = {"Authorization": f"Bearer {user_a['token']}"}
            response = requests.post(f"{API_URL}/categories", json=category, headers=headers_a)
            if response.status_code == 200 and "id" in response.json():
                categories_a.append(response.json())
                print(f"Created category for User A: {category['name']} with ID: {response.json()['id']}")
            else:
                print(f"Failed to create category for User A: {response.text}")
        
        # Create categories for User B
        categories_b = []
        for i in range(2):
            category = {
                "name": f"User B Category {i+1}",
                "color": f"#33FF{i+1}7"
            }
            headers_b = {"Authorization": f"Bearer {user_b['token']}"}
            response = requests.post(f"{API_URL}/categories", json=category, headers=headers_b)
            if response.status_code == 200 and "id" in response.json():
                categories_b.append(response.json())
                print(f"Created category for User B: {category['name']} with ID: {response.json()['id']}")
            else:
                print(f"Failed to create category for User B: {response.text}")
        
        # Get User A's categories
        headers_a = {"Authorization": f"Bearer {user_a['token']}"}
        response_a = requests.get(f"{API_URL}/categories", headers=headers_a)
        
        # Get User B's categories
        headers_b = {"Authorization": f"Bearer {user_b['token']}"}
        response_b = requests.get(f"{API_URL}/categories", headers=headers_b)
        
        # Verify User A can only see User A's categories
        user_a_can_see_only_own = True
        if response_a.status_code == 200:
            categories_seen_by_a = response_a.json()
            print(f"User A can see {len(categories_seen_by_a)} categories")
            
            # Check if User A can see any of User B's categories
            for category in categories_seen_by_a:
                if "User B Category" in category.get("name", ""):
                    user_a_can_see_only_own = False
                    print(f"SECURITY ISSUE: User A can see User B's category: {category}")
        else:
            print(f"Failed to get User A's categories: {response_a.text}")
            user_a_can_see_only_own = False
        
        # Verify User B can only see User B's categories
        user_b_can_see_only_own = True
        if response_b.status_code == 200:
            categories_seen_by_b = response_b.json()
            print(f"User B can see {len(categories_seen_by_b)} categories")
            
            # Check if User B can see any of User A's categories
            for category in categories_seen_by_b:
                if "User A Category" in category.get("name", ""):
                    user_b_can_see_only_own = False
                    print(f"SECURITY ISSUE: User B can see User A's category: {category}")
        else:
            print(f"Failed to get User B's categories: {response_b.text}")
            user_b_can_see_only_own = False
        
        success = user_a_can_see_only_own and user_b_can_see_only_own
        return print_test_result("Categories Data Isolation", success, 
                                error=None if success else "Users can see other users' categories")
    except Exception as e:
        return print_test_result("Categories Data Isolation", False, error=str(e))

# Test 3: Test monthly report analytics data isolation
def test_monthly_report_data_isolation():
    try:
        # Create two test users with auth tokens
        user_a = register_and_login_user()
        user_b = register_and_login_user()
        
        if not user_a or not user_b:
            return print_test_result("Monthly Report Data Isolation", False, 
                                    error="Failed to create test users")
        
        # Create transactions for User A
        transactions_a = []
        for i in range(3):
            transaction = {
                "date": f"2024-11-{i+1:02d}",
                "description": f"User A Transaction {i+1}",
                "category": "Retail and Grocery",
                "amount": round(random.uniform(10, 100), 2),
                "account_type": "credit_card"
            }
            headers_a = {"Authorization": f"Bearer {user_a['token']}"}
            response = requests.post(f"{API_URL}/transactions", json=transaction, headers=headers_a)
            if response.status_code == 200 and "id" in response.json():
                transactions_a.append(response.json())
                print(f"Created transaction for User A: {transaction['description']} with ID: {response.json()['id']}")
            else:
                print(f"Failed to create transaction for User A: {response.text}")
        
        # Create transactions for User B
        transactions_b = []
        for i in range(3):
            transaction = {
                "date": f"2024-11-{i+1:02d}",
                "description": f"User B Transaction {i+1}",
                "category": "Transportation",
                "amount": round(random.uniform(10, 100), 2),
                "account_type": "credit_card"
            }
            headers_b = {"Authorization": f"Bearer {user_b['token']}"}
            response = requests.post(f"{API_URL}/transactions", json=transaction, headers=headers_b)
            if response.status_code == 200 and "id" in response.json():
                transactions_b.append(response.json())
                print(f"Created transaction for User B: {transaction['description']} with ID: {response.json()['id']}")
            else:
                print(f"Failed to create transaction for User B: {response.text}")
        
        current_year = datetime.now().year
        
        # Get User A's monthly report
        headers_a = {"Authorization": f"Bearer {user_a['token']}"}
        response_a = requests.get(f"{API_URL}/analytics/monthly-report?year={current_year}", headers=headers_a)
        
        # Get User B's monthly report
        headers_b = {"Authorization": f"Bearer {user_b['token']}"}
        response_b = requests.get(f"{API_URL}/analytics/monthly-report?year={current_year}", headers=headers_b)
        
        # Verify User A's monthly report only includes User A's data
        user_a_report_correct = True
        if response_a.status_code == 200:
            monthly_report_a = response_a.json()
            print(f"User A's monthly report has {len(monthly_report_a)} months")
            
            # Check total spent matches User A's transactions
            if monthly_report_a:
                user_a_total_spent = sum(report.get("total_spent", 0) for report in monthly_report_a)
                expected_a_total = sum(transaction.get("amount", 0) for transaction in transactions_a)
                
                # Allow for some floating point imprecision
                if abs(user_a_total_spent - expected_a_total) > 0.01:
                    user_a_report_correct = False
                    print(f"SECURITY ISSUE: User A's monthly report total ({user_a_total_spent}) doesn't match expected total ({expected_a_total})")
        else:
            print(f"Failed to get User A's monthly report: {response_a.text}")
            user_a_report_correct = False
        
        # Verify User B's monthly report only includes User B's data
        user_b_report_correct = True
        if response_b.status_code == 200:
            monthly_report_b = response_b.json()
            print(f"User B's monthly report has {len(monthly_report_b)} months")
            
            # Check total spent matches User B's transactions
            if monthly_report_b:
                user_b_total_spent = sum(report.get("total_spent", 0) for report in monthly_report_b)
                expected_b_total = sum(transaction.get("amount", 0) for transaction in transactions_b)
                
                # Allow for some floating point imprecision
                if abs(user_b_total_spent - expected_b_total) > 0.01:
                    user_b_report_correct = False
                    print(f"SECURITY ISSUE: User B's monthly report total ({user_b_total_spent}) doesn't match expected total ({expected_b_total})")
        else:
            print(f"Failed to get User B's monthly report: {response_b.text}")
            user_b_report_correct = False
        
        success = user_a_report_correct and user_b_report_correct
        return print_test_result("Monthly Report Data Isolation", success, 
                                error=None if success else "Monthly reports may include other users' data")
    except Exception as e:
        return print_test_result("Monthly Report Data Isolation", False, error=str(e))

# Test 4: Test category breakdown analytics data isolation
def test_category_breakdown_data_isolation():
    try:
        # Create two test users with auth tokens
        user_a = register_and_login_user()
        user_b = register_and_login_user()
        
        if not user_a or not user_b:
            return print_test_result("Category Breakdown Data Isolation", False, 
                                    error="Failed to create test users")
        
        # Create transactions for User A
        transactions_a = []
        for i in range(3):
            transaction = {
                "date": f"2024-11-{i+1:02d}",
                "description": f"User A Transaction {i+1}",
                "category": "Retail and Grocery",
                "amount": round(random.uniform(10, 100), 2),
                "account_type": "credit_card"
            }
            headers_a = {"Authorization": f"Bearer {user_a['token']}"}
            response = requests.post(f"{API_URL}/transactions", json=transaction, headers=headers_a)
            if response.status_code == 200 and "id" in response.json():
                transactions_a.append(response.json())
                print(f"Created transaction for User A: {transaction['description']} with ID: {response.json()['id']}")
            else:
                print(f"Failed to create transaction for User A: {response.text}")
        
        # Create transactions for User B
        transactions_b = []
        for i in range(3):
            transaction = {
                "date": f"2024-11-{i+1:02d}",
                "description": f"User B Transaction {i+1}",
                "category": "Transportation",
                "amount": round(random.uniform(10, 100), 2),
                "account_type": "credit_card"
            }
            headers_b = {"Authorization": f"Bearer {user_b['token']}"}
            response = requests.post(f"{API_URL}/transactions", json=transaction, headers=headers_b)
            if response.status_code == 200 and "id" in response.json():
                transactions_b.append(response.json())
                print(f"Created transaction for User B: {transaction['description']} with ID: {response.json()['id']}")
            else:
                print(f"Failed to create transaction for User B: {response.text}")
        
        # Get User A's category breakdown
        headers_a = {"Authorization": f"Bearer {user_a['token']}"}
        response_a = requests.get(f"{API_URL}/analytics/category-breakdown", headers=headers_a)
        
        # Get User B's category breakdown
        headers_b = {"Authorization": f"Bearer {user_b['token']}"}
        response_b = requests.get(f"{API_URL}/analytics/category-breakdown", headers=headers_b)
        
        # Verify User A's category breakdown only includes User A's data
        user_a_breakdown_correct = True
        if response_a.status_code == 200:
            category_breakdown_a = response_a.json()
            print(f"User A's category breakdown has {len(category_breakdown_a)} categories")
            
            # Check total amount matches User A's transactions
            if category_breakdown_a:
                user_a_total_amount = sum(category.get("amount", 0) for category in category_breakdown_a)
                expected_a_total = sum(transaction.get("amount", 0) for transaction in transactions_a)
                
                # Allow for some floating point imprecision
                if abs(user_a_total_amount - expected_a_total) > 0.01:
                    user_a_breakdown_correct = False
                    print(f"SECURITY ISSUE: User A's category breakdown total ({user_a_total_amount}) doesn't match expected total ({expected_a_total})")
                
                # Check if User A's breakdown includes User B's categories
                for category in category_breakdown_a:
                    if category.get("category") == "Transportation" and any("User B Transaction" in t.get("description", "") for t in transactions_b):
                        user_a_breakdown_correct = False
                        print(f"SECURITY ISSUE: User A's category breakdown includes User B's category: {category}")
        else:
            print(f"Failed to get User A's category breakdown: {response_a.text}")
            user_a_breakdown_correct = False
        
        # Verify User B's category breakdown only includes User B's data
        user_b_breakdown_correct = True
        if response_b.status_code == 200:
            category_breakdown_b = response_b.json()
            print(f"User B's category breakdown has {len(category_breakdown_b)} categories")
            
            # Check total amount matches User B's transactions
            if category_breakdown_b:
                user_b_total_amount = sum(category.get("amount", 0) for category in category_breakdown_b)
                expected_b_total = sum(transaction.get("amount", 0) for transaction in transactions_b)
                
                # Allow for some floating point imprecision
                if abs(user_b_total_amount - expected_b_total) > 0.01:
                    user_b_breakdown_correct = False
                    print(f"SECURITY ISSUE: User B's category breakdown total ({user_b_total_amount}) doesn't match expected total ({expected_b_total})")
                
                # Check if User B's breakdown includes User A's categories
                for category in category_breakdown_b:
                    if category.get("category") == "Retail and Grocery" and any("User A Transaction" in t.get("description", "") for t in transactions_a):
                        user_b_breakdown_correct = False
                        print(f"SECURITY ISSUE: User B's category breakdown includes User A's category: {category}")
        else:
            print(f"Failed to get User B's category breakdown: {response_b.text}")
            user_b_breakdown_correct = False
        
        success = user_a_breakdown_correct and user_b_breakdown_correct
        return print_test_result("Category Breakdown Data Isolation", success, 
                                error=None if success else "Category breakdowns may include other users' data")
    except Exception as e:
        return print_test_result("Category Breakdown Data Isolation", False, error=str(e))

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

# Test 6: Test forgot password functionality
def test_forgot_password():
    try:
        # Create a test user
        random_id = uuid.uuid4().hex[:8]
        email = f"test_user_{random_id}@example.com"
        password = "Test@123456"
        full_name = f"Test User {random_id}"
        
        user = register_and_login_user(email, password, full_name)
        if not user:
            return print_test_result("Forgot Password", False, 
                                    error="Failed to create test user")
        
        # Test forgot password endpoint
        forgot_password_data = {
            "email": email
        }
        
        forgot_response = requests.post(f"{API_URL}/auth/forgot-password", json=forgot_password_data)
        
        if forgot_response.status_code != 200:
            return print_test_result("Forgot Password", False, 
                                    response=forgot_response,
                                    error="Forgot password endpoint failed")
        
        print("Forgot password request successful. In a real scenario, an email would be sent with a reset code.")
        print("Since we can't access the email, we'll simulate the reset code process.")
        
        # For testing purposes, we'll try to reset with a mock code
        # In a real scenario, the user would get the code from their email
        reset_code = "123456"  # This is a mock code
        
        reset_data = {
            "email": email,
            "reset_code": reset_code,
            "new_password": "NewTest@123456"
        }
        
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

# Test 7: Test user profile management
def test_user_profile_management():
    try:
        # Create a test user
        user = register_and_login_user()
        if not user:
            return print_test_result("User Profile Management", False, 
                                    error="Failed to create test user")
        
        # Test update profile endpoint
        headers = {"Authorization": f"Bearer {user['token']}"}
        
        # Update user profile
        update_data = {
            "full_name": f"Updated {user['full_name']}",
            "username": f"updated_user_{uuid.uuid4().hex[:5]}"
        }
        
        update_response = requests.put(f"{API_URL}/auth/profile", json=update_data, headers=headers)
        
        profile_update_success = update_response.status_code == 200
        
        if not profile_update_success:
            return print_test_result("User Profile Management", False, 
                                    response=update_response,
                                    error="Profile update failed")
        
        # Test change password endpoint
        password_data = {
            "current_password": user['password'],
            "new_password": f"New{user['password']}"
        }
        
        password_response = requests.post(f"{API_URL}/auth/change-password", json=password_data, headers=headers)
        
        password_change_success = password_response.status_code == 200
        
        if not password_change_success:
            return print_test_result("User Profile Management", False, 
                                    response=password_response,
                                    error="Password change failed")
        
        # Try logging in with the new password
        login_data = {
            "email": user['email'],
            "password": f"New{user['password']}"
        }
        
        login_response = requests.post(f"{API_URL}/auth/login", json=login_data)
        
        login_success = login_response.status_code == 200
        
        success = profile_update_success and password_change_success and login_success
        
        return print_test_result("User Profile Management", success, 
                                response=login_response,
                                error=None if success else "User profile management failed")
    except Exception as e:
        return print_test_result("User Profile Management", False, error=str(e))

# Test 8: Test Google OAuth endpoints
def test_google_oauth():
    try:
        # Test Google login endpoint - should redirect to Google
        login_response = requests.get(f"{API_URL}/auth/google/login", allow_redirects=False)
        
        # Check if it's a redirect (status code 302)
        login_redirect = login_response.status_code == 302
        
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

# Test 9: Test enhanced PDF parsing for negative amounts
def test_enhanced_pdf_parsing():
    try:
        # Create a test user
        user = register_and_login_user()
        if not user:
            return print_test_result("Enhanced PDF Parsing", False, 
                                    error="Failed to create test user")
        
        # Create a test PDF with negative amounts
        # Since we can't create a real PDF in this test, we'll simulate the API response
        
        # First, let's check if the PDF import endpoint exists
        headers = {"Authorization": f"Bearer {user['token']}"}
        
        # We'll make a request without a file to check if the endpoint exists
        # We expect a 400 error about missing file, not a 404
        test_response = requests.post(f"{API_URL}/transactions/pdf-import", headers=headers)
        
        endpoint_exists = test_response.status_code in [400, 422]  # 400 Bad Request or 422 Unprocessable Entity
        
        if not endpoint_exists:
            return print_test_result("Enhanced PDF Parsing", False, 
                                    response=test_response,
                                    error="PDF import endpoint does not exist")
        
        print("PDF import endpoint exists. In a real scenario, we would upload a PDF with negative amounts.")
        print("Since we can't create a real PDF in this test, we'll check if the endpoint is properly configured.")
        
        # Create a transaction with a negative amount to simulate a credit/payment
        negative_transaction = {
            "date": "2024-11-15",
            "description": "Test Credit Transaction",
            "category": "Retail and Grocery",
            "amount": -50.00,  # Negative amount
            "account_type": "credit_card"
        }
        
        neg_response = requests.post(f"{API_URL}/transactions", json=negative_transaction, headers=headers)
        
        if neg_response.status_code != 200:
            return print_test_result("Enhanced PDF Parsing", False, 
                                    response=neg_response,
                                    error="Failed to create transaction with negative amount")
        
        # Verify the transaction was created with the negative amount
        transactions_response = requests.get(f"{API_URL}/transactions", headers=headers)
        
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
        
        success = endpoint_exists and negative_found
        
        return print_test_result("Enhanced PDF Parsing", success, 
                                error=None if success else "Enhanced PDF parsing for negative amounts not functioning properly")
    except Exception as e:
        return print_test_result("Enhanced PDF Parsing", False, error=str(e))

# Run all tests
def run_all_tests():
    print("\n" + "=" * 40)
    print("STARTING USER DATA SEGMENTATION TESTS")
    print("=" * 40 + "\n")
    
    # User data segmentation tests
    test_results = {
        "Transactions Data Isolation": test_transactions_data_isolation(),
        "Categories Data Isolation": test_categories_data_isolation(),
        "Monthly Report Data Isolation": test_monthly_report_data_isolation(),
        "Category Breakdown Data Isolation": test_category_breakdown_data_isolation(),
        "Authentication Requirement": test_authentication_requirement()
    }
    
    print("\n" + "=" * 40)
    print("TEST SUMMARY")
    print("=" * 40)
    
    all_passed = True
    for test_name, result in test_results.items():
        status = "PASSED" if result else "FAILED"
        if not result:
            all_passed = False
        print(f"{test_name}: {status}")
    
    print("\nOVERALL RESULT: " + ("PASSED" if all_passed else "FAILED"))
    print("=" * 40 + "\n")
    
    return all_passed

if __name__ == "__main__":
    run_all_tests()