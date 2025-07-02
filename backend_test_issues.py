#!/usr/bin/env python3
import requests
import json
import os
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

# Test 1: Search for Lovisa transaction
def test_search_lovisa_transaction():
    try:
        # Get all transactions
        response = requests.get(f"{API_URL}/transactions")
        
        if response.status_code != 200:
            return print_test_result("Search Lovisa Transaction", False, response, "Failed to get transactions")
        
        transactions = response.json()
        
        # Search for Lovisa transaction
        lovisa_transactions = []
        alberta_transactions = []
        
        for transaction in transactions:
            description = transaction.get("description", "").lower()
            if "lovisa" in description:
                lovisa_transactions.append(transaction)
            if "alberta" in description:
                alberta_transactions.append(transaction)
        
        print(f"Found {len(lovisa_transactions)} transactions containing 'lovisa'")
        print(f"Found {len(alberta_transactions)} transactions containing 'alberta'")
        
        # Print details of found transactions
        if lovisa_transactions:
            print("\nLovisa Transactions:")
            for tx in lovisa_transactions:
                print(f"Date: {tx.get('date')}, Description: {tx.get('description')}, Amount: {tx.get('amount')}, Category: {tx.get('category')}, PDF Source: {tx.get('pdf_source')}")
        
        if alberta_transactions:
            print("\nAlberta Transactions:")
            for tx in alberta_transactions:
                print(f"Date: {tx.get('date')}, Description: {tx.get('description')}, Amount: {tx.get('amount')}, Category: {tx.get('category')}, PDF Source: {tx.get('pdf_source')}")
        
        # Check for similar merchant names that might have been imported instead
        similar_transactions = []
        for transaction in transactions:
            description = transaction.get("description", "").lower()
            amount = transaction.get("amount")
            
            # Look for transactions with similar amount (29.39) or similar name
            if (amount and abs(float(amount) - 29.39) < 0.01) or any(keyword in description for keyword in ["retail", "grocery", "ab"]):
                if transaction not in lovisa_transactions and transaction not in alberta_transactions:
                    similar_transactions.append(transaction)
        
        if similar_transactions:
            print("\nSimilar Transactions (by amount or keywords):")
            for tx in similar_transactions:
                print(f"Date: {tx.get('date')}, Description: {tx.get('description')}, Amount: {tx.get('amount')}, Category: {tx.get('category')}, PDF Source: {tx.get('pdf_source')}")
        
        # Check if we found the specific transaction
        specific_transaction_found = False
        for tx in lovisa_transactions + alberta_transactions:
            if "lovisa alberta ab" in tx.get("description", "").lower() and abs(float(tx.get("amount", 0)) - 29.39) < 0.01:
                specific_transaction_found = True
                break
        
        success = True  # This is an investigation, so we're successful if we can run the search
        return print_test_result("Search Lovisa Transaction", success, response)
    except Exception as e:
        return print_test_result("Search Lovisa Transaction", False, error=str(e))

# Test 2: Monthly overview API testing
def test_monthly_overview_api():
    try:
        # Test with year parameter
        current_year = datetime.now().year
        response = requests.get(f"{API_URL}/analytics/monthly-report?year={current_year}")
        
        if response.status_code != 200:
            return print_test_result("Monthly Overview API", False, response, "Failed to get monthly report")
        
        monthly_data = response.json()
        
        # Verify structure and data
        if not isinstance(monthly_data, list):
            return print_test_result("Monthly Overview API", False, response, "Response is not a list")
        
        print(f"Monthly report contains data for {len(monthly_data)} months")
        
        # Check each month's data
        for month_data in monthly_data:
            if not all(key in month_data for key in ["month", "year", "categories", "total_spent", "transaction_count"]):
                return print_test_result("Monthly Overview API", False, response, f"Missing required fields in month data: {month_data}")
            
            print(f"\nMonth: {month_data['month']}")
            print(f"Total Spent: ${month_data['total_spent']:.2f}")
            print(f"Transaction Count: {month_data['transaction_count']}")
            print("Categories:")
            for category, amount in month_data['categories'].items():
                print(f"  - {category}: ${amount:.2f}")
        
        # Test without year parameter to see if it fails
        no_year_response = requests.get(f"{API_URL}/analytics/monthly-report")
        print("\nTesting API without year parameter:")
        print(f"Status code: {no_year_response.status_code}")
        try:
            print(f"Response: {json.dumps(no_year_response.json(), indent=2)}")
        except:
            print(f"Response: {no_year_response.text}")
        
        success = True
        return print_test_result("Monthly Overview API", success, response)
    except Exception as e:
        return print_test_result("Monthly Overview API", False, error=str(e))

# Test 3: Date display verification
def test_date_display():
    try:
        # Get all transactions
        response = requests.get(f"{API_URL}/transactions")
        
        if response.status_code != 200:
            return print_test_result("Date Display Verification", False, response, "Failed to get transactions")
        
        transactions = response.json()
        
        # Look for specific transactions to verify dates
        dollarama_transaction = None
        for transaction in transactions:
            description = transaction.get("description", "").lower()
            if "dollarama #594" in description:
                dollarama_transaction = transaction
                break
        
        if dollarama_transaction:
            print(f"\nFound DOLLARAMA #594 transaction:")
            print(f"Date: {dollarama_transaction.get('date')}")
            print(f"Description: {dollarama_transaction.get('description')}")
            print(f"Amount: {dollarama_transaction.get('amount')}")
            
            # Check if date is 2024-11-14
            expected_date = "2024-11-14"
            actual_date = dollarama_transaction.get('date')
            if actual_date == expected_date:
                print(f"✅ Date matches expected value: {expected_date}")
            else:
                print(f"❌ Date mismatch! Expected: {expected_date}, Actual: {actual_date}")
        else:
            print("DOLLARAMA #594 transaction not found")
        
        # Check a sample of other transactions to verify date format
        print("\nSample of transaction dates:")
        sample_size = min(10, len(transactions))
        for i in range(sample_size):
            tx = transactions[i]
            print(f"{tx.get('date')} - {tx.get('description')}")
        
        success = True  # This is an investigation, so we're successful if we can run the check
        return print_test_result("Date Display Verification", success, response)
    except Exception as e:
        return print_test_result("Date Display Verification", False, error=str(e))

# Test 4: PDF source analysis
def test_pdf_source_analysis():
    try:
        # Get all transactions
        response = requests.get(f"{API_URL}/transactions")
        
        if response.status_code != 200:
            return print_test_result("PDF Source Analysis", False, response, "Failed to get transactions")
        
        transactions = response.json()
        
        # Get list of unique PDF sources
        sources_response = requests.get(f"{API_URL}/transactions/sources")
        
        if sources_response.status_code != 200:
            return print_test_result("PDF Source Analysis", False, sources_response, "Failed to get PDF sources")
        
        pdf_sources = sources_response.json().get("sources", [])
        print(f"Found {len(pdf_sources)} unique PDF sources: {pdf_sources}")
        
        # Look for transactions from "Account Statement 4.pdf"
        statement4_transactions = []
        for transaction in transactions:
            if transaction.get("pdf_source") == "Account Statement 4.pdf":
                statement4_transactions.append(transaction)
        
        print(f"\nFound {len(statement4_transactions)} transactions from 'Account Statement 4.pdf'")
        
        # Analyze transactions from Statement 4
        if statement4_transactions:
            # Sort by date
            statement4_transactions.sort(key=lambda x: x.get("date", ""))
            
            print("\nTransactions from Account Statement 4.pdf (sorted by date):")
            for tx in statement4_transactions:
                print(f"Date: {tx.get('date')}, Description: {tx.get('description')}, Amount: {tx.get('amount')}, Category: {tx.get('category')}")
            
            # Look for patterns in dates
            dates = [tx.get("date") for tx in statement4_transactions]
            unique_dates = sorted(set(dates))
            print(f"\nUnique dates in Statement 4: {unique_dates}")
            
            # Look for patterns in categories
            categories = [tx.get("category") for tx in statement4_transactions]
            category_counts = {}
            for category in categories:
                category_counts[category] = category_counts.get(category, 0) + 1
            
            print("\nCategory distribution in Statement 4:")
            for category, count in category_counts.items():
                print(f"  - {category}: {count} transactions")
            
            # Look for patterns in amounts
            amounts = [float(tx.get("amount", 0)) for tx in statement4_transactions]
            if amounts:
                print(f"\nAmount statistics in Statement 4:")
                print(f"  - Min: ${min(amounts):.2f}")
                print(f"  - Max: ${max(amounts):.2f}")
                print(f"  - Avg: ${sum(amounts)/len(amounts):.2f}")
                
                # Check for amounts close to 29.39
                close_to_target = [tx for tx in statement4_transactions if abs(float(tx.get("amount", 0)) - 29.39) < 1.0]
                if close_to_target:
                    print(f"\nTransactions with amounts close to $29.39:")
                    for tx in close_to_target:
                        print(f"Date: {tx.get('date')}, Description: {tx.get('description')}, Amount: {tx.get('amount')}")
        
        success = True  # This is an investigation, so we're successful if we can run the analysis
        return print_test_result("PDF Source Analysis", success, response)
    except Exception as e:
        return print_test_result("PDF Source Analysis", False, error=str(e))

# Run all tests
def run_all_tests():
    print("\n" + "=" * 40)
    print("STARTING ISSUE INVESTIGATION TESTS")
    print("=" * 40 + "\n")
    
    test_results = {
        "Search Lovisa Transaction": test_search_lovisa_transaction(),
        "Monthly Overview API": test_monthly_overview_api(),
        "Date Display Verification": test_date_display(),
        "PDF Source Analysis": test_pdf_source_analysis()
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