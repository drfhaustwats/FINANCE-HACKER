#!/usr/bin/env python3
"""
Test script to verify transaction sign handling with CIBC statement
"""
import sys
import os
import tempfile
import base64
from pathlib import Path

# Add the backend directory to the Python path
sys.path.append('/app/backend')

# Now import from the backend
from server import (
    extract_text_from_pdf, 
    parse_transactions_from_text, 
    detect_statement_format
)

# Test data - this simulates the CIBC credit card statement content the user provided
CIBC_TEST_TRANSACTIONS = [
    # Format: Trans Date, Post Date, Description, Category, Amount
    "Oct 22    Oct 24    PAYMENT THANK YOU/PAIEMENT MERCI                           1,085.99",
    "Oct 26    Oct 28    JOHN & ROSS'S NW CALG CALGARY    AB    Retail and Grocery   90.34", 
    "Oct 31    Nov 01    LYFT *RIDE THU 2PM    VANCOUVER   BC    Transportation       14.09",
    "Oct 31    Nov 01    STOKES             ROCKY VIEW    AB    Home and Office Improvement  73.48",
    "Nov 01    Nov 01    WESTHILLSSHOPPINGS 4100 ROCKY VIEW  AB    Retail and Grocery  15.74",
    "Nov 01    Nov 01    WINNERSHOMEDENSE4166 ROCKY VIEW   AB    Retail and Grocery   67.15",
    "Nov 05    Nov 06    APPLE.COM/BILL         866-712-7753 ON  Retail and Grocery    52.49",
    "Nov 06    Nov 07    STAPLES STORE #253    CALGARY    AB    Retail and Grocery     0.67",
    "Nov 06    Nov 07    H&M CAN SUPERSTORE #1  CALGARY   AB    Retail and Grocery    35.05",
    "Nov 06    Nov 07    REAL CDN SUPERSTORE #1  CALGARY  AB    Retail and Grocery    47.56",
    "Nov 07    Nov 08    LYFT *RIDE THU 12PM   VANCOUVER  BC    Transportation        20.87",
    "Nov 07    Nov 09    LYFT *RIDE FRI 4PM    VANCOUVER  BC    Transportation        17.99",
    "Nov 07    Nov 12    SKY 360              CALGARY    AB    Restaurants            23.16",
    "Nov 08    Nov 12    MOUNTAINWAREHOUSE.COM VANCOUVER  BC    Retail and Grocery     62.99",
    "Nov 08    Nov 12    LYFT *RIDE THU 8PM   VANCOUVER  BC    Transportation         27.99",
    "Nov 08    Nov 12    JOHN & ROSS'S NW CALG CALGARY   AB    Retail and Grocery     92.79",
    "Nov 10    Nov 12    APPLE.COM/BILL        TORONTO    ON    Hotel, Entertainment and Recreation  13.64",
    "Nov 14    Nov 15    DOLLARAMA # 594      CALGARY    AB    Retail and Grocery     54.34",
    # Continuation from page 2
    "Nov 14    Nov 15    A&W FOREST LAWN      CALGARY    AB    Restaurants            24.00",
    "Nov 14    Nov 15    T&T SUPERMARKET #333  CALGARY   AB    Retail and Grocery     63.05",
    "Nov 15    Nov 15    HONG KONG FOOD MARKET CALGARY   AB    Retail and Grocery      2.79"
]

def test_transaction_signs():
    """Test transaction sign handling with CIBC data"""
    print("🧪 Testing Transaction Sign Handling with CIBC Statement")
    print("=" * 60)
    
    # Simulate PDF text content
    pdf_text = """
CIBC
JANE AGBAOHWO
Account number: 4500 XXXX XXXX 8519
Statement Date: November 15, 2024

Your new charges and credits
Trans   Post
date    date    Description                     Spend Categories       Amount($)

""" + "\n".join(CIBC_TEST_TRANSACTIONS) + """

Total for 4500 XXXX XXXX 8519                                          $765.84
"""
    
    print("📄 Simulated PDF Text Preview:")
    print("-" * 40)
    print(pdf_text[:500] + "...")
    print("-" * 40)
    
    # Test format detection
    format_type = detect_statement_format(pdf_text)
    print(f"🔍 Detected Format: {format_type}")
    
    # Parse transactions
    print("\n📊 Parsing Transactions...")
    try:
        transactions = parse_transactions_from_text(pdf_text, "test_user", "test_statement.pdf")
        
        print(f"\n✅ Successfully parsed {len(transactions)} transactions")
        print("\n📋 Transaction Details:")
        print("-" * 80)
        
        # Analyze transaction signs
        positive_count = 0
        negative_count = 0
        
        for i, trans in enumerate(transactions, 1):
            amount = trans['amount']
            sign_indicator = "🔴 OUTFLOW" if amount > 0 else "🟢 INFLOW"
            abs_amount = abs(amount)
            
            if amount > 0:
                positive_count += 1
            else:
                negative_count += 1
            
            print(f"{i:2}. {trans['date']} | {trans['description'][:40]:<40} | ${abs_amount:>8.2f} | {sign_indicator}")
        
        print("-" * 80)
        print(f"📈 Summary:")
        print(f"   Total Transactions: {len(transactions)}")
        print(f"   Outflows (Charges): {positive_count} transactions")
        print(f"   Inflows (Credits):  {negative_count} transactions")
        
        # Check for specific expected transactions
        print(f"\n🔍 Verification Checks:")
        
        # Look for payment transaction (should be negative/inflow)
        payment_found = False
        for trans in transactions:
            if "PAYMENT THANK YOU" in trans['description']:
                payment_found = True
                is_correct_sign = trans['amount'] < 0
                print(f"   Payment Transaction: {'✅ CORRECT' if is_correct_sign else '❌ WRONG'} (${abs(trans['amount']):.2f} as {'inflow' if trans['amount'] < 0 else 'outflow'})")
                break
        
        if not payment_found:
            print(f"   Payment Transaction: ❌ NOT FOUND")
        
        # Look for regular purchase (should be positive/outflow)
        purchase_found = False
        for trans in transactions:
            if "DOLLARAMA" in trans['description']:
                purchase_found = True
                is_correct_sign = trans['amount'] > 0
                print(f"   Purchase Transaction: {'✅ CORRECT' if is_correct_sign else '❌ WRONG'} (${abs(trans['amount']):.2f} as {'outflow' if trans['amount'] > 0 else 'inflow'})")
                break
        
        if not purchase_found:
            print(f"   Purchase Transaction: ❌ NOT FOUND")
        
        return True
        
    except Exception as e:
        print(f"❌ Error parsing transactions: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_debit_vs_credit_handling():
    """Test different handling for debit vs credit statements"""
    print("\n\n🏦 Testing Debit vs Credit Statement Handling")
    print("=" * 60)
    
    # Test credit card format (current data)
    print("📊 Credit Card Statement:")
    credit_success = test_transaction_signs()
    
    # Test debit format simulation
    print("\n\n📊 Debit Account Statement (Simulated):")
    debit_text = """
CIBC Account Summary
JANE AGBAOHWO
For Oct 1 to Oct 31, 2024

Transaction Details
Date        Description                         Withdrawals($)  Deposits($)  Balance($)
Oct 15      GROCERY STORE PURCHASE             45.67                        1,234.56
Oct 16      PAYROLL DEPOSIT                                    2,500.00     3,689.89
Oct 17      ATM WITHDRAWAL                     60.00                        3,629.89
"""
    
    try:
        format_type = detect_statement_format(debit_text)
        print(f"🔍 Detected Format: {format_type}")
        
        debit_transactions = parse_transactions_from_text(debit_text, "test_user", "test_debit.pdf")
        print(f"✅ Parsed {len(debit_transactions)} debit transactions")
        
        for trans in debit_transactions:
            amount = trans['amount']
            sign_indicator = "🔴 WITHDRAWAL" if amount > 0 else "🟢 DEPOSIT"
            abs_amount = abs(amount)
            print(f"   {trans['description'][:30]:<30} | ${abs_amount:>8.2f} | {sign_indicator}")
        
    except Exception as e:
        print(f"❌ Error with debit parsing: {e}")
    
    return True

if __name__ == "__main__":
    print("🚀 Starting Transaction Sign Handling Tests")
    print("=" * 60)
    
    # Run the tests
    success = test_transaction_signs()
    test_debit_vs_credit_handling()
    
    print("\n" + "=" * 60)
    print(f"🏁 Test Complete: {'✅ SUCCESS' if success else '❌ FAILED'}")