#!/usr/bin/env python3

import requests
import json
import tempfile
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

API_URL = "http://localhost:8001/api"

def create_cibc_test_pdf(filepath):
    """Create a test PDF that mimics the CIBC format exactly as shown in user's screenshots"""
    c = canvas.Canvas(filepath, pagesize=letter)
    width, height = letter
    
    # Set font
    c.setFont("Helvetica", 10)
    
    # Add CIBC header
    c.drawString(100, 750, "CIBC")
    c.drawString(100, 730, "Prepared for: JANE OGHENERUEMU AGBAOHWO October 16 to November 15, 2024")
    c.drawString(100, 710, "Your new charges and credits")
    
    # Add transaction headers
    c.drawString(100, 680, "Trans    Post")
    c.drawString(100, 665, "date     date     Description                           Spend Categories                Amount($)")
    c.drawString(100, 650, "Card number 4500 XXXX XXXX 8519")
    
    # Add the exact transactions from the CIBC statement including the problematic Lovisa
    transactions = [
        "Sep 19    Sep 19    AMZN Mktp CA*OU3N84VZ3  WWW.AMAZON.CAON    Personal and Household Expenses    53.54",
        "Sep 19    Sep 19    AMZN Mktp CA*XP7J71EX3  WWW.AMAZON.CAON    Personal and Household Expenses    130.71", 
        "Sep 20    Sep 20    AMZN Mktp CA*QE4BX0783  WWW.AMAZON.CAON    Personal and Household Expenses    68.99",
        "Sep 22    Sep 23    OPENAI *CHATGPT SUBSCR  HTTPSOPENAI.CCA    Foreign Currency Transactions    29.26",
        "Sep 23    Sep 24    AMZN Mktp CA  WWW.AMAZON.CAON  Personal and Household Expenses    -53.54",
        "Sep 24    Sep 25    REAL CDN SUPERSTORE #1  CALGARY    AB    Retail and Grocery    46.43",
        "Sep 24    Sep 25    REAL CDN SUPERSTORE #1  CALGARY    AB    Retail and Grocery    31.87",
        "Sep 24    Sep 25    Country Hills Plates  888-4607771  AB    Professional and Financial Services    19.00",
        "Sep 25    Oct 01    WAL-MART SUPERCENTER#1097CALGARY  AB    Retail and Grocery    7.24",
        "Sep 26    Sep 27    LYFT *RIDE WED 7PM  VANCOUVER  BC    Transportation    12.99",
        "Oct 03    Oct 04    TRANSIT-ESTORE  CALGARY  AB    Professional and Financial Services    40.25",
        "Oct 06    Oct 07    Amazon.ca*4R13D7JM3  AMAZON.CA  ON    Personal and Household Expenses    608.96",
        "Oct 06    Oct 08    LYFT *RIDE SUN 9AM  VANCOUVER  BC    Transportation    20.78",
        "Oct 09    Oct 10    DOORDASHDASHPASS  DOWNTOWN TOROON    Restaurants    10.49",
        "Oct 13    Oct 15    Lovisa  Alberta  AB    Retail and Grocery    29.39",
        "Oct 13    Oct 15    REAL CDN SUPERSTORE #1  CALGARY  AB    Retail and Grocery    29.63"
    ]
    
    y_position = 620
    for trans in transactions:
        c.drawString(100, y_position, trans)
        y_position -= 15
    
    c.showPage()
    c.save()

def test_pdf_import():
    """Test PDF import and check for Lovisa transaction"""
    print("=" * 60)
    print("TESTING PDF IMPORT FOR LOVISA TRANSACTION")
    print("=" * 60)
    
    # Create test PDF
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
        pdf_path = tmp_file.name
    
    try:
        create_cibc_test_pdf(pdf_path)
        print(f"Created test PDF: {pdf_path}")
        
        # Upload PDF
        with open(pdf_path, 'rb') as f:
            files = {'file': ('test_cibc_lovisa.pdf', f, 'application/pdf')}
            response = requests.post(f"{API_URL}/transactions/pdf-import", files=files)
        
        print(f"Upload response: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Imported: {result.get('imported_count', 0)} transactions")
            print(f"Duplicates: {result.get('duplicate_count', 0)}")
            print(f"Total found: {result.get('total_found', 0)}")
            
            # Now check if Lovisa transaction was imported
            transactions_response = requests.get(f"{API_URL}/transactions")
            if transactions_response.status_code == 200:
                transactions = transactions_response.json()
                
                # Look for Lovisa
                lovisa_transactions = [t for t in transactions if 'lovisa' in t.get('description', '').lower()]
                
                print(f"\nFound {len(lovisa_transactions)} Lovisa transactions:")
                for t in lovisa_transactions:
                    print(f"  {t['date']}: {t['description']} - ${t['amount']} (Source: {t.get('pdf_source', 'N/A')})")
                
                if not lovisa_transactions:
                    print("❌ LOVISA TRANSACTION MISSING!")
                    print("\nAll transactions found:")
                    for t in transactions[-20:]:  # Show last 20
                        print(f"  {t['date']}: {t['description']} - ${t['amount']}")
                else:
                    print("✅ Lovisa transaction found!")
                    
        else:
            print(f"❌ PDF upload failed: {response.text}")
            
    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)

def test_custom_category_update():
    """Test updating a transaction to use a custom category"""
    print("\n" + "=" * 60)
    print("TESTING CUSTOM CATEGORY UPDATE")
    print("=" * 60)
    
    # Get all categories
    categories_response = requests.get(f"{API_URL}/categories")
    if categories_response.status_code != 200:
        print("❌ Failed to get categories")
        return
        
    categories = categories_response.json()
    print(f"Found {len(categories)} categories:")
    for cat in categories:
        print(f"  {cat['name']} (ID: {cat['id']}, Default: {cat.get('is_default', False)})")
    
    # Find a custom category
    custom_categories = [cat for cat in categories if not cat.get('is_default', True)]
    if not custom_categories:
        print("No custom categories found. Creating one...")
        # Create a custom category
        create_response = requests.post(f"{API_URL}/categories", json={
            "name": "Test Custom Category",
            "color": "#FF5733"
        })
        if create_response.status_code == 200:
            custom_category = create_response.json()
            print(f"Created custom category: {custom_category['name']} (ID: {custom_category['id']})")
        else:
            print("❌ Failed to create custom category")
            return
    else:
        custom_category = custom_categories[0]
        print(f"Using existing custom category: {custom_category['name']} (ID: {custom_category['id']})")
    
    # Get a transaction to update
    transactions_response = requests.get(f"{API_URL}/transactions")
    if transactions_response.status_code != 200:
        print("❌ Failed to get transactions")
        return
        
    transactions = transactions_response.json()
    if not transactions:
        print("❌ No transactions found")
        return
        
    test_transaction = transactions[0]
    print(f"\nTesting with transaction: {test_transaction['description']} (ID: {test_transaction['id']})")
    print(f"Current category: {test_transaction['category']}")
    
    # Try to update the transaction to use the custom category
    update_response = requests.put(f"{API_URL}/transactions/{test_transaction['id']}", json={
        "category": custom_category['name']
    })
    
    print(f"Update response: {update_response.status_code}")
    if update_response.status_code == 200:
        updated_transaction = update_response.json()
        print(f"✅ Successfully updated category to: {updated_transaction['category']}")
    else:
        print(f"❌ Failed to update category: {update_response.text}")
        
        # Try with category ID instead
        print("Trying with category ID instead of name...")
        update_response2 = requests.put(f"{API_URL}/transactions/{test_transaction['id']}", json={
            "category": custom_category['id']
        })
        print(f"Update response (ID): {update_response2.status_code}")
        if update_response2.status_code == 200:
            updated_transaction = update_response2.json()
            print(f"✅ Successfully updated category to: {updated_transaction['category']}")
        else:
            print(f"❌ Failed to update with ID: {update_response2.text}")

if __name__ == "__main__":
    test_pdf_import()
    test_custom_category_update()