#!/usr/bin/env python3
import requests
import json
from datetime import datetime, date
import re

# Get backend URL
def get_backend_url():
    with open('/app/frontend/.env', 'r') as f:
        for line in f:
            if line.startswith('REACT_APP_BACKEND_URL='):
                return line.strip().split('=')[1].strip('"\'')
    return None

BACKEND_URL = get_backend_url()
API_URL = f"{BACKEND_URL}/api"

def test_dollarama_transaction():
    """Find the specific Dollarama transaction and check the date"""
    try:
        response = requests.get(f"{API_URL}/transactions")
        if response.status_code == 200:
            transactions = response.json()
            
            print("Looking for DOLLARAMA # 594 transaction...")
            print("=" * 60)
            
            dollarama_transactions = []
            for trans in transactions:
                desc = trans.get('description', '').upper()
                if 'DOLLARAMA' in desc and '594' in desc:
                    dollarama_transactions.append(trans)
            
            if dollarama_transactions:
                print(f"Found {len(dollarama_transactions)} DOLLARAMA #594 transactions:")
                for i, trans in enumerate(dollarama_transactions):
                    print(f"\n{i+1}. Transaction details:")
                    print(f"   Date: {trans.get('date')}")
                    print(f"   Description: {trans.get('description')}")
                    print(f"   Amount: ${trans.get('amount')}")
                    print(f"   PDF Source: {trans.get('pdf_source', 'N/A')}")
                    
                    # Check if this is the $54.34 transaction
                    if abs(float(trans.get('amount', 0)) - 54.34) < 0.01:
                        print(f"   *** This is the $54.34 transaction! ***")
                        print(f"   Expected date from PDF: Nov 14 (2024-11-14)")
                        print(f"   Actual date in database: {trans.get('date')}")
                        
                        # Parse the date to check offset
                        try:
                            actual_date = datetime.fromisoformat(trans.get('date')).date()
                            expected_date = date(2024, 11, 14)
                            offset = (actual_date - expected_date).days
                            print(f"   Date offset: {offset} days")
                            
                            if offset == -1:
                                print(f"   ✅ CONFIRMED: -1 day offset bug!")
                            elif offset == 0:
                                print(f"   ❓ No offset found - might be a different issue")
                            else:
                                print(f"   ❓ Unexpected offset: {offset} days")
                        except Exception as e:
                            print(f"   Error parsing dates: {e}")
            else:
                print("No DOLLARAMA #594 transactions found")
                
            return True
        else:
            print(f"Failed to get transactions: {response.status_code}")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_date_parsing_logic():
    """Test the date parsing logic with the exact values from user's statement"""
    print("\nTesting date parsing logic...")
    print("=" * 40)
    
    # Replicate the parse_date_string function
    def parse_date_string_test(date_str: str, statement_year: int) -> date:
        try:
            month_map = {
                'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
            }
            
            parts = date_str.strip().split()
            if len(parts) == 2:
                month_name, day = parts
                month = month_map.get(month_name[:3], None)
                if month:
                    year = statement_year if statement_year else 2024
                    parsed_date = date(year, month, int(day))
                    print(f"Date parsing: '{date_str}' -> {parsed_date}")
                    return parsed_date
        except Exception as e:
            print(f"Date parsing error for '{date_str}': {e}")
        return None
    
    # Test with the exact transaction from the user
    print("Testing: 'Nov 14' should become 2024-11-14")
    result = parse_date_string_test("Nov 14", 2024)
    if result:
        print(f"Result: {result} ({result.isoformat()})")
        if result.isoformat() == "2024-11-14":
            print("✅ Date parsing logic is correct")
        else:
            print("❌ Date parsing logic has an issue")
    else:
        print("❌ Date parsing failed")

def check_statement_year_extraction():
    """Check if there's an issue with statement year extraction"""
    print("\nChecking statement year extraction...")
    print("=" * 40)
    
    # Look for any statements uploaded and check their years
    try:
        response = requests.get(f"{API_URL}/transactions/sources")
        if response.status_code == 200:
            sources_data = response.json()
            sources = sources_data.get('sources', [])
            
            print(f"Found {len(sources)} PDF sources:")
            for source in sources:
                print(f"  - {source}")
                
                # Get transactions from this source
                trans_response = requests.get(f"{API_URL}/transactions?pdf_source={source}")
                if trans_response.status_code == 200:
                    transactions = trans_response.json()
                    if transactions:
                        # Check date range
                        dates = [t.get('date') for t in transactions if t.get('date')]
                        if dates:
                            min_date = min(dates)
                            max_date = max(dates)
                            print(f"    Date range: {min_date} to {max_date}")
                            
                            # Check if all dates are in 2024
                            years = set()
                            for date_str in dates:
                                try:
                                    year = datetime.fromisoformat(date_str).year
                                    years.add(year)
                                except:
                                    pass
                            print(f"    Years found: {sorted(years)}")
        else:
            print(f"Failed to get sources: {response.status_code}")
    except Exception as e:
        print(f"Error checking sources: {e}")

if __name__ == "__main__":
    print("INVESTIGATING DATE OFFSET BUG")
    print("=" * 60)
    
    # Test 1: Find the specific problematic transaction
    test_dollarama_transaction()
    
    # Test 2: Verify date parsing logic
    test_date_parsing_logic()
    
    # Test 3: Check statement year extraction
    check_statement_year_extraction()