#!/usr/bin/env python3
import sys
import re
from datetime import datetime, date
import pdfplumber
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

def create_cibc_test_pdf(filepath):
    """Create a test PDF that mirrors the exact format of the user's CIBC statement"""
    c = canvas.Canvas(filepath, pagesize=letter)
    c.setFont("Helvetica", 10)
    
    # Add header information matching CIBC format
    c.drawString(50, 750, "CIBC")
    c.drawString(50, 730, "Prepared for: JANE OGHENERUEMU AGBAOHWO - October 16 to November 15, 2024")
    c.drawString(50, 710, "Account number: 4500 XXXX XXXX 8519")
    
    # Add section headers
    c.drawString(50, 680, "Your new charges and credits")
    c.drawString(50, 660, "Trans    Post")
    c.drawString(120, 660, "Description")
    c.drawString(350, 660, "Spend Categories")
    c.drawString(450, 660, "Amount($)")
    c.drawString(50, 645, "date     date")
    
    # Add actual transactions from the user's PDF
    transactions = [
        "Oct 25   Oct 26   PAYMENT THANK YOU/PAIEMENT MERCI                                       1,085.99",
        "",
        "Oct 26   Oct 28   JOHN & ROSS / AC CALG   CALG      AB      Retail and Grocery          90.34", 
        "Oct 31   Nov 01   LYFT *RIDE THU 2PM      VANCOUVER BC      Transportation              14.09",
        "Oct 31   Nov 01   STOKES                  ROCKVIEW  AB      Home and Office Improvement 73.48",
        "Nov 01   Nov 01   WINNERSHOMESENSE4160    ROCKY VIEW AB     Retail and Grocery          15.74",
        "Nov 01   Nov 01   WINNERSHOMESENSE4160    ROCKY VIEW AB     Retail and Grocery          67.15",
        "Nov 05   Nov 06   APPLE.COM/BILL          866-712-7753 ON   Retail and Grocery          52.49",
        "Nov 06   Nov 07   STAPLES STORE #253      CALGARY   AB      Retail and Grocery          0.57",
        "Nov 06   Nov 07   REAL CDN SUPERSTORE     CALGARY   AB      Retail and Grocery          47.05",
        "Nov 06   Nov 07   REAL CDN SUPERSTORE #1  CALGARY   AB      Retail and Grocery          47.56",
        "Nov 07   Nov 08   LYFT *RIDE THU 12PM     VANCOUVER BC      Transportation              20.87",
        "Nov 07   Nov 08   LYFT *RIDE THU 4PM      VANCOUVER BC      Transportation              17.99",
        "Nov 07   Nov 12   SKY 360                 CALGARY   AB      Restaurants                 23.16",
        "Nov 08   Nov 12   MOUNTAINWAREHOUSE.COM   VANCOUVER BC      Retail and Grocery          62.99",
        "Nov 08   Nov 12   LYFT *RIDE THU 8PM      VANCOUVER BC      Transportation              27.99",
        "Nov 08   Nov 12   JOHN & ROSS / AC CALG   CALGARY   AB      Retail and Grocery          92.79",
        "Nov 10   Nov 12   APPLE.COM/BILL          TORONTO   ON      Hotel, Entertainment        13.64",
        "Nov 14   Nov 15   DOLLARAMA #504          CALGARY   AB      Retail and Grocery          54.34"
    ]
    
    y_position = 620
    for trans in transactions:
        if trans.strip():  # Skip empty lines
            c.drawString(50, y_position, trans)
        y_position -= 15
    
    c.save()
    print(f"Created CIBC test PDF at {filepath}")
    return filepath

def parse_date_string_test(date_str: str, statement_year: int) -> date:
    """Test version of the date parsing function"""
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
                
                # Smart year logic: if we're in July 2025 and see Oct/Nov dates, they're likely from 2024
                current_year = datetime.now().year
                if not statement_year:
                    if month in [10, 11, 12]:  # Oct/Nov/Dec
                        year = 2024
                    elif month in [1, 2, 3] and datetime.now().month > 6:
                        year = current_year + 1
                    else:
                        year = current_year
                
                parsed_date = date(year, month, int(day))
                print(f"Date parsing: '{date_str}' -> {parsed_date} (year context: {year})")
                return parsed_date
    except Exception as e:
        print(f"Date parsing error for '{date_str}': {e}")
    return None

def test_date_extraction_patterns():
    """Test the regex patterns used for date extraction"""
    
    # Sample lines from CIBC PDF
    test_lines = [
        "Oct 25   Oct 26   PAYMENT THANK YOU/PAIEMENT MERCI                                       1,085.99",
        "Oct 26   Oct 28   JOHN & ROSS / AC CALG   CALG      AB      Retail and Grocery          90.34",
        "Oct 31   Nov 01   LYFT *RIDE THU 2PM      VANCOUVER BC      Transportation              14.09",
        "Nov 01   Nov 01   WINNERSHOMESENSE4160    ROCKY VIEW AB     Retail and Grocery          15.74",
        "Nov 14   Nov 15   DOLLARAMA #504          CALGARY   AB      Retail and Grocery          54.34"
    ]
    
    # Pattern used in backend (from server.py)
    date_pattern = re.compile(r'^([A-Za-z]{3}\s+\d{1,2})\s+([A-Za-z]{3}\s+\d{1,2})\s+(.+)', re.MULTILINE)
    
    print("Testing date extraction patterns:")
    print("=" * 80)
    
    for line in test_lines:
        print(f"\nTesting line: {line}")
        match = date_pattern.match(line.strip())
        if match:
            trans_date, post_date, rest = match.groups()
            print(f"  Trans date: '{trans_date}'")
            print(f"  Post date:  '{post_date}'")
            print(f"  Rest:       '{rest}'")
            
            # Test parsing the transaction date
            parsed_trans = parse_date_string_test(trans_date, 2024)
            parsed_post = parse_date_string_test(post_date, 2024)
            
            print(f"  Parsed trans: {parsed_trans}")
            print(f"  Parsed post:  {parsed_post}")
            
            # Check for offset
            if parsed_trans and parsed_post:
                diff = (parsed_post - parsed_trans).days
                print(f"  Date difference (post - trans): {diff} days")
                
                # The user reports -1 offset, so let's see what happens
                print(f"  User would see: {parsed_trans} (actual transaction date)")
                print(f"  If there's a -1 offset, they'd see: {parsed_trans - timedelta(days=1)}")
        else:
            print(f"  No match found for pattern")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    # Test the date extraction logic
    from datetime import timedelta
    
    print("CIBC Date Parsing Test")
    print("=" * 80)
    
    # Create test PDF
    pdf_path = '/tmp/cibc_test.pdf'
    create_cibc_test_pdf(pdf_path)
    
    # Test date extraction patterns
    test_date_extraction_patterns()
    
    # Test actual PDF parsing with pdfplumber
    print("\nTesting PDF text extraction:")
    print("=" * 40)
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                text = page.extract_text()
                print(f"Page {page_num + 1} text (first 500 chars):")
                print(text[:500])
                print("...")
    except Exception as e:
        print(f"Error reading PDF: {e}")