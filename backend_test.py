#!/usr/bin/env python3
import requests
import json
import csv
import io
import os
from datetime import datetime, date
import time
import sys
import PyPDF2
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import uuid
import random

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

# Test data
test_transaction = {
    "date": "2024-11-06",
    "description": "STAPLES STORE #253 CALGARY AB",
    "category": "Home and Office Improvement",
    "amount": 0.57,
    "account_type": "credit_card"
}

# Test users for data segmentation testing
test_user_a = {
    "email": f"user_a_{uuid.uuid4().hex[:8]}@example.com",
    "password": "SecurePassword123!",
    "full_name": "User A Test",
    "username": f"user_a_{uuid.uuid4().hex[:8]}"
}

test_user_b = {
    "email": f"user_b_{uuid.uuid4().hex[:8]}@example.com",
    "password": "SecurePassword456!",
    "full_name": "User B Test",
    "username": f"user_b_{uuid.uuid4().hex[:8]}"
}

test_category = {
    "name": "Test Category",
    "color": "#FF5733"
}

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

# Helper function to create a test PDF with transaction data
def create_test_pdf(filepath):
    c = canvas.Canvas(filepath, pagesize=letter)
    c.setFont("Helvetica", 12)
    
    # Add a title
    c.drawString(100, 750, "CIBC DIVIDEND VISA INFINITE CARD")
    c.drawString(100, 730, "Account: XXXX-XXXX-XXXX-1234")
    c.drawString(100, 710, "Statement Period: October 15 to November 15, 2024")
    c.drawString(100, 690, "JOHN DOE")
    
    # Add transaction headers
    c.drawString(100, 650, "TRANS   POST    DESCRIPTION                           SPEND CATEGORIES        AMOUNT")
    c.drawString(100, 630, "--------------------------------------------------------------------------------")
    
    # Add some transactions including the problematic Lovisa transaction
    transactions = [
        ("Oct 13", "Oct 15", "Lovisa Alberta AB", "Retail and Grocery", "29.39"),
        ("Oct 15", "Oct 16", "AMAZON.COM PURCHASE", "Shopping", "45.99"),
        ("Oct 17", "Oct 18", "STARBUCKS COFFEE", "Restaurants", "5.75"),
        ("Oct 19", "Oct 20", "UBER RIDE", "Transportation", "12.50"),
        ("Oct 21", "Oct 22", "WALMART STORE #123", "Retail and Grocery", "67.89"),
        ("Oct 23", "Oct 24", "NETFLIX SUBSCRIPTION", "Hotel, Entertainment and Recreation", "14.99")
    ]
    
    y_position = 610
    for trans in transactions:
        c.drawString(100, y_position, f"{trans[0]}    {trans[1]}    {trans[2]}    {trans[3]}    {trans[4]}")
        y_position -= 20
    
    c.save()
    print(f"Created test PDF at {filepath}")
    return filepath

# User Data Segmentation Tests
# Test 1: Register two different users
def test_register_users():
    try:
        # Register User A
        register_url = f"{API_URL}/auth/register"
        response_a = requests.post(register_url, json=test_user_a)
        success_a = response_a.status_code == 200 and "access_token" in response_a.json()
        
        if success_a:
            global user_a_token
            user_a_token = response_a.json()["access_token"]
            print(f"Registered User A: {test_user_a['email']} with token: {user_a_token[:20]}...")
        else:
            print(f"Failed to register User A: {response_a.text}")
            return print_test_result("Register Users for Data Segmentation", False, response_a)
        
        # Register User B
        response_b = requests.post(register_url, json=test_user_b)
        success_b = response_b.status_code == 200 and "access_token" in response_b.json()
        
        if success_b:
            global user_b_token
            user_b_token = response_b.json()["access_token"]
            print(f"Registered User B: {test_user_b['email']} with token: {user_b_token[:20]}...")
        else:
            print(f"Failed to register User B: {response_b.text}")
            return print_test_result("Register Users for Data Segmentation", False, response_b)
        
        return print_test_result("Register Users for Data Segmentation", success_a and success_b)
    except Exception as e:
        return print_test_result("Register Users for Data Segmentation", False, error=str(e))

# Test 2: Login with registered users
def test_login_users():
    try:
        # Login User A
        login_url = f"{API_URL}/auth/login"
        login_data_a = {"email": test_user_a["email"], "password": test_user_a["password"]}
        response_a = requests.post(login_url, json=login_data_a)
        success_a = response_a.status_code == 200 and "access_token" in response_a.json()
        
        if success_a:
            global user_a_token
            user_a_token = response_a.json()["access_token"]
            print(f"Logged in User A with token: {user_a_token[:20]}...")
        else:
            print(f"Failed to login User A: {response_a.text}")
            # Try to register instead if login fails
            return test_register_users()
        
        # Login User B
        login_data_b = {"email": test_user_b["email"], "password": test_user_b["password"]}
        response_b = requests.post(login_url, json=login_data_b)
        success_b = response_b.status_code == 200 and "access_token" in response_b.json()
        
        if success_b:
            global user_b_token
            user_b_token = response_b.json()["access_token"]
            print(f"Logged in User B with token: {user_b_token[:20]}...")
        else:
            print(f"Failed to login User B: {response_b.text}")
            # Try to register instead if login fails
            return test_register_users()
        
        return print_test_result("Login Users for Data Segmentation", success_a and success_b)
    except Exception as e:
        print(f"Login failed, trying registration instead: {str(e)}")
        return test_register_users()

# Test 3: Create transactions for User A
def test_create_transactions_for_user_a():
    try:
        if not hasattr(sys.modules[__name__], 'user_a_token'):
            success = test_login_users()
            if not success:
                return print_test_result("Create Transactions for User A", False, error="Failed to get User A token")
        
        headers = {"Authorization": f"Bearer {user_a_token}"}
        
        # Create 3 transactions for User A
        transactions_a = []
        for i in range(3):
            transaction = {
                "date": f"2024-11-{i+1}",
                "description": f"User A Transaction {i+1}",
                "category": "Retail and Grocery",
                "amount": round(random.uniform(10, 100), 2),
                "account_type": "credit_card"
            }
            response = requests.post(f"{API_URL}/transactions", json=transaction, headers=headers)
            if response.status_code == 200 and "id" in response.json():
                transactions_a.append(response.json())
                print(f"Created transaction for User A: {transaction['description']} with ID: {response.json()['id']}")
            else:
                print(f"Failed to create transaction for User A: {response.text}")
        
        global user_a_transactions
        user_a_transactions = transactions_a
        
        success = len(transactions_a) == 3
        return print_test_result("Create Transactions for User A", success)
    except Exception as e:
        return print_test_result("Create Transactions for User A", False, error=str(e))

# Test 4: Create transactions for User B
def test_create_transactions_for_user_b():
    try:
        if not hasattr(sys.modules[__name__], 'user_b_token'):
            success = test_login_users()
            if not success:
                return print_test_result("Create Transactions for User B", False, error="Failed to get User B token")
        
        headers = {"Authorization": f"Bearer {user_b_token}"}
        
        # Create 3 transactions for User B
        transactions_b = []
        for i in range(3):
            transaction = {
                "date": f"2024-11-{i+1}",
                "description": f"User B Transaction {i+1}",
                "category": "Transportation",
                "amount": round(random.uniform(10, 100), 2),
                "account_type": "credit_card"
            }
            response = requests.post(f"{API_URL}/transactions", json=transaction, headers=headers)
            if response.status_code == 200 and "id" in response.json():
                transactions_b.append(response.json())
                print(f"Created transaction for User B: {transaction['description']} with ID: {response.json()['id']}")
            else:
                print(f"Failed to create transaction for User B: {response.text}")
        
        global user_b_transactions
        user_b_transactions = transactions_b
        
        success = len(transactions_b) == 3
        return print_test_result("Create Transactions for User B", success)
    except Exception as e:
        return print_test_result("Create Transactions for User B", False, error=str(e))

# Test 5: Create categories for User A
def test_create_categories_for_user_a():
    try:
        if not hasattr(sys.modules[__name__], 'user_a_token'):
            success = test_login_users()
            if not success:
                return print_test_result("Create Categories for User A", False, error="Failed to get User A token")
        
        headers = {"Authorization": f"Bearer {user_a_token}"}
        
        # Create 2 categories for User A
        categories_a = []
        for i in range(2):
            category = {
                "name": f"User A Category {i+1}",
                "color": f"#FF{i+1}733"
            }
            response = requests.post(f"{API_URL}/categories", json=category, headers=headers)
            if response.status_code == 200 and "id" in response.json():
                categories_a.append(response.json())
                print(f"Created category for User A: {category['name']} with ID: {response.json()['id']}")
            else:
                print(f"Failed to create category for User A: {response.text}")
        
        global user_a_categories
        user_a_categories = categories_a
        
        success = len(categories_a) == 2
        return print_test_result("Create Categories for User A", success)
    except Exception as e:
        return print_test_result("Create Categories for User A", False, error=str(e))

# Test 6: Create categories for User B
def test_create_categories_for_user_b():
    try:
        if not hasattr(sys.modules[__name__], 'user_b_token'):
            success = test_login_users()
            if not success:
                return print_test_result("Create Categories for User B", False, error="Failed to get User B token")
        
        headers = {"Authorization": f"Bearer {user_b_token}"}
        
        # Create 2 categories for User B
        categories_b = []
        for i in range(2):
            category = {
                "name": f"User B Category {i+1}",
                "color": f"#33FF{i+1}7"
            }
            response = requests.post(f"{API_URL}/categories", json=category, headers=headers)
            if response.status_code == 200 and "id" in response.json():
                categories_b.append(response.json())
                print(f"Created category for User B: {category['name']} with ID: {response.json()['id']}")
            else:
                print(f"Failed to create category for User B: {response.text}")
        
        global user_b_categories
        user_b_categories = categories_b
        
        success = len(categories_b) == 2
        return print_test_result("Create Categories for User B", success)
    except Exception as e:
        return print_test_result("Create Categories for User B", False, error=str(e))

# Test 7: Test transactions data isolation
def test_transactions_data_isolation():
    try:
        # Ensure we have users and their data
        if not hasattr(sys.modules[__name__], 'user_a_token') or not hasattr(sys.modules[__name__], 'user_b_token'):
            test_login_users()
        
        if not hasattr(sys.modules[__name__], 'user_a_transactions'):
            test_create_transactions_for_user_a()
        
        if not hasattr(sys.modules[__name__], 'user_b_transactions'):
            test_create_transactions_for_user_b()
        
        # Get User A's transactions with User A's token
        headers_a = {"Authorization": f"Bearer {user_a_token}"}
        response_a = requests.get(f"{API_URL}/transactions", headers=headers_a)
        
        # Get User B's transactions with User B's token
        headers_b = {"Authorization": f"Bearer {user_b_token}"}
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

# Test 8: Test categories data isolation
def test_categories_data_isolation():
    try:
        # Ensure we have users and their data
        if not hasattr(sys.modules[__name__], 'user_a_token') or not hasattr(sys.modules[__name__], 'user_b_token'):
            test_login_users()
        
        if not hasattr(sys.modules[__name__], 'user_a_categories'):
            test_create_categories_for_user_a()
        
        if not hasattr(sys.modules[__name__], 'user_b_categories'):
            test_create_categories_for_user_b()
        
        # Get User A's categories with User A's token
        headers_a = {"Authorization": f"Bearer {user_a_token}"}
        response_a = requests.get(f"{API_URL}/categories", headers=headers_a)
        
        # Get User B's categories with User B's token
        headers_b = {"Authorization": f"Bearer {user_b_token}"}
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

# Test 9: Test monthly report analytics data isolation
def test_monthly_report_data_isolation():
    try:
        # Ensure we have users and their data
        if not hasattr(sys.modules[__name__], 'user_a_token') or not hasattr(sys.modules[__name__], 'user_b_token'):
            test_login_users()
        
        if not hasattr(sys.modules[__name__], 'user_a_transactions'):
            test_create_transactions_for_user_a()
        
        if not hasattr(sys.modules[__name__], 'user_b_transactions'):
            test_create_transactions_for_user_b()
        
        current_year = datetime.now().year
        
        # Get User A's monthly report with User A's token
        headers_a = {"Authorization": f"Bearer {user_a_token}"}
        response_a = requests.get(f"{API_URL}/analytics/monthly-report?year={current_year}", headers=headers_a)
        
        # Get User B's monthly report with User B's token
        headers_b = {"Authorization": f"Bearer {user_b_token}"}
        response_b = requests.get(f"{API_URL}/analytics/monthly-report?year={current_year}", headers=headers_b)
        
        # Verify User A's monthly report only includes User A's data
        user_a_report_correct = True
        if response_a.status_code == 200:
            monthly_report_a = response_a.json()
            print(f"User A's monthly report has {len(monthly_report_a)} months")
            
            # Check total spent matches User A's transactions
            if monthly_report_a:
                user_a_total_spent = sum(report.get("total_spent", 0) for report in monthly_report_a)
                expected_a_total = sum(transaction.get("amount", 0) for transaction in user_a_transactions)
                
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
                expected_b_total = sum(transaction.get("amount", 0) for transaction in user_b_transactions)
                
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

# Test 10: Test category breakdown analytics data isolation
def test_category_breakdown_data_isolation():
    try:
        # Ensure we have users and their data
        if not hasattr(sys.modules[__name__], 'user_a_token') or not hasattr(sys.modules[__name__], 'user_b_token'):
            test_login_users()
        
        if not hasattr(sys.modules[__name__], 'user_a_transactions'):
            test_create_transactions_for_user_a()
        
        if not hasattr(sys.modules[__name__], 'user_b_transactions'):
            test_create_transactions_for_user_b()
        
        # Get User A's category breakdown with User A's token
        headers_a = {"Authorization": f"Bearer {user_a_token}"}
        response_a = requests.get(f"{API_URL}/analytics/category-breakdown", headers=headers_a)
        
        # Get User B's category breakdown with User B's token
        headers_b = {"Authorization": f"Bearer {user_b_token}"}
        response_b = requests.get(f"{API_URL}/analytics/category-breakdown", headers=headers_b)
        
        # Verify User A's category breakdown only includes User A's data
        user_a_breakdown_correct = True
        if response_a.status_code == 200:
            category_breakdown_a = response_a.json()
            print(f"User A's category breakdown has {len(category_breakdown_a)} categories")
            
            # Check total amount matches User A's transactions
            if category_breakdown_a:
                user_a_total_amount = sum(category.get("amount", 0) for category in category_breakdown_a)
                expected_a_total = sum(transaction.get("amount", 0) for transaction in user_a_transactions)
                
                # Allow for some floating point imprecision
                if abs(user_a_total_amount - expected_a_total) > 0.01:
                    user_a_breakdown_correct = False
                    print(f"SECURITY ISSUE: User A's category breakdown total ({user_a_total_amount}) doesn't match expected total ({expected_a_total})")
                
                # Check if User A's breakdown includes User B's categories
                for category in category_breakdown_a:
                    if category.get("category") == "Transportation" and any("User B Transaction" in t.get("description", "") for t in user_b_transactions):
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
                expected_b_total = sum(transaction.get("amount", 0) for transaction in user_b_transactions)
                
                # Allow for some floating point imprecision
                if abs(user_b_total_amount - expected_b_total) > 0.01:
                    user_b_breakdown_correct = False
                    print(f"SECURITY ISSUE: User B's category breakdown total ({user_b_total_amount}) doesn't match expected total ({expected_b_total})")
                
                # Check if User B's breakdown includes User A's categories
                for category in category_breakdown_b:
                    if category.get("category") == "Retail and Grocery" and any("User A Transaction" in t.get("description", "") for t in user_a_transactions):
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

# Test 11: Test authentication requirement
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
    print("STARTING USER DATA SEGMENTATION TESTS")
    print("=" * 40 + "\n")
    
    # User data segmentation tests
    test_results = {
        "Register Users for Data Segmentation": test_register_users(),
        "Login Users for Data Segmentation": test_login_users(),
        "Create Transactions for User A": test_create_transactions_for_user_a(),
        "Create Transactions for User B": test_create_transactions_for_user_b(),
        "Create Categories for User A": test_create_categories_for_user_a(),
        "Create Categories for User B": test_create_categories_for_user_b(),
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