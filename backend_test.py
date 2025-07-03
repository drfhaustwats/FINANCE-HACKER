#!/usr/bin/env python3
import requests
import json
import uuid
import random
import sys
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

# Test 1: Test transactions data isolation
def test_transactions_data_isolation():
    try:
        # Create two random user IDs
        user_a_id = f"user_a_{uuid.uuid4()}"
        user_b_id = f"user_b_{uuid.uuid4()}"
        
        # Create transactions for User A
        transactions_a = []
        for i in range(3):
            transaction = {
                "date": f"2024-11-{i+1}",
                "description": f"User A Transaction {i+1}",
                "category": "Retail and Grocery",
                "amount": round(random.uniform(10, 100), 2),
                "account_type": "credit_card",
                "user_id": user_a_id
            }
            response = requests.post(f"{API_URL}/transactions", json=transaction)
            if response.status_code == 200 and "id" in response.json():
                transactions_a.append(response.json())
                print(f"Created transaction for User A: {transaction['description']} with ID: {response.json()['id']}")
            else:
                print(f"Failed to create transaction for User A: {response.text}")
        
        # Create transactions for User B
        transactions_b = []
        for i in range(3):
            transaction = {
                "date": f"2024-11-{i+1}",
                "description": f"User B Transaction {i+1}",
                "category": "Transportation",
                "amount": round(random.uniform(10, 100), 2),
                "account_type": "credit_card",
                "user_id": user_b_id
            }
            response = requests.post(f"{API_URL}/transactions", json=transaction)
            if response.status_code == 200 and "id" in response.json():
                transactions_b.append(response.json())
                print(f"Created transaction for User B: {transaction['description']} with ID: {response.json()['id']}")
            else:
                print(f"Failed to create transaction for User B: {response.text}")
        
        # Get User A's transactions
        response_a = requests.get(f"{API_URL}/transactions?user_id={user_a_id}")
        
        # Get User B's transactions
        response_b = requests.get(f"{API_URL}/transactions?user_id={user_b_id}")
        
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
        # Create two random user IDs
        user_a_id = f"user_a_{uuid.uuid4()}"
        user_b_id = f"user_b_{uuid.uuid4()}"
        
        # Create categories for User A
        categories_a = []
        for i in range(2):
            category = {
                "name": f"User A Category {i+1}",
                "color": f"#FF{i+1}733",
                "user_id": user_a_id
            }
            response = requests.post(f"{API_URL}/categories", json=category)
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
                "color": f"#33FF{i+1}7",
                "user_id": user_b_id
            }
            response = requests.post(f"{API_URL}/categories", json=category)
            if response.status_code == 200 and "id" in response.json():
                categories_b.append(response.json())
                print(f"Created category for User B: {category['name']} with ID: {response.json()['id']}")
            else:
                print(f"Failed to create category for User B: {response.text}")
        
        # Get User A's categories
        response_a = requests.get(f"{API_URL}/categories?user_id={user_a_id}")
        
        # Get User B's categories
        response_b = requests.get(f"{API_URL}/categories?user_id={user_b_id}")
        
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
        # Create two random user IDs
        user_a_id = f"user_a_{uuid.uuid4()}"
        user_b_id = f"user_b_{uuid.uuid4()}"
        
        # Create transactions for User A
        transactions_a = []
        for i in range(3):
            transaction = {
                "date": f"2024-11-{i+1}",
                "description": f"User A Transaction {i+1}",
                "category": "Retail and Grocery",
                "amount": round(random.uniform(10, 100), 2),
                "account_type": "credit_card",
                "user_id": user_a_id
            }
            response = requests.post(f"{API_URL}/transactions", json=transaction)
            if response.status_code == 200 and "id" in response.json():
                transactions_a.append(response.json())
                print(f"Created transaction for User A: {transaction['description']} with ID: {response.json()['id']}")
            else:
                print(f"Failed to create transaction for User A: {response.text}")
        
        # Create transactions for User B
        transactions_b = []
        for i in range(3):
            transaction = {
                "date": f"2024-11-{i+1}",
                "description": f"User B Transaction {i+1}",
                "category": "Transportation",
                "amount": round(random.uniform(10, 100), 2),
                "account_type": "credit_card",
                "user_id": user_b_id
            }
            response = requests.post(f"{API_URL}/transactions", json=transaction)
            if response.status_code == 200 and "id" in response.json():
                transactions_b.append(response.json())
                print(f"Created transaction for User B: {transaction['description']} with ID: {response.json()['id']}")
            else:
                print(f"Failed to create transaction for User B: {response.text}")
        
        current_year = datetime.now().year
        
        # Get User A's monthly report
        response_a = requests.get(f"{API_URL}/analytics/monthly-report?year={current_year}&user_id={user_a_id}")
        
        # Get User B's monthly report
        response_b = requests.get(f"{API_URL}/analytics/monthly-report?year={current_year}&user_id={user_b_id}")
        
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
        # Create two random user IDs
        user_a_id = f"user_a_{uuid.uuid4()}"
        user_b_id = f"user_b_{uuid.uuid4()}"
        
        # Create transactions for User A
        transactions_a = []
        for i in range(3):
            transaction = {
                "date": f"2024-11-{i+1}",
                "description": f"User A Transaction {i+1}",
                "category": "Retail and Grocery",
                "amount": round(random.uniform(10, 100), 2),
                "account_type": "credit_card",
                "user_id": user_a_id
            }
            response = requests.post(f"{API_URL}/transactions", json=transaction)
            if response.status_code == 200 and "id" in response.json():
                transactions_a.append(response.json())
                print(f"Created transaction for User A: {transaction['description']} with ID: {response.json()['id']}")
            else:
                print(f"Failed to create transaction for User A: {response.text}")
        
        # Create transactions for User B
        transactions_b = []
        for i in range(3):
            transaction = {
                "date": f"2024-11-{i+1}",
                "description": f"User B Transaction {i+1}",
                "category": "Transportation",
                "amount": round(random.uniform(10, 100), 2),
                "account_type": "credit_card",
                "user_id": user_b_id
            }
            response = requests.post(f"{API_URL}/transactions", json=transaction)
            if response.status_code == 200 and "id" in response.json():
                transactions_b.append(response.json())
                print(f"Created transaction for User B: {transaction['description']} with ID: {response.json()['id']}")
            else:
                print(f"Failed to create transaction for User B: {response.text}")
        
        # Get User A's category breakdown
        response_a = requests.get(f"{API_URL}/analytics/category-breakdown?user_id={user_a_id}")
        
        # Get User B's category breakdown
        response_b = requests.get(f"{API_URL}/analytics/category-breakdown?user_id={user_b_id}")
        
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