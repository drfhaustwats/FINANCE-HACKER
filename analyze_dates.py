#!/usr/bin/env python3
import requests
import json
from datetime import datetime

# Get backend URL
def get_backend_url():
    with open('/app/frontend/.env', 'r') as f:
        for line in f:
            if line.startswith('REACT_APP_BACKEND_URL='):
                return line.strip().split('=')[1].strip('"\'')
    return None

BACKEND_URL = get_backend_url()
API_URL = f"{BACKEND_URL}/api"

# Get all transactions and analyze dates
response = requests.get(f"{API_URL}/transactions")
if response.status_code == 200:
    transactions = response.json()
    
    print("Sample of transactions to check for date offset:")
    print("=" * 80)
    
    # Group by date to see patterns
    dates_with_transactions = {}
    for trans in transactions:
        trans_date = trans.get('date')
        if trans_date not in dates_with_transactions:
            dates_with_transactions[trans_date] = []
        dates_with_transactions[trans_date].append(trans.get('description', ''))
    
    # Show transactions by date to spot patterns
    sorted_dates = sorted(dates_with_transactions.keys())
    
    print("Transactions grouped by date (first 15 dates):")
    for i, date_key in enumerate(sorted_dates[:15]):
        transactions_on_date = dates_with_transactions[date_key]
        print(f"\n{date_key} ({len(transactions_on_date)} transactions):")
        for j, desc in enumerate(transactions_on_date[:3]):  # Show first 3 per date
            print(f"  {j+1}. {desc[:60]}...")
        if len(transactions_on_date) > 3:
            print(f"  ... and {len(transactions_on_date) - 3} more")
    
    # Look for specific patterns that might indicate offset
    print(f"\n\nLooking for date patterns that might indicate offset...")
    print("=" * 80)
    
    # Check for consecutive dates with similar transactions (might indicate offset)
    consecutive_patterns = []
    for i in range(len(sorted_dates) - 1):
        date1 = sorted_dates[i]
        date2 = sorted_dates[i + 1]
        
        # Parse dates to check if they're consecutive
        try:
            d1 = datetime.fromisoformat(date1).date()
            d2 = datetime.fromisoformat(date2).date()
            diff = (d2 - d1).days
            
            if diff == 1:  # Consecutive days
                trans1 = dates_with_transactions[date1]
                trans2 = dates_with_transactions[date2]
                
                # Look for similar merchant names on consecutive days
                for t1 in trans1:
                    for t2 in trans2:
                        # Simple similarity check
                        t1_words = set(t1.upper().split())
                        t2_words = set(t2.upper().split())
                        common_words = t1_words.intersection(t2_words)
                        
                        if len(common_words) >= 2:  # At least 2 words in common
                            consecutive_patterns.append({
                                'date1': date1,
                                'date2': date2, 
                                'trans1': t1,
                                'trans2': t2,
                                'common': common_words
                            })
        except:
            pass
    
    if consecutive_patterns:
        print(f"Found {len(consecutive_patterns)} suspicious consecutive date patterns:")
        for i, pattern in enumerate(consecutive_patterns[:5]):  # Show first 5
            print(f"\n{i+1}. Consecutive dates with similar transactions:")
            print(f"   {pattern['date1']}: {pattern['trans1'][:50]}...")
            print(f"   {pattern['date2']}: {pattern['trans2'][:50]}...")
            print(f"   Common words: {pattern['common']}")
    else:
        print("No obvious consecutive date patterns found.")
    
    # Check PDF sources to see if there are multiple versions
    print(f"\n\nChecking PDF sources...")
    print("=" * 40)
    
    pdf_sources = set()
    for trans in transactions:
        pdf_source = trans.get('pdf_source')
        if pdf_source:
            pdf_sources.add(pdf_source)
    
    print(f"Found {len(pdf_sources)} PDF sources:")
    for source in sorted(pdf_sources):
        # Count transactions from this source
        source_trans = [t for t in transactions if t.get('pdf_source') == source]
        print(f"  {source}: {len(source_trans)} transactions")
        
        # Show date range for this source
        source_dates = [t.get('date') for t in source_trans if t.get('date')]
        if source_dates:
            min_date = min(source_dates)
            max_date = max(source_dates)
            print(f"    Date range: {min_date} to {max_date}")
            
else:
    print(f"Failed to get transactions: {response.status_code}")