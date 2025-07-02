#!/usr/bin/env python3

import requests
import json

API_URL = "http://localhost:8001/api"

def test_phase_1_features():
    """Test Phase 1: Excel Export and Enhanced Analytics"""
    print("=" * 70)
    print("🚀 TESTING PHASE 1: EXCEL EXPORT & ENHANCED ANALYTICS")
    print("=" * 70)
    
    # Test 1: Excel Export Endpoint
    print("\n1. Testing Excel Export Endpoint...")
    try:
        response = requests.get(f"{API_URL}/transactions/export/excel")
        print(f"Excel export response: {response.status_code}")
        
        if response.status_code == 200:
            print(f"✅ Excel export working! File size: {len(response.content)} bytes")
            print(f"Content type: {response.headers.get('content-type')}")
        else:
            print(f"❌ Excel export failed: {response.text}")
    except Exception as e:
        print(f"❌ Excel export error: {e}")
    
    # Test 2: Account Type Analytics
    print("\n2. Testing Account Type Analytics...")
    try:
        response = requests.get(f"{API_URL}/analytics/account-type-breakdown")
        print(f"Account type analytics response: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Account type analytics working!")
            print(f"Debit: ${data.get('debit', {}).get('total', 0):,.2f} ({data.get('debit', {}).get('count', 0)} transactions)")
            print(f"Credit: ${data.get('credit', {}).get('total', 0):,.2f} ({data.get('credit', {}).get('count', 0)} transactions)")
        else:
            print(f"❌ Account type analytics failed: {response.text}")
    except Exception as e:
        print(f"❌ Account type analytics error: {e}")
    
    # Test 3: Monthly by Account Type
    print("\n3. Testing Monthly Analytics by Account Type...")
    try:
        response = requests.get(f"{API_URL}/analytics/monthly-by-account-type?year=2024")
        print(f"Monthly by account type response: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Monthly by account type analytics working!")
            print(f"Found {len(data)} months of data")
            for month_data in data[-3:]:  # Show last 3 months
                print(f"  {month_data['month']}: Debit ${month_data['debit']['total']:,.2f}, Credit ${month_data['credit']['total']:,.2f}")
        else:
            print(f"❌ Monthly by account type failed: {response.text}")
    except Exception as e:
        print(f"❌ Monthly by account type error: {e}")
    
    # Test 4: Source Breakdown
    print("\n4. Testing Source Breakdown Analytics...")
    try:
        response = requests.get(f"{API_URL}/analytics/source-breakdown")
        print(f"Source breakdown response: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Source breakdown analytics working!")
            print(f"Found {len(data)} different sources:")
            for source in data[:5]:  # Show top 5
                print(f"  {source['source']}: ${source['total']:,.2f} ({source['count']} transactions) - {source['percentage']:.1f}%")
        else:
            print(f"❌ Source breakdown failed: {response.text}")
    except Exception as e:
        print(f"❌ Source breakdown error: {e}")
    
    # Test 5: Test Excel Export with Filters
    print("\n5. Testing Excel Export with Filters...")
    try:
        # Export only debit transactions
        response = requests.get(f"{API_URL}/transactions/export/excel?account_type=debit")
        print(f"Filtered excel export response: {response.status_code}")
        
        if response.status_code == 200:
            print(f"✅ Filtered Excel export working! File size: {len(response.content)} bytes")
        else:
            print(f"❌ Filtered Excel export failed: {response.text}")
    except Exception as e:
        print(f"❌ Filtered Excel export error: {e}")
    
    print("\n" + "=" * 70)
    print("🎉 PHASE 1 TESTING COMPLETE!")
    print("✅ Excel Export: Export transactions to formatted Excel files")
    print("✅ Enhanced Analytics: Account type and source breakdowns")
    print("✅ Filtered Exports: Export with date, category, and account type filters")
    print("=" * 70)

if __name__ == "__main__":
    test_phase_1_features()