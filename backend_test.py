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

test_user = {
    "name": "John Doe",
    "email": "john.doe@example.com",
    "household_name": "Doe Family"
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
        # Create a CSV file with proper date format
        csv_content = """date,description,category,amount,account_type
2024-10-15,AMAZON.COM PURCHASE,Shopping,45.99,credit_card
2024-10-16,STARBUCKS COFFEE,Food & Dining,5.75,debit
2024-10-17,UBER RIDE,Transportation,12.50,credit_card"""
        
        print(f"CSV Content:\n{csv_content}")
        
        # Create a temporary CSV file
        temp_csv_path = '/tmp/transactions.csv'
        with open(temp_csv_path, 'w') as f:
            f.write(csv_content)
        
        # Use the file from disk
        with open(temp_csv_path, 'rb') as f:
            files = {'file': ('transactions.csv', f, 'text/csv')}
            response = requests.post(f"{API_URL}/transactions/bulk-import", files=files)
            print(f"Bulk import response: {response.text}")
        
        success = response.status_code == 200 and "message" in response.json()
        
        # Clean up
        if os.path.exists(temp_csv_path):
            os.remove(temp_csv_path)
        
        if not success:
            print("\nSUGGESTED FIX FOR BULK IMPORT:")
            print("The issue is in the bulk_import_transactions function in server.py.")
            print("When pandas reads the CSV, it converts date strings to datetime.date objects,")
            print("but these aren't properly converted to strings before being inserted into MongoDB.")
            print("\nHere's how to fix it:")
            print("1. Modify the bulk_import_transactions function to convert date objects to strings:")
            print("```python")
            print("@api_router.post('/transactions/bulk-import')")
            print("async def bulk_import_transactions(file: UploadFile = File(...)):")
            print("    # ... existing code ...")
            print("    transactions = []")
            print("    for _, row in df.iterrows():")
            print("        # Convert date to string if it's a datetime object")
            print("        date_value = row['date']")
            print("        if isinstance(date_value, (datetime, date)):")
            print("            date_value = date_value.isoformat()")
            print("        ")
            print("        transaction_data = {")
            print("            'date': date_value,")
            print("            'description': row['description'],")
            print("            'category': row['category'],")
            print("            'amount': float(row['amount']),")
            print("            'account_type': row.get('account_type', 'credit_card')")
            print("        }")
            print("        transaction_obj = Transaction(**transaction_data)")
            print("        transaction_dict = transaction_obj.dict()")
            print("        # Ensure dates are strings for MongoDB")
            print("        transaction_dict['date'] = transaction_dict['date'].isoformat() if isinstance(transaction_dict['date'], (datetime, date)) else transaction_dict['date']")
            print("        transaction_dict['created_at'] = transaction_dict['created_at'].isoformat() if isinstance(transaction_dict['created_at'], (datetime, date)) else transaction_dict['created_at']")
            print("        transactions.append(transaction_dict)")
            print("    # ... rest of the function ...")
            print("```")
        
        return print_test_result("Bulk Import Transactions", success, response)
    except Exception as e:
        print(f"Bulk import exception: {str(e)}")
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

# Test 8: Create user
def test_create_user():
    try:
        response = requests.post(f"{API_URL}/users", json=test_user)
        success = response.status_code == 200 and "id" in response.json()
        
        # Store the user ID for later tests
        if success:
            global created_user_id
            created_user_id = response.json()["id"]
            print(f"Created user with ID: {created_user_id}")
        
        return print_test_result("Create User", success, response)
    except Exception as e:
        return print_test_result("Create User", False, error=str(e))

# Test 9: Get all users
def test_get_users():
    try:
        response = requests.get(f"{API_URL}/users")
        success = response.status_code == 200 and isinstance(response.json(), list)
        
        # Verify the user we just created is in the list
        if success and hasattr(sys.modules[__name__], 'created_user_id'):
            user_found = False
            for user in response.json():
                if user.get("id") == created_user_id:
                    user_found = True
                    break
            
            if not user_found:
                print(f"WARNING: Created user with ID {created_user_id} not found in results")
                success = False
        
        return print_test_result("Get All Users", success, response)
    except Exception as e:
        return print_test_result("Get All Users", False, error=str(e))

# Test 10: Get all categories
def test_get_categories():
    try:
        response = requests.get(f"{API_URL}/categories")
        success = response.status_code == 200 and isinstance(response.json(), list)
        
        # Verify the structure of the response
        if success and response.json():
            category = response.json()[0]
            required_fields = ["id", "name", "color", "user_id"]
            for field in required_fields:
                if field not in category:
                    print(f"WARNING: Required field '{field}' missing from category")
                    success = False
        
        return print_test_result("Get All Categories", success, response)
    except Exception as e:
        return print_test_result("Get All Categories", False, error=str(e))

# Test 11: Create category
def test_create_category():
    try:
        response = requests.post(f"{API_URL}/categories", json=test_category)
        success = response.status_code == 200 and "id" in response.json()
        
        # Store the category ID for later tests
        if success:
            global created_category_id
            created_category_id = response.json()["id"]
            print(f"Created category with ID: {created_category_id}")
        
        return print_test_result("Create Category", success, response)
    except Exception as e:
        return print_test_result("Create Category", False, error=str(e))

# Test 12: Update category
def test_update_category():
    # Skip if we don't have a category ID
    if not hasattr(sys.modules[__name__], 'created_category_id'):
        return print_test_result("Update Category", False, error="No category ID available to update")
    
    try:
        update_data = {
            "name": "Updated Test Category",
            "color": "#33FF57"
        }
        
        response = requests.put(f"{API_URL}/categories/{created_category_id}", json=update_data)
        success = response.status_code == 200 and "id" in response.json()
        
        # Verify the category was actually updated
        if success:
            updated_name = response.json().get("name")
            updated_color = response.json().get("color")
            
            if updated_name != update_data["name"] or updated_color != update_data["color"]:
                print(f"WARNING: Category not updated correctly. Expected name: {update_data['name']}, got: {updated_name}. Expected color: {update_data['color']}, got: {updated_color}")
                success = False
        
        return print_test_result("Update Category", success, response)
    except Exception as e:
        return print_test_result("Update Category", False, error=str(e))

# Test 13: Delete category
def test_delete_category():
    # Skip if we don't have a category ID
    if not hasattr(sys.modules[__name__], 'created_category_id'):
        return print_test_result("Delete Category", False, error="No category ID available to delete")
    
    try:
        response = requests.delete(f"{API_URL}/categories/{created_category_id}")
        success = response.status_code == 200 and "message" in response.json()
        
        # Verify the category was actually deleted
        if success:
            verify_response = requests.get(f"{API_URL}/categories")
            if verify_response.status_code == 200:
                for category in verify_response.json():
                    if category.get("id") == created_category_id:
                        print(f"WARNING: Category with ID {created_category_id} still exists after deletion")
                        success = False
                        break
        
        return print_test_result("Delete Category", success, response)
    except Exception as e:
        return print_test_result("Delete Category", False, error=str(e))

# Test 14: Create transaction with category
def test_create_transaction_with_category():
    try:
        # First, get all categories
        categories_response = requests.get(f"{API_URL}/categories")
        if categories_response.status_code != 200 or not categories_response.json():
            return print_test_result("Create Transaction with Category", False, error="No categories available")
        
        # Use the first category
        category_id = categories_response.json()[0]["id"]
        
        # Create a transaction with this category
        transaction_data = {
            "date": "2024-11-07",
            "description": "TRANSACTION WITH CATEGORY",
            "category": category_id,
            "amount": 25.99,
            "account_type": "credit_card"
        }
        
        response = requests.post(f"{API_URL}/transactions", json=transaction_data)
        success = response.status_code == 200 and "id" in response.json()
        
        # Store the transaction ID for later tests
        if success:
            global created_transaction_with_category_id
            created_transaction_with_category_id = response.json()["id"]
            print(f"Created transaction with category, ID: {created_transaction_with_category_id}")
            
            # Verify the category is correctly linked
            if response.json().get("category") != category_id:
                print(f"WARNING: Category not correctly linked. Expected: {category_id}, got: {response.json().get('category')}")
                success = False
        
        return print_test_result("Create Transaction with Category", success, response)
    except Exception as e:
        return print_test_result("Create Transaction with Category", False, error=str(e))

# Test 15: Analytics with category filtering
def test_analytics_with_category_filtering():
    try:
        # First, get all categories
        categories_response = requests.get(f"{API_URL}/categories")
        if categories_response.status_code != 200 or not categories_response.json():
            return print_test_result("Analytics with Category Filtering", False, error="No categories available")
        
        # Use the first category
        category_id = categories_response.json()[0]["id"]
        
        # Get category breakdown with filtering
        response = requests.get(f"{API_URL}/analytics/category-breakdown?category={category_id}")
        success = response.status_code == 200 and isinstance(response.json(), list)
        
        return print_test_result("Analytics with Category Filtering", success, response)
    except Exception as e:
        return print_test_result("Analytics with Category Filtering", False, error=str(e))

# Test 16: PDF import
def test_pdf_import():
    try:
        # Create a test PDF file
        pdf_path = '/tmp/test_transactions.pdf'
        create_test_pdf(pdf_path)
        
        # Upload the PDF file
        with open(pdf_path, 'rb') as f:
            files = {'file': ('test_transactions.pdf', f, 'application/pdf')}
            response = requests.post(f"{API_URL}/transactions/pdf-import", files=files)
        
        success = response.status_code == 200 and "message" in response.json()
        
        # Clean up
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        
        return print_test_result("PDF Import", success, response)
    except Exception as e:
        return print_test_result("PDF Import", False, error=str(e))

# Test 17: PDF import duplicate detection
def test_pdf_import_duplicate_detection():
    try:
        # Create a test PDF file
        pdf_path = '/tmp/test_transactions.pdf'
        create_test_pdf(pdf_path)
        
        # Upload the PDF file first time
        with open(pdf_path, 'rb') as f:
            files = {'file': ('test_transactions.pdf', f, 'application/pdf')}
            first_response = requests.post(f"{API_URL}/transactions/pdf-import", files=files)
        
        # Upload the same PDF file second time to test duplicate detection
        with open(pdf_path, 'rb') as f:
            files = {'file': ('test_transactions.pdf', f, 'application/pdf')}
            second_response = requests.post(f"{API_URL}/transactions/pdf-import", files=files)
        
        # Check if duplicates were detected
        success = second_response.status_code == 200 and "duplicate_count" in second_response.json()
        
        # Clean up
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        
        return print_test_result("PDF Import Duplicate Detection", success, second_response)
    except Exception as e:
        return print_test_result("PDF Import Duplicate Detection", False, error=str(e))

# Test 18: PDF import error handling
def test_pdf_import_error_handling():
    try:
        # Create an invalid PDF file (just a text file with .pdf extension)
        invalid_pdf_path = '/tmp/invalid.pdf'
        with open(invalid_pdf_path, 'w') as f:
            f.write("This is not a valid PDF file")
        
        # Upload the invalid PDF file
        with open(invalid_pdf_path, 'rb') as f:
            files = {'file': ('invalid.pdf', f, 'application/pdf')}
            response = requests.post(f"{API_URL}/transactions/pdf-import", files=files)
        
        # We expect an error response
        success = response.status_code != 200
        
        # Clean up
        if os.path.exists(invalid_pdf_path):
            os.remove(invalid_pdf_path)
        
        return print_test_result("PDF Import Error Handling", success, response)
    except Exception as e:
        return print_test_result("PDF Import Error Handling", False, error=str(e))

# Run all tests
def run_all_tests():
    print("\n" + "=" * 40)
    print("STARTING BACKEND API TESTS")
    print("=" * 40 + "\n")
    
    test_results = {
        "Root Endpoint": test_root_endpoint(),
        "Create User": test_create_user(),
        "Get All Users": test_get_users(),
        "Get All Categories": test_get_categories(),
        "Create Category": test_create_category(),
        "Update Category": test_update_category(),
        "Create Transaction": test_create_transaction(),
        "Create Transaction with Category": test_create_transaction_with_category(),
        "Get All Transactions": test_get_transactions(),
        "Monthly Report Analytics": test_monthly_report(),
        "Category Breakdown Analytics": test_category_breakdown(),
        "Analytics with Category Filtering": test_analytics_with_category_filtering(),
        "Bulk Import Transactions": test_bulk_import(),
        "PDF Import": test_pdf_import(),
        "PDF Import Duplicate Detection": test_pdf_import_duplicate_detection(),
        "PDF Import Error Handling": test_pdf_import_error_handling(),
        "Delete Transaction": test_delete_transaction(),
        "Delete Category": test_delete_category()
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