#!/usr/bin/env python3
import requests
import json
import sys
from datetime import datetime, date, timedelta

# Get backend URL
def get_backend_url():
    with open('/app/frontend/.env', 'r') as f:
        for line in f:
            if line.startswith('REACT_APP_BACKEND_URL='):
                return line.strip().split('=')[1].strip('"\'')
    return None

BACKEND_URL = get_backend_url()
API_URL = f"{BACKEND_URL}/api"

def test_current_transactions_dates():
    """Check existing transactions to see if dates have offset issue"""
    try:
        response = requests.get(f"{API_URL}/transactions")
        if response.status_code == 200:
            transactions = response.json()
            print(f"Found {len(transactions)} existing transactions")
            
            # Look for patterns in dates
            print("\nFirst 10 transactions with dates:")
            for i, trans in enumerate(transactions[:10]):
                print(f"{i+1}. {trans.get('date')} - {trans.get('description', '')[:50]}...")
                
            # Check if we can identify any obvious date issues
            print("\nAnalyzing dates for potential offset issues...")
            
            # Look for transactions that might show the offset pattern
            suspicious_patterns = []
            for trans in transactions:
                desc = trans.get('description', '').lower()
                trans_date = trans.get('date', '')
                
                # Look for transactions that might indicate date problems
                if any(keyword in desc for keyword in ['payment', 'thank you', 'paiement']):
                    suspicious_patterns.append({
                        'date': trans_date,
                        'description': desc,
                        'type': 'payment'
                    })
            
            if suspicious_patterns:
                print(f"Found {len(suspicious_patterns)} payment-type transactions:")
                for p in suspicious_patterns[:3]:  # Show first 3
                    print(f"  {p['date']} - {p['description']}")
            
            return True
        else:
            print(f"Failed to get transactions: {response.status_code}")
            return False
    except Exception as e:
        print(f"Error checking transactions: {e}")
        return False

def upload_test_pdf():
    """Upload the created test PDF and check the extracted dates"""
    try:
        pdf_path = '/tmp/cibc_test.pdf'
        
        with open(pdf_path, 'rb') as f:
            files = {'file': ('cibc_test.pdf', f, 'application/pdf')}
            response = requests.post(f"{API_URL}/transactions/pdf-import", files=files)
        
        if response.status_code == 200:
            result = response.json()
            print(f"PDF upload successful!")
            print(f"Imported: {result.get('imported_count', 0)} transactions")
            print(f"Duplicates: {result.get('duplicate_count', 0)} transactions")
            
            # Get the newly imported transactions
            source_file = result.get('source_file')
            if source_file:
                trans_response = requests.get(f"{API_URL}/transactions?pdf_source={source_file}")
                if trans_response.status_code == 200:
                    imported_transactions = trans_response.json()
                    
                    print(f"\nImported transactions from {source_file}:")
                    print("Expected vs Actual dates:")
                    
                    # Expected dates from our test data
                    expected_dates = {
                        'JOHN & ROSS / AC CALG': '2024-10-26',
                        'LYFT *RIDE THU 2PM': '2024-10-31', 
                        'STOKES': '2024-10-31',
                        'WINNERSHOMESENSE4160': '2024-11-01',
                        'DOLLARAMA #504': '2024-11-14'
                    }
                    
                    for trans in imported_transactions:
                        desc = trans.get('description', '')
                        actual_date = trans.get('date', '')
                        
                        # Try to match with expected dates
                        for expected_desc, expected_date in expected_dates.items():
                            if expected_desc in desc.upper():
                                if actual_date != expected_date:
                                    # Parse dates to check offset
                                    try:
                                        actual_parsed = datetime.fromisoformat(actual_date).date()
                                        expected_parsed = datetime.fromisoformat(expected_date).date()
                                        offset = (actual_parsed - expected_parsed).days
                                        print(f"  OFFSET FOUND: {desc[:30]}...")
                                        print(f"    Expected: {expected_date}")
                                        print(f"    Actual:   {actual_date}")
                                        print(f"    Offset:   {offset} days")
                                    except:
                                        print(f"  DATE PARSING ERROR: {desc[:30]}...")
                                        print(f"    Expected: {expected_date}")
                                        print(f"    Actual:   {actual_date}")
                                else:
                                    print(f"  ✓ CORRECT: {desc[:30]}... -> {actual_date}")
                                break
                    
                    return True
                else:
                    print(f"Failed to get imported transactions: {trans_response.status_code}")
            else:
                print("No source file in response")
        else:
            print(f"PDF upload failed: {response.status_code}")
            print(f"Response: {response.text}")
        
        return False
    except Exception as e:
        print(f"Error uploading PDF: {e}")
        return False

if __name__ == "__main__":
    print("Testing Date Offset Issue")
    print("=" * 50)
    
    print("\n1. Checking existing transactions...")
    test_current_transactions_dates()
    
    print("\n2. Testing PDF upload with known dates...")
    upload_test_pdf()