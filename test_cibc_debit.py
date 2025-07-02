#!/usr/bin/env python3

import requests
import json
import tempfile
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

API_URL = "http://localhost:8001/api"

def create_test_credit_pdf(filepath):
    """Create a CIBC credit card test PDF"""
    c = canvas.Canvas(filepath, pagesize=letter)
    c.setFont("Helvetica", 10)
    
    # Add CIBC credit header with user name
    c.drawString(100, 750, "CIBC")
    c.drawString(100, 730, "Prepared for: DANIEL SMITH OCTOBER 1 to OCTOBER 31, 2024")
    c.drawString(100, 710, "Your new charges and credits")
    
    # Add transaction headers
    c.drawString(100, 680, "Trans    Post")
    c.drawString(100, 665, "date     date     Description                           Spend Categories                Amount($)")
    
    # Add transactions
    transactions = [
        "Oct 05    Oct 07    STARBUCKS COFFEE SHOP                 Restaurants                     15.99",
        "Oct 08    Oct 09    AMAZON PRIME SUBSCRIPTION             Professional Services           14.99",
        "Oct 10    Oct 11    LOVISA JEWELRY STORE                  Retail and Grocery             45.99"
    ]
    
    y_position = 620
    for trans in transactions:
        c.drawString(100, y_position, trans)
        y_position -= 20
    
    c.save()

def create_test_debit_pdf(filepath):
    """Create a CIBC debit account test PDF"""
    c = canvas.Canvas(filepath, pagesize=letter)
    c.setFont("Helvetica", 10)
    
    # Add CIBC debit header with user name in the format shown
    c.drawString(100, 750, "CIBC")
    c.drawString(100, 730, "CIBC Account Statement")
    c.drawString(100, 710, "SARAH JOHNSON                           For Oct 1 to Oct 31, 2024")
    c.drawString(100, 690, "Account number: 56-12345")
    
    # Add transaction details
    c.drawString(100, 650, "Transaction details")
    c.drawString(100, 630, "Date     Description                              Withdrawals ($)  Deposits ($)   Balance ($)")
    
    # Add transactions
    transactions = [
        "Oct 01   Opening balance                                                            1000.00",
        "Oct 05   VISA DEBIT RETAIL PURCHASE                      25.99                      974.01",
        "         TIM HORTONS #1234",
        "Oct 08   E-TRANSFER    RENT PAYMENT                      800.00                     174.01",
        "         TO: LANDLORD PROPERTIES",
        "Oct 12   VISA DEBIT RETAIL PURCHASE                      67.50                      106.51",
        "         GROCERY STORE SUPERMARKET"
    ]
    
    y_position = 610
    for trans in transactions:
        c.drawString(100, y_position, trans)
        y_position -= 15
    
    c.save()

def test_enhanced_source_naming():
    """Test that source names are enhanced with user names and account types"""
    print("=" * 70)
    print("TESTING ENHANCED SOURCE NAMING & ACCOUNT TYPE FEATURES")
    print("=" * 70)
    
    # Test 1: Credit card statement
    print("\n1. Testing Credit Card Statement (DANIEL'S CREDIT)...")
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
        credit_pdf_path = tmp_file.name
    
    try:
        create_test_credit_pdf(credit_pdf_path)
        
        with open(credit_pdf_path, 'rb') as f:
            files = {'file': ('daniel_credit_statement.pdf', f, 'application/pdf')}
            response = requests.post(f"{API_URL}/transactions/pdf-import", files=files)
        
        print(f"Credit upload response: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Credit imported: {result.get('imported_count', 0)} transactions")
    finally:
        if os.path.exists(credit_pdf_path):
            os.remove(credit_pdf_path)
    
    # Test 2: Debit account statement
    print("\n2. Testing Debit Account Statement (SARAH'S DEBIT)...")
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
        debit_pdf_path = tmp_file.name
    
    try:
        create_test_debit_pdf(debit_pdf_path)
        
        with open(debit_pdf_path, 'rb') as f:
            files = {'file': ('sarah_debit_statement.pdf', f, 'application/pdf')}
            response = requests.post(f"{API_URL}/transactions/pdf-import", files=files)
        
        print(f"Debit upload response: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Debit imported: {result.get('imported_count', 0)} transactions")
    finally:
        if os.path.exists(debit_pdf_path):
            os.remove(debit_pdf_path)
    
    # Test 3: Check the enhanced source names and account types
    print("\n3. Checking Enhanced Source Names and Account Types...")
    transactions_response = requests.get(f"{API_URL}/transactions")
    if transactions_response.status_code == 200:
        transactions = transactions_response.json()
        
        # Look for our test transactions
        test_transactions = [t for t in transactions if t.get('pdf_source') and 
                           ('daniel' in t.get('pdf_source', '').lower() or 
                            'sarah' in t.get('pdf_source', '').lower())]
        
        print(f"\nFound {len(test_transactions)} test transactions:")
        for t in test_transactions:
            print(f"  {t['date']}: {t['description']}")
            print(f"    Source: {t['pdf_source']}")
            print(f"    Account Type: {t['account_type']}")
            print(f"    User: {t.get('user_name', 'N/A')}")
            print()
        
        # Verify enhanced naming patterns
        daniel_credit_found = any('daniel' in t.get('pdf_source', '').lower() and 'credit' in t.get('pdf_source', '').lower() for t in test_transactions)
        sarah_debit_found = any('sarah' in t.get('pdf_source', '').lower() and 'debit' in t.get('pdf_source', '').lower() for t in test_transactions)
        
        if daniel_credit_found:
            print("✅ Daniel's Credit format found!")
        else:
            print("❌ Daniel's Credit format NOT found")
            
        if sarah_debit_found:
            print("✅ Sarah's Debit format found!")
        else:
            print("❌ Sarah's Debit format NOT found")
    
    # Test 4: Account type filtering
    print("\n4. Testing Account Type Filtering...")
    
    # Filter by debit
    debit_response = requests.get(f"{API_URL}/transactions?account_type=debit")
    if debit_response.status_code == 200:
        debit_transactions = debit_response.json()
        print(f"Debit transactions found: {len(debit_transactions)}")
        
    # Filter by credit_card
    credit_response = requests.get(f"{API_URL}/transactions?account_type=credit_card")
    if credit_response.status_code == 200:
        credit_transactions = credit_response.json()
        print(f"Credit transactions found: {len(credit_transactions)}")
    
    print("\n✅ Enhanced source naming and account type filtering tests completed!")

if __name__ == "__main__":
    test_enhanced_source_naming()