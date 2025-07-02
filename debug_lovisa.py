#!/usr/bin/env python3
import re
from datetime import datetime, date

def parse_date_string(date_str: str, statement_year: int) -> date:
    """Parse date string like 'Oct 22' with given year"""
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

def test_lovisa_line_parsing():
    """Test the specific Lovisa transaction line through the parsing logic"""
    
    # The exact line from the user's statement
    test_line = "Oct 13 Oct 15 Lovisa Alberta AB Retail and Grocery 29.39"
    
    print("Testing Lovisa transaction line parsing...")
    print(f"Input line: '{test_line}'")
    print("=" * 80)
    
    # Step 1: Check if it passes the initial filters
    has_month_day = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}', test_line)
    has_decimal_amount = re.search(r'\d+\.\d{2}', test_line)
    
    print(f"1. Has month/day pattern: {bool(has_month_day)}")
    if has_month_day:
        print(f"   Found: '{has_month_day.group()}'")
    
    print(f"2. Has decimal amount: {bool(has_decimal_amount)}")
    if has_decimal_amount:
        print(f"   Found: '{has_decimal_amount.group()}'")
    
    if not (has_month_day and has_decimal_amount):
        print("❌ FAILED: Line doesn't pass initial transaction detection")
        return False
    
    # Step 2: Extract amount
    amount_matches = re.findall(r'(\d{1,3}(?:,\d{3})*\.\d{2})', test_line)
    print(f"3. Amount matches: {amount_matches}")
    
    if not amount_matches:
        print("❌ FAILED: No amount found")
        return False
    
    # Take the last amount as the transaction amount
    amount_str = amount_matches[-1]
    clean_amount_str = amount_str.replace(',', '')
    print(f"   Selected amount: '{amount_str}' -> '{clean_amount_str}'")
    
    # Step 3: Remove amount to get date and description part
    amount_pos = test_line.rfind(amount_str)
    line_without_amount = test_line[:amount_pos].strip()
    print(f"4. Line without amount: '{line_without_amount}'")
    
    # Step 4: Extract dates
    date_pattern = re.match(r'(\w{3}\s+\d{1,2})\s+(\w{3}\s+\d{1,2})\s+(.+)', line_without_amount)
    if not date_pattern:
        print("❌ FAILED: Date pattern match failed")
        print(f"   Pattern: r'(\\w{{3}}\\s+\\d{{1,2}})\\s+(\\w{{3}}\\s+\\d{{1,2}})\\s+(.+)'")
        print(f"   Input: '{line_without_amount}'")
        return False
    
    trans_date_str, post_date_str, description_and_category = date_pattern.groups()
    print(f"5. Date extraction successful:")
    print(f"   Trans date: '{trans_date_str}'")
    print(f"   Post date: '{post_date_str}'")
    print(f"   Rest: '{description_and_category}'")
    
    # Step 5: Check if it's a payment (would be skipped)
    desc_and_cat = description_and_category.strip()
    payment_keywords = [
        'PAYMENT THANK YOU', 'PAIEMENT MERCI', 'PAYMENT - THANK YOU', 
        'THANK YOU FOR YOUR PAYMENT', 'PAYMENT RECEIVED'
    ]
    
    is_payment = any(payment_keyword in desc_and_cat.upper() for payment_keyword in payment_keywords)
    print(f"6. Is payment (would be skipped): {is_payment}")
    
    if is_payment:
        print("❌ FAILED: Would be skipped as payment")
        return False
    
    # Step 6: Parse dates
    statement_year = 2024
    transaction_date = parse_date_string(trans_date_str, statement_year)
    
    if not transaction_date:
        print("❌ FAILED: Date parsing failed")
        return False
    
    print(f"7. Parsed transaction date: {transaction_date}")
    
    # Step 7: Test amount conversion
    try:
        amount = float(clean_amount_str)
        print(f"8. Parsed amount: ${amount}")
    except Exception as e:
        print(f"❌ FAILED: Amount conversion failed: {e}")
        return False
    
    print("\n✅ SUCCESS: This transaction should be imported!")
    print(f"Final result:")
    print(f"  Date: {transaction_date}")
    print(f"  Description: {desc_and_cat}")
    print(f"  Amount: ${amount}")
    
    return True

def test_existing_patterns():
    """Test with some existing patterns to compare"""
    
    print("\n" + "=" * 80)
    print("TESTING EXISTING PATTERNS FOR COMPARISON")
    print("=" * 80)
    
    # Some lines that we know work (from previous data)
    working_lines = [
        "Oct 26 Oct 28 JOHN & ROSS / AC CALG CALG AB Retail and Grocery 90.34",
        "Nov 01 Nov 01 WINNERSHOMESENSE4160 ROCKY VIEW AB Retail and Grocery 15.74",
        "Nov 14 Nov 15 DOLLARAMA # 594 CALGARY AB Retail and Grocery 54.34"
    ]
    
    for line in working_lines:
        print(f"\nTesting working line: '{line}'")
        has_month_day = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}', line)
        has_decimal_amount = re.search(r'\d+\.\d{2}', line)
        print(f"  Month/day: {bool(has_month_day)}, Decimal: {bool(has_decimal_amount)}")
        
        if has_month_day and has_decimal_amount:
            amount_matches = re.findall(r'(\d{1,3}(?:,\d{3})*\.\d{2})', line)
            if amount_matches:
                amount_str = amount_matches[-1]
                amount_pos = line.rfind(amount_str)
                line_without_amount = line[:amount_pos].strip()
                date_pattern = re.match(r'(\w{3}\s+\d{1,2})\s+(\w{3}\s+\d{1,2})\s+(.+)', line_without_amount)
                if date_pattern:
                    print(f"  ✅ Pattern matched: {date_pattern.groups()}")
                else:
                    print(f"  ❌ Pattern failed on: '{line_without_amount}'")

if __name__ == "__main__":
    print("DEBUGGING MISSING LOVISA TRANSACTION")
    print("=" * 80)
    
    # Test the specific Lovisa line
    success = test_lovisa_line_parsing()
    
    if success:
        print("\n🤔 The parsing logic should work for this line!")
        print("The issue might be:")
        print("1. The line format in the actual PDF is different")
        print("2. The PDF text extraction is not capturing this line")
        print("3. There's a bug elsewhere in the processing")
    
    # Test some working patterns for comparison
    test_existing_patterns()