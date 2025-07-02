#!/usr/bin/env python3
import requests
import json
import csv
import io
import os
from datetime import datetime, date
import time
import sys

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

# Test 1: Root endpoint
def test_root_endpoint():
    try:
        response = requests.get(f"{API_URL}/")
        success = response.status_code == 200 and "message" in response.json()
        return print_test_result("Root Endpoint", success, response)
    except Exception as e:
        return print_test_result("Root Endpoint", False, error=str(e))

# Test 2: Create transaction
def test_create_transaction():
    try:
        response = requests.post(f"{API_URL}/transactions", json=test_transaction)
        success = response.status_code == 200 and "id" in response.json()
        
        # Store the transaction ID for later tests
        if success:
            global created_transaction_id
            created_transaction_id = response.json()["id"]
            print(f"Created transaction with ID: {created_transaction_id}")
            
            # Verify date handling is correct
            response_date = response.json().get("date")
            expected_date = test_transaction["date"]
            if response_date != expected_date:
                print(f"WARNING: Date format issue. Expected {expected_date}, got {response_date}")
                success = False
        
        return print_test_result("Create Transaction", success, response)
    except Exception as e:
        return print_test_result("Create Transaction", False, error=str(e))

# Test 3: Get all transactions
def test_get_transactions():
    try:
        response = requests.get(f"{API_URL}/transactions")
        success = response.status_code == 200 and isinstance(response.json(), list)
        
        # Verify the transaction we just created is in the list
        if success and hasattr(sys.modules[__name__], 'created_transaction_id'):
            transaction_found = False
            for transaction in response.json():
                if transaction.get("id") == created_transaction_id:
                    transaction_found = True
                    break
            
            if not transaction_found:
                print(f"WARNING: Created transaction with ID {created_transaction_id} not found in results")
                success = False
        
        return print_test_result("Get All Transactions", success, response)
    except Exception as e:
        return print_test_result("Get All Transactions", False, error=str(e))

# Test 4: Monthly report analytics
def test_monthly_report():
    try:
        current_year = datetime.now().year
        response = requests.get(f"{API_URL}/analytics/monthly-report?year={current_year}")
        success = response.status_code == 200 and isinstance(response.json(), list)
        
        # Verify the structure of the response
        if success and response.json():
            report = response.json()[0]
            required_fields = ["month", "year", "categories", "total_spent", "transaction_count"]
            for field in required_fields:
                if field not in report:
                    print(f"WARNING: Required field '{field}' missing from monthly report")
                    success = False
        
        return print_test_result("Monthly Report Analytics", success, response)
    except Exception as e:
        return print_test_result("Monthly Report Analytics", False, error=str(e))

# Test 5: Category breakdown analytics
def test_category_breakdown():
    try:
        response = requests.get(f"{API_URL}/analytics/category-breakdown")
        success = response.status_code == 200 and isinstance(response.json(), list)
        
        # Verify the structure of the response
        if success and response.json():
            category = response.json()[0]
            required_fields = ["category", "amount", "count", "percentage"]
            for field in required_fields:
                if field not in category:
                    print(f"WARNING: Required field '{field}' missing from category breakdown")
                    success = False
        
        return print_test_result("Category Breakdown Analytics", success, response)
    except Exception as e:
        return print_test_result("Category Breakdown Analytics", False, error=str(e))

# Test 6: Bulk import transactions
def test_bulk_import():
    try:
        # Create a CSV file in memory
        csv_data = io.StringIO()
        writer = csv.writer(csv_data)
        writer.writerow(["date", "description", "category", "amount", "account_type"])
        writer.writerow(["2024-10-15", "AMAZON.COM PURCHASE", "Shopping", "45.99", "credit_card"])
        writer.writerow(["2024-10-16", "STARBUCKS COFFEE", "Food & Dining", "5.75", "debit"])
        writer.writerow(["2024-10-17", "UBER RIDE", "Transportation", "12.50", "credit_card"])
        
        csv_data.seek(0)
        csv_content = csv_data.getvalue()
        
        # Create a temporary CSV file
        temp_csv_path = '/tmp/transactions.csv'
        with open(temp_csv_path, 'w') as f:
            f.write(csv_content)
        
        # Use the file from disk
        with open(temp_csv_path, 'rb') as f:
            files = {'file': ('transactions.csv', f, 'text/csv')}
            response = requests.post(f"{API_URL}/transactions/bulk-import", files=files)
        
        success = response.status_code == 200 and "message" in response.json()
        
        # Clean up
        if os.path.exists(temp_csv_path):
            os.remove(temp_csv_path)
        
        return print_test_result("Bulk Import Transactions", success, response)
    except Exception as e:
        return print_test_result("Bulk Import Transactions", False, error=str(e))

# Test 7: Delete transaction
def test_delete_transaction():
    # Skip if we don't have a transaction ID
    if not hasattr(sys.modules[__name__], 'created_transaction_id'):
        return print_test_result("Delete Transaction", False, error="No transaction ID available to delete")
    
    try:
        response = requests.delete(f"{API_URL}/transactions/{created_transaction_id}")
        success = response.status_code == 200 and "message" in response.json()
        
        # Verify the transaction was actually deleted
        if success:
            verify_response = requests.get(f"{API_URL}/transactions")
            if verify_response.status_code == 200:
                for transaction in verify_response.json():
                    if transaction.get("id") == created_transaction_id:
                        print(f"WARNING: Transaction with ID {created_transaction_id} still exists after deletion")
                        success = False
                        break
        
        return print_test_result("Delete Transaction", success, response)
    except Exception as e:
        return print_test_result("Delete Transaction", False, error=str(e))

# Run all tests
def run_all_tests():
    print("\n" + "=" * 40)
    print("STARTING BACKEND API TESTS")
    print("=" * 40 + "\n")
    
    test_results = {
        "Root Endpoint": test_root_endpoint(),
        "Create Transaction": test_create_transaction(),
        "Get All Transactions": test_get_transactions(),
        "Monthly Report Analytics": test_monthly_report(),
        "Category Breakdown Analytics": test_category_breakdown(),
        "Bulk Import Transactions": test_bulk_import(),
        "Delete Transaction": test_delete_transaction()
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