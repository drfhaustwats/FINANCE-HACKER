#!/usr/bin/env python3
import requests
import json

# Get backend URL
def get_backend_url():
    with open('/app/frontend/.env', 'r') as f:
        for line in f:
            if line.startswith('REACT_APP_BACKEND_URL='):
                return line.strip().split('=')[1].strip('"\'')
    return None

BACKEND_URL = get_backend_url()
API_URL = f"{BACKEND_URL}/api"

# Get transactions from Account Statement 4
response = requests.get(f"{API_URL}/transactions?pdf_source=Account Statement 4.pdf")

if response.status_code == 200:
    transactions = response.json()
    print(f"Found {len(transactions)} transactions from Account Statement 4.pdf:")
    print("=" * 80)
    
    # Sort by date
    transactions.sort(key=lambda x: x.get('date', ''))
    
    for i, trans in enumerate(transactions, 1):
        print(f"{i:2d}. {trans.get('date')} | ${trans.get('amount'):>8.2f} | {trans.get('description')}")
    
    print("\n" + "=" * 80)
    print("ANALYSIS:")
    
    # Check date range
    dates = [trans.get('date') for trans in transactions if trans.get('date')]
    if dates:
        print(f"Date range: {min(dates)} to {max(dates)}")
    
    # Check for Oct 13 transactions
    oct13_transactions = [trans for trans in transactions if trans.get('date') == '2024-10-13']
    print(f"Transactions on Oct 13: {len(oct13_transactions)}")
    for trans in oct13_transactions:
        print(f"  - {trans.get('description')} (${trans.get('amount')})")
    
    # Check for any "Lovisa" or "Alberta" in descriptions
    lovisa_found = False
    alberta_found = False
    for trans in transactions:
        desc = trans.get('description', '').lower()
        if 'lovisa' in desc:
            lovisa_found = True
            print(f"Found Lovisa: {trans}")
        if 'alberta' in desc and 'lovisa' in desc:
            alberta_found = True
            print(f"Found Alberta: {trans}")
    
    if not lovisa_found:
        print("❌ No transactions containing 'Lovisa' found")
    if not alberta_found:
        print("❌ No transactions containing 'Alberta' found")
    
    # Look for transactions around Oct 13-15 range
    print(f"\nTransactions in Oct 13-15 range:")
    for trans in transactions:
        date_str = trans.get('date', '')
        if date_str.startswith('2024-10-1') and date_str >= '2024-10-13' and date_str <= '2024-10-15':
            print(f"  {date_str} | ${trans.get('amount'):>8.2f} | {trans.get('description')}")
    
else:
    print(f"Failed to get transactions from Account Statement 4: {response.status_code}")
    print(response.text)