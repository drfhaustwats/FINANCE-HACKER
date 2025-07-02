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

# Test 19: PDF transaction extraction completeness
def test_pdf_extraction_completeness():
    try:
        # Create a test PDF file with the Lovisa transaction and other transactions
        pdf_path = '/tmp/test_lovisa_transaction.pdf'
        create_test_pdf(pdf_path)
        
        # Upload the PDF file
        with open(pdf_path, 'rb') as f:
            files = {'file': ('test_lovisa_transaction.pdf', f, 'application/pdf')}
            response = requests.post(f"{API_URL}/transactions/pdf-import", files=files)
        
        success = response.status_code == 200 and "message" in response.json()
        
        # Check if all transactions were extracted, including the Lovisa transaction
        if success:
            # Verify the response data
            imported_count = response.json().get("imported_count", 0)
            total_found = response.json().get("total_found", 0)
            
            print(f"PDF Import Response: {response.json()}")
            print(f"Total transactions found in PDF: {total_found}")
            print(f"Transactions imported (excluding duplicates): {imported_count}")
            
            # We expect to find all 6 transactions from our test PDF
            if total_found < 6:
                print(f"WARNING: Expected at least 6 transactions, but only found {total_found}")
                success = False
            
            # Get all transactions
            transactions_response = requests.get(f"{API_URL}/transactions")
            if transactions_response.status_code == 200:
                transactions = transactions_response.json()
                
                # Check specifically for the Lovisa transaction
                lovisa_found = False
                for transaction in transactions:
                    if "lovisa" in transaction.get("description", "").lower():
                        lovisa_found = True
                        print(f"Found Lovisa transaction: {transaction}")
                        break
                
                if not lovisa_found:
                    print("WARNING: Lovisa transaction not found in extracted transactions")
                    success = False
        
        # Clean up
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        
        return print_test_result("PDF Transaction Extraction Completeness", success, response)
    except Exception as e:
        return print_test_result("PDF Transaction Extraction Completeness", False, error=str(e))

# Test 20: Check for transactions on specific dates
def test_transactions_by_date():
    try:
        # Check for transactions on Oct 13-15
        response = requests.get(f"{API_URL}/transactions?start_date=2024-10-13&end_date=2024-10-15")
        success = response.status_code == 200
        
        transactions = response.json()
        print(f"Found {len(transactions)} transactions between Oct 13-15:")
        for transaction in transactions:
            print(f"  {transaction.get('date')}: {transaction.get('description')} - ${transaction.get('amount')}")
        
        # Check specifically for the Lovisa transaction
        lovisa_found = False
        for transaction in transactions:
            if "lovisa" in transaction.get("description", "").lower():
                lovisa_found = True
                print(f"Found Lovisa transaction: {transaction}")
                break
        
        if not lovisa_found:
            print("WARNING: Lovisa transaction not found in date range Oct 13-15")
        
        return print_test_result("Transactions by Date", success, response)
    except Exception as e:
        return print_test_result("Transactions by Date", False, error=str(e))

# Test 21: Check database state
def test_database_state():
    try:
        # Get all transactions
        response = requests.get(f"{API_URL}/transactions")
        success = response.status_code == 200
        
        transactions = response.json()
        print(f"Total transactions in database: {len(transactions)}")
        
        # Group by month
        months = {}
        for transaction in transactions:
            date_str = transaction.get("date", "")
            if date_str:
                month = date_str[:7]  # YYYY-MM
                if month not in months:
                    months[month] = 0
                months[month] += 1
        
        print("Transactions by month:")
        for month, count in sorted(months.items()):
            print(f"  {month}: {count} transactions")
        
        # Group by category
        categories = {}
        for transaction in transactions:
            category = transaction.get("category", "Unknown")
            if category not in categories:
                categories[category] = 0
            categories[category] += 1
        
        print("Transactions by category:")
        for category, count in sorted(categories.items()):
            print(f"  {category}: {count} transactions")
        
        return print_test_result("Database State", success, response)
    except Exception as e:
        return print_test_result("Database State", False, error=str(e))

# Test 22: Monthly report analytics with year parameter
def test_monthly_report_with_year():
    try:
        # Test with current year (2025)
        current_year = datetime.now().year
        response_current = requests.get(f"{API_URL}/analytics/monthly-report?year={current_year}")
        
        # Test with 2024 (where we know data exists)
        response_2024 = requests.get(f"{API_URL}/analytics/monthly-report?year=2024")
        
        print(f"Monthly report for {current_year}:")
        print(json.dumps(response_current.json(), indent=2))
        
        print(f"Monthly report for 2024:")
        print(json.dumps(response_2024.json(), indent=2))
        
        success = response_current.status_code == 200 and response_2024.status_code == 200
        
        return print_test_result("Monthly Report with Year Parameter", success, response_2024)
    except Exception as e:
        return print_test_result("Monthly Report with Year Parameter", False, error=str(e))

# Test 23: Check for specific transaction (Lovisa) and test transaction update API
def test_check_for_lovisa():
    try:
        # Search for transactions with 'lovisa' in description
        response = requests.get(f"{API_URL}/transactions")
        success = response.status_code == 200
        
        transactions = response.json()
        lovisa_transactions = [t for t in transactions if "lovisa" in t.get("description", "").lower()]
        
        print(f"Found {len(lovisa_transactions)} transactions with 'lovisa' in description:")
        for transaction in lovisa_transactions:
            print(f"  {transaction.get('date')}: {transaction.get('description')} - ${transaction.get('amount')}")
        
        # If we found the Lovisa transaction, test updating its category
        if lovisa_transactions:
            lovisa_transaction = lovisa_transactions[0]
            transaction_id = lovisa_transaction.get("id")
            
            # Get available categories
            categories_response = requests.get(f"{API_URL}/categories")
            if categories_response.status_code == 200 and categories_response.json():
                # Choose a different category than the current one
                current_category = lovisa_transaction.get("category")
                available_categories = [c for c in categories_response.json() if c.get("name") != current_category]
                
                if available_categories:
                    new_category = available_categories[0].get("name")
                    
                    # Update the transaction with a new category
                    update_data = {"category": new_category}
                    update_response = requests.put(f"{API_URL}/transactions/{transaction_id}", json=update_data)
                    
                    if update_response.status_code == 200:
                        print(f"Successfully updated Lovisa transaction category from '{current_category}' to '{new_category}'")
                        
                        # Verify the update was successful
                        verify_response = requests.get(f"{API_URL}/transactions")
                        if verify_response.status_code == 200:
                            updated_transaction = next((t for t in verify_response.json() if t.get("id") == transaction_id), None)
                            
                            if updated_transaction and updated_transaction.get("category") == new_category:
                                print(f"Verified category update: {updated_transaction}")
                            else:
                                print("WARNING: Category update verification failed")
                                success = False
                    else:
                        print(f"Failed to update transaction: {update_response.text}")
                        success = False
        
        return print_test_result("Check for Lovisa Transaction and Update", success, response)
    except Exception as e:
        return print_test_result("Check for Lovisa Transaction and Update", False, error=str(e))

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
        "PDF Transaction Extraction Completeness": test_pdf_extraction_completeness(),
        "Transactions by Date": test_transactions_by_date(),
        "Database State": test_database_state(),
        "Monthly Report with Year Parameter": test_monthly_report_with_year(),
        "Check for Lovisa Transaction and Update": test_check_for_lovisa(),
        "Word Boundary Fix for Header Detection": test_word_boundary_fix(),
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

# Test 24: Verify word boundary fix for header detection
def test_word_boundary_fix():
    try:
        # Create a test PDF with specific content to test the word boundary fix
        pdf_path = '/tmp/test_word_boundary.pdf'
        
        # Create a PDF with a line containing "VISA" as a substring (like "LOVISA")
        c = canvas.Canvas(pdf_path, pagesize=letter)
        c.setFont("Helvetica", 12)
        
        # Add a title
        c.drawString(100, 750, "CIBC DIVIDEND VISA INFINITE CARD")
        c.drawString(100, 730, "Account: XXXX-XXXX-XXXX-1234")
        c.drawString(100, 710, "Statement Period: October 15 to November 15, 2024")
        c.drawString(100, 690, "JOHN DOE")
        
        # Add transaction headers
        c.drawString(100, 650, "TRANS   POST    DESCRIPTION                           SPEND CATEGORIES        AMOUNT")
        c.drawString(100, 630, "--------------------------------------------------------------------------------")
        
        # Add transactions with "VISA" as a substring in different contexts
        transactions = [
            ("Oct 13", "Oct 15", "LOVISA ALBERTA AB", "Retail and Grocery", "29.39"),  # Should be parsed (contains "VISA")
            ("Oct 16", "Oct 17", "VISA PAYMENT THANK YOU", "Payment", "100.00"),  # Should be skipped (is a header)
            ("Oct 18", "Oct 19", "ADVISATECH SOLUTIONS", "Professional Services", "45.99"),  # Should be parsed (contains "VISA")
            ("Oct 20", "Oct 21", "VISA INTERNATIONAL FEE", "Fees", "2.50"),  # Should be skipped (is a header)
            ("Oct 22", "Oct 23", "REVISAGE BEAUTY SALON", "Personal Care", "75.00")  # Should be parsed (contains "VISA")
        ]
        
        y_position = 610
        for trans in transactions:
            c.drawString(100, y_position, f"{trans[0]}    {trans[1]}    {trans[2]}    {trans[3]}    {trans[4]}")
            y_position -= 20
        
        c.save()
        print(f"Created test PDF at {pdf_path}")
        
        # Upload the PDF file
        with open(pdf_path, 'rb') as f:
            files = {'file': ('test_word_boundary.pdf', f, 'application/pdf')}
            response = requests.post(f"{API_URL}/transactions/pdf-import", files=files)
        
        success = response.status_code == 200 and "message" in response.json()
        
        # Check if the correct transactions were extracted
        if success:
            # Get all transactions
            transactions_response = requests.get(f"{API_URL}/transactions")
            if transactions_response.status_code == 200:
                transactions = transactions_response.json()
                
                # Filter for transactions from our test PDF
                test_pdf_transactions = [t for t in transactions if t.get("pdf_source") == "test_word_boundary.pdf"]
                
                # We should have 3 transactions (LOVISA, ADVISATECH, REVISAGE)
                # and not the 2 VISA header lines
                expected_descriptions = ["LOVISA ALBERTA AB", "ADVISATECH SOLUTIONS", "REVISAGE BEAUTY SALON"]
                unexpected_descriptions = ["VISA PAYMENT THANK YOU", "VISA INTERNATIONAL FEE"]
                
                found_expected = []
                found_unexpected = []
                
                for transaction in test_pdf_transactions:
                    desc = transaction.get("description", "")
                    if any(expected in desc for expected in expected_descriptions):
                        found_expected.append(desc)
                    if any(unexpected in desc for unexpected in unexpected_descriptions):
                        found_unexpected.append(desc)
                
                print(f"Found {len(test_pdf_transactions)} transactions from test PDF")
                print(f"Found expected transactions: {found_expected}")
                print(f"Found unexpected transactions: {found_unexpected}")
                
                # Check if we found all expected transactions
                if len(found_expected) != len(expected_descriptions):
                    missing = [d for d in expected_descriptions if not any(d in found for found in found_expected)]
                    print(f"WARNING: Missing expected transactions: {missing}")
                    success = False
                
                # Check if we found any unexpected transactions
                if found_unexpected:
                    print(f"WARNING: Found unexpected transactions that should have been skipped: {found_unexpected}")
                    success = False
        
        # Clean up
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        
        return print_test_result("Word Boundary Fix for Header Detection", success, response)
    except Exception as e:
        return print_test_result("Word Boundary Fix for Header Detection", False, error=str(e))

if __name__ == "__main__":
    run_all_tests()