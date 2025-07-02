#!/usr/bin/env python3
import requests
import json
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

# Test Monthly Report API with detailed debugging
def test_monthly_report_detailed():
    try:
        # First, get all transactions to understand what data we have
        transactions_response = requests.get(f"{API_URL}/transactions")
        
        if transactions_response.status_code != 200:
            return print_test_result("Monthly Report API (Detailed)", False, transactions_response, "Failed to get transactions")
        
        transactions = transactions_response.json()
        
        # Analyze transaction dates to understand what months/years we have data for
        years_months = {}
        for transaction in transactions:
            date_str = transaction.get("date", "")
            if date_str:
                try:
                    date_parts = date_str.split("-")
                    if len(date_parts) >= 2:
                        year = date_parts[0]
                        month = date_parts[1]
                        
                        if year not in years_months:
                            years_months[year] = set()
                        years_months[year].add(month)
                except Exception as e:
                    print(f"Error parsing date {date_str}: {e}")
        
        print("Transaction data available for:")
        for year, months in years_months.items():
            print(f"Year {year}: Months {sorted(list(months))}")
        
        # Test with each year we have data for
        for year in years_months.keys():
            print(f"\nTesting monthly report for year {year}")
            response = requests.get(f"{API_URL}/analytics/monthly-report?year={year}")
            
            if response.status_code != 200:
                print(f"Failed to get monthly report for year {year}")
                continue
            
            monthly_data = response.json()
            
            if not monthly_data:
                print(f"No monthly data returned for year {year} despite having transactions for this year")
            else:
                print(f"Monthly report for year {year} contains data for {len(monthly_data)} months")
                for month_data in monthly_data:
                    print(f"  - Month: {month_data.get('month')}, Total: ${month_data.get('total_spent'):.2f}, Transactions: {month_data.get('transaction_count')}")
        
        # Test with explicit user_id parameter
        print("\nTesting with explicit user_id parameter")
        response = requests.get(f"{API_URL}/analytics/monthly-report?year=2024&user_id=default_user")
        
        if response.status_code != 200:
            print(f"Failed to get monthly report with explicit user_id")
        else:
            monthly_data = response.json()
            if not monthly_data:
                print(f"No monthly data returned with explicit user_id despite having transactions")
            else:
                print(f"Monthly report with explicit user_id contains data for {len(monthly_data)} months")
        
        # Check the implementation of the monthly report function in server.py
        print("\nAnalyzing monthly report implementation:")
        print("1. The get_monthly_report function in server.py should group transactions by month")
        print("2. It should filter transactions by the provided year parameter")
        print("3. It should use the user_id from the dependency function get_current_user_id")
        print("4. Check if there's an issue with date format conversion when grouping by month")
        print("5. Check if there's an issue with the defaultdict initialization for monthly_data")
        
        success = True  # This is an investigation, so we're successful if we can run the analysis
        return print_test_result("Monthly Report API (Detailed)", success, response)
    except Exception as e:
        return print_test_result("Monthly Report API (Detailed)", False, error=str(e))

if __name__ == "__main__":
    test_monthly_report_detailed()