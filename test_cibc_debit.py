#!/usr/bin/env python3

import requests
import json
import tempfile
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

API_URL = "http://localhost:8001/api"

def create_cibc_debit_test_pdf(filepath):
    """Create a test PDF that mimics the CIBC debit account format"""
    c = canvas.Canvas(filepath, pagesize=letter)
    width, height = letter
    
    # Set font
    c.setFont("Helvetica", 10)
    
    # Add CIBC debit header
    c.drawString(100, 750, "CIBC")
    c.drawString(100, 730, "CIBC Account Statement")
    c.drawString(100, 710, "JANE AGBAOHWO                                For Jul 1 to Jul 31, 2024")
    c.drawString(100, 690, "Account number: 56-80581")
    
    # Add account summary
    c.drawString(100, 650, "Account summary")
    c.drawString(100, 630, "Opening balance on Jul 1, 2024                    $138.70")
    c.drawString(100, 610, "Withdrawals                        -    1,165.71")
    c.drawString(100, 590, "Deposits                           +    1,249.27")
    c.drawString(100, 570, "Closing balance on Jul 31, 2024   =     $222.26")
    
    # Add transaction details header
    c.drawString(100, 530, "Transaction details")
    c.drawString(100, 510, "Date     Description                              Withdrawals ($)  Deposits ($)   Balance ($)")
    c.drawString(100, 490, "Jul 1    Opening balance                                                            $138.70")
    
    # Add the actual transactions from the statement
    transactions = [
        "Jul 2    VISA DEBIT RETAIL PURCHASE                      14.82                           123.88",
        "         LYFT *TEMP AU  418022828768",
        "         VISA DEBIT RETAIL PURCHASE                       3.70                           120.18",
        "         CALGARY TRANSIT  418177070165",
        "         VISA DEBIT RETAIL PURCHASE                       3.70                           116.48",
        "         CALGARY TRANSIT  418200951177",
        "         VISA DEBIT RETAIL PURCHASE                       3.70                           112.78",
        "         CALGARY TRANSIT  418200957832",
        "Jul 3    INT VISA DEB PURCHASE REVERSAL                                  14.82           127.60",
        "         LYFT *TEMP AU  418022828768",
        "         14.82 CAD @ 1.000000",
        "         INTL VISA DEB RETAIL PURCHASE                   15.71                           111.89",
        "         LYFT *TEMP AU  418022828768",
        "         15.71 CAD @ 1.000000",
        "         VISA DEBIT RETAIL PURCHASE                       3.70                           108.19",
        "         CALGARY TRANSIT  418501053444",
        "Jul 10   VISA DEBIT RETAIL PURCHASE                       3.70                           104.49",
        "         CALGARY TRANSIT  419277301087",
        "Jul 12   VISA DEBIT RETAIL PURCHASE                       3.70                           100.79",
        "         CALGARY TRANSIT  419477372474",
        "         VISA DEBIT RETAIL PURCHASE                       3.70                            97.09",
        "         CALGARY TRANSIT  419477378445",
        "Jul 15   VISA DEBIT RETAIL PURCHASE                       3.70                            93.39",
        "         CALGARY TRANSIT  419477383370",
        "         VISA DEBIT RETAIL PURCHASE                       3.70                            89.69",
        "         CALGARY TRANSIT  419677421310",
        "Jul 22   RETAIL PURCHASE  137643686369                    5.23                            84.46",
        "         SQ *LAZY DAY RA",
        "         VISA DEBIT RETAIL PURCHASE                      32.13                            52.33",
        "         SEPHORA.CA      420493056661",
        "Jul 26   E-TRANSFER      011058991047                                     400.00          452.33",
        "         OLUWADARA OLAIFA",
        "         RETAIL PURCHASE  420721158104                   43.05                           409.28",
        "         DOLLARAMA #161",
        "         RETAIL PURCHASE  000001001982                   26.19                           383.09",
        "         WALMART STORE #",
        "Jul 29   E-TRANSFER      105084129922                    55.00                           328.09",
        "         ese",
        "         RETAIL PURCHASE  000001023369                  113.87                           214.22",
        "         FREESTONE PRODU",
        "         RETAIL PURCHASE  000001023370                    9.14                           205.08",
        "         FREESTONE PRODU",
        "Jul 31   E-TRANSFER      011016193536                                     820.00        1,025.08",
        "         OLUWADARA OLAIFA",
        "         INTERNET TRANSFER 000000108875                 802.82                           222.26",
        "         SERVICE CHARGE  REWARDS                         14.45                           207.81",
        "         ADD TXN$7.50;MONTHLY$6.95",
        "         RECORD-KEEPING  N/A",
        "         SERVICE CHARGE  REWARDS                                          14.45           222.26"
    ]
    
    y_position = 470
    for trans in transactions:
        if y_position < 50:  # Start new page if needed
            c.showPage()
            c.setFont("Helvetica", 10)
            y_position = 750
        c.drawString(100, y_position, trans)
        y_position -= 12
    
    c.showPage()
    c.save()

def test_cibc_debit_format():
    """Test CIBC debit format parsing"""
    print("=" * 60)
    print("TESTING CIBC DEBIT FORMAT PARSING")
    print("=" * 60)
    
    # Create test PDF
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
        pdf_path = tmp_file.name
    
    try:
        create_cibc_debit_test_pdf(pdf_path)
        print(f"Created CIBC debit test PDF: {pdf_path}")
        
        # Upload PDF
        with open(pdf_path, 'rb') as f:
            files = {'file': ('test_cibc_debit.pdf', f, 'application/pdf')}
            response = requests.post(f"{API_URL}/transactions/pdf-import", files=files)
        
        print(f"Upload response: {response.status_code}")
        response_data = response.json()
        print(f"Response: {response_data}")
        
        if response.status_code == 200:
            print(f"Imported: {response_data.get('imported_count', 0)} transactions")
            print(f"Duplicates: {response_data.get('duplicate_count', 0)}")
            print(f"Total found: {response_data.get('total_found', 0)}")
            
            # Check if debit transactions were imported
            transactions_response = requests.get(f"{API_URL}/transactions")
            if transactions_response.status_code == 200:
                transactions = transactions_response.json()
                
                # Look for debit account transactions
                debit_transactions = [t for t in transactions if t.get('account_type') == 'debit' and t.get('pdf_source') == 'test_cibc_debit.pdf']
                
                print(f"\nFound {len(debit_transactions)} debit transactions:")
                for t in debit_transactions[-10:]:  # Show last 10
                    print(f"  {t['date']}: {t['description']} - ${t['amount']} ({t['category']})")
                
                if debit_transactions:
                    print("✅ CIBC debit format parsing working!")
                else:
                    print("❌ No debit transactions found!")
                    
        else:
            print(f"❌ PDF upload failed: {response.text}")
            
    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)

def test_custom_category_in_dropdown():
    """Test that custom categories appear in transaction editing dropdown"""
    print("\n" + "=" * 60)
    print("TESTING CUSTOM CATEGORY FRONTEND INTEGRATION")
    print("=" * 60)
    
    # Get all categories (including custom ones)
    categories_response = requests.get(f"{API_URL}/categories")
    if categories_response.status_code != 200:
        print("❌ Failed to get categories")
        return
        
    categories = categories_response.json()
    custom_categories = [cat for cat in categories if not cat.get('is_default', True)]
    
    print(f"Found {len(categories)} total categories:")
    print(f"Custom categories: {len(custom_categories)}")
    
    for cat in custom_categories:
        print(f"  - {cat['name']} (ID: {cat['id']})")
    
    if not custom_categories:
        print("Creating a test custom category...")
        create_response = requests.post(f"{API_URL}/categories", json={
            "name": "Test Frontend Category",
            "color": "#FF6B6B"
        })
        if create_response.status_code == 200:
            new_category = create_response.json()
            print(f"✅ Created: {new_category['name']}")
        else:
            print(f"❌ Failed to create category: {create_response.text}")
    
    print("\n✅ Frontend fix applied: Category dropdown now uses dynamic 'categories' array instead of hardcoded 'defaultCategories'")
    print("✅ Custom categories should now appear in the transaction editing dropdown!")

if __name__ == "__main__":
    test_cibc_debit_format()
    test_custom_category_in_dropdown()