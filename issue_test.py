#!/usr/bin/env python3
import requests
import json
import os
import sys
import re
from datetime import datetime, date, timedelta
import io
import PyPDF2
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import pdfplumber

# Get the backend URL from the frontend .env file
def get_backend_url():
    with open('/app/frontend/.env', 'r') as f:
        for line in f:
            if line.startswith('REACT_APP_BACKEND_URL='):
                return line.strip().split('=')[1].strip('"\'')
    return None

BACKEND_URL = get_backend_url()
if not BACKEND_URL:
    print("Error: Could not find REACT_APP_BACKEND_URL in frontend/.env")
    sys.exit(1)

API_URL = f"{BACKEND_URL}/api"
print(f"Using API URL: {API_URL}")

# Helper function to print test results
def print_test_result(test_name, success, response=None, error=None, details=None):
    print(f"\n{'=' * 80}")
    print(f"TEST: {test_name}")
    print(f"STATUS: {'SUCCESS' if success else 'FAILURE'}")
    
    if response:
        print(f"RESPONSE STATUS: {response.status_code}")
        try:
            print(f"RESPONSE BODY: {json.dumps(response.json(), indent=2)}")
        except:
            print(f"RESPONSE BODY: {response.text}")
    
    if error:
        print(f"ERROR: {error}")
        
    if details:
        print(f"DETAILS: {details}")
    
    print(f"{'=' * 80}\n")
    return success

# Helper function to create a test PDF with transaction data for date testing
def create_test_pdf_with_dates(filepath):
    c = canvas.Canvas(filepath, pagesize=letter)
    c.setFont("Helvetica", 12)
    
    # Add a title and statement period
    c.drawString(100, 750, "CIBC DIVIDEND VISA INFINITE CARD")
    c.drawString(100, 730, "JOHN SMITH")
    c.drawString(100, 710, "Statement Period: October 16 to November 15, 2024")
    
    # Add transaction headers
    c.drawString(100, 670, "TRANS   POST    DESCRIPTION                      SPEND CATEGORIES        AMOUNT($)")
    c.drawString(100, 650, "---------------------------------------------------------------------------------")
    
    # Add transactions with specific dates for testing
    transactions = [
        "Oct 16   Oct 17   AMAZON.COM PURCHASE            Retail and Grocery        45.99",
        "Oct 17   Oct 18   STARBUCKS COFFEE               Restaurants               5.75",
        "Oct 18   Oct 19   UBER RIDE                      Transportation            12.50",
        "Oct 19   Oct 20   WALMART STORE #123             Retail and Grocery        67.89",
        "Oct 20   Oct 21   NETFLIX SUBSCRIPTION           Entertainment             14.99"
    ]
    
    y_position = 630
    for trans in transactions:
        c.drawString(100, y_position, trans)
        y_position -= 20
    
    c.save()
    print(f"Created test PDF at {filepath}")
    return filepath

# Test 1: Check current transactions in the database
def test_current_transactions():
    try:
        response = requests.get(f"{API_URL}/transactions")
        success = response.status_code == 200
        
        if success:
            transactions = response.json()
            print(f"Found {len(transactions)} transactions in the database")
            
            # Analyze dates in transactions
            date_analysis = {}
            for transaction in transactions:
                date_str = transaction.get('date')
                if date_str:
                    try:
                        # Parse the date string to a date object
                        transaction_date = datetime.fromisoformat(date_str).date()
                        
                        # Store in our analysis
                        month_year = transaction_date.strftime('%Y-%m')
                        if month_year not in date_analysis:
                            date_analysis[month_year] = 0
                        date_analysis[month_year] += 1
                    except Exception as e:
                        print(f"Error parsing date '{date_str}': {e}")
            
            # Print date analysis
            print("\nTransaction date distribution by month:")
            for month_year, count in sorted(date_analysis.items()):
                print(f"  {month_year}: {count} transactions")
                
            return print_test_result("Current Transactions Check", success, response, 
                                    details=f"Found {len(transactions)} transactions across {len(date_analysis)} months")
        else:
            return print_test_result("Current Transactions Check", success, response)
    except Exception as e:
        return print_test_result("Current Transactions Check", False, error=str(e))

# Test 2: Check monthly report analytics
def test_monthly_report_analytics():
    try:
        # Get current year
        current_year = datetime.now().year
        
        # Test with explicit year parameter
        response = requests.get(f"{API_URL}/analytics/monthly-report?year={current_year}")
        success = response.status_code == 200
        
        if success:
            monthly_data = response.json()
            print(f"Monthly report contains data for {len(monthly_data)} months")
            
            # Check if any months have data
            has_data = False
            for month in monthly_data:
                if month.get('total_spent', 0) > 0:
                    has_data = True
                    break
            
            if not has_data:
                print("WARNING: Monthly report contains no spending data")
            
            # Test without year parameter (should return empty array)
            response_no_year = requests.get(f"{API_URL}/analytics/monthly-report")
            if response_no_year.status_code != 200:
                print("WARNING: Monthly report fails without year parameter")
                success = False
            elif response_no_year.json():
                print("WARNING: Monthly report returns data without year parameter")
            
            return print_test_result("Monthly Report Analytics", success, response, 
                                    details=f"Monthly report contains data for {len(monthly_data)} months, has_data={has_data}")
        else:
            return print_test_result("Monthly Report Analytics", success, response)
    except Exception as e:
        return print_test_result("Monthly Report Analytics", False, error=str(e))

# Test 3: Check category breakdown analytics
def test_category_breakdown_analytics():
    try:
        # Test with explicit user_id parameter
        response = requests.get(f"{API_URL}/analytics/category-breakdown?user_id=default_user")
        success = response.status_code == 200
        
        if success:
            category_data = response.json()
            print(f"Category breakdown contains data for {len(category_data)} categories")
            
            # Check if any categories have data
            has_data = False
            for category in category_data:
                if category.get('amount', 0) > 0:
                    has_data = True
                    break
            
            if not has_data:
                print("WARNING: Category breakdown contains no spending data")
                
            # Test without user_id parameter (should use default)
            response_no_user = requests.get(f"{API_URL}/analytics/category-breakdown")
            if response_no_user.status_code != 200:
                print("WARNING: Category breakdown fails without explicit user_id parameter")
                success = False
            
            return print_test_result("Category Breakdown Analytics", success, response, 
                                    details=f"Category breakdown contains data for {len(category_data)} categories, has_data={has_data}")
        else:
            return print_test_result("Category Breakdown Analytics", success, response)
    except Exception as e:
        return print_test_result("Category Breakdown Analytics", False, error=str(e))

# Test 4: Test PDF import date extraction
def test_pdf_import_date_extraction():
    try:
        # Create a test PDF file with specific dates
        pdf_path = '/tmp/date_test.pdf'
        create_test_pdf_with_dates(pdf_path)
        
        # Upload the PDF file
        with open(pdf_path, 'rb') as f:
            files = {'file': ('date_test.pdf', f, 'application/pdf')}
            response = requests.post(f"{API_URL}/transactions/pdf-import", files=files)
        
        success = response.status_code == 200
        
        if success:
            # Get the imported transactions
            imported_count = response.json().get('imported_count', 0)
            
            if imported_count > 0:
                # Get all transactions from this PDF source
                pdf_source = response.json().get('source_file')
                if pdf_source:
                    transactions_response = requests.get(f"{API_URL}/transactions?pdf_source={pdf_source}")
                    
                    if transactions_response.status_code == 200:
                        imported_transactions = transactions_response.json()
                        
                        # Check for date offset issues
                        date_issues = []
                        expected_dates = {
                            "Oct 16": "2024-10-16",
                            "Oct 17": "2024-10-17",
                            "Oct 18": "2024-10-18",
                            "Oct 19": "2024-10-19",
                            "Oct 20": "2024-10-20"
                        }
                        
                        for transaction in imported_transactions:
                            # Extract the description to match with expected date
                            desc = transaction.get('description', '')
                            actual_date = transaction.get('date')
                            
                            # Try to determine expected date from description
                            expected_date = None
                            if "AMAZON" in desc:
                                expected_date = expected_dates.get("Oct 16")
                            elif "STARBUCKS" in desc:
                                expected_date = expected_dates.get("Oct 17")
                            elif "UBER" in desc:
                                expected_date = expected_dates.get("Oct 18")
                            elif "WALMART" in desc:
                                expected_date = expected_dates.get("Oct 19")
                            elif "NETFLIX" in desc:
                                expected_date = expected_dates.get("Oct 20")
                            
                            if expected_date and actual_date != expected_date:
                                date_issues.append({
                                    "description": desc,
                                    "expected_date": expected_date,
                                    "actual_date": actual_date
                                })
                        
                        if date_issues:
                            print("FOUND DATE OFFSET ISSUES:")
                            for issue in date_issues:
                                print(f"  Description: {issue['description']}")
                                print(f"  Expected: {issue['expected_date']}")
                                print(f"  Actual: {issue['actual_date']}")
                                print()
                            
                            # Check if all dates are consistently off by -1 day
                            all_minus_one = True
                            for issue in date_issues:
                                expected = datetime.fromisoformat(issue['expected_date']).date()
                                actual = datetime.fromisoformat(issue['actual_date']).date()
                                if expected - actual != timedelta(days=1):
                                    all_minus_one = False
                                    break
                            
                            if all_minus_one:
                                print("CONFIRMED: All dates are consistently offset by -1 day")
                            else:
                                print("Date offsets are not consistent")
                            
                            success = False
                            
                        return print_test_result("PDF Import Date Extraction", success, response, 
                                                details=f"Imported {imported_count} transactions, found {len(date_issues)} date issues")
            
            return print_test_result("PDF Import Date Extraction", success, response, 
                                    details=f"Imported {imported_count} transactions")
        else:
            return print_test_result("PDF Import Date Extraction", success, response)
    except Exception as e:
        return print_test_result("PDF Import Date Extraction", False, error=str(e))

# Test 5: Analyze PDF parsing function directly
def test_pdf_parsing_function():
    try:
        # Create a test PDF file with specific dates
        pdf_path = '/tmp/parse_test.pdf'
        create_test_pdf_with_dates(pdf_path)
        
        # Extract text from PDF
        with open(pdf_path, 'rb') as f:
            pdf_content = f.read()
            
        text = ""
        try:
            # Use pdfplumber to extract text
            with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            print(f"pdfplumber extraction failed: {e}")
            
            # Fallback to PyPDF2
            try:
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_content))
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            except Exception as e2:
                print(f"PyPDF2 extraction also failed: {e2}")
                return print_test_result("PDF Parsing Function", False, error="Could not extract text from PDF")
        
        # Print extracted text for analysis
        print("EXTRACTED TEXT FROM PDF:")
        print("-" * 40)
        print(text)
        print("-" * 40)
        
        # Look for date patterns in the text
        date_patterns = []
        for line in text.split('\n'):
            # Look for transaction date patterns (e.g., "Oct 16")
            matches = re.findall(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2})', line)
            if matches:
                date_patterns.append({
                    "line": line,
                    "matches": matches
                })
        
        print(f"Found {len(date_patterns)} lines with date patterns")
        for pattern in date_patterns:
            print(f"  Line: {pattern['line']}")
            print(f"  Matches: {pattern['matches']}")
            print()
        
        return print_test_result("PDF Parsing Function", True, details=f"Extracted text and found {len(date_patterns)} date patterns")
    except Exception as e:
        return print_test_result("PDF Parsing Function", False, error=str(e))

# Run all tests
def run_issue_tests():
    print("\n" + "=" * 40)
    print("STARTING ISSUE-SPECIFIC TESTS")
    print("=" * 40 + "\n")
    
    test_results = {
        "Current Transactions Check": test_current_transactions(),
        "Monthly Report Analytics": test_monthly_report_analytics(),
        "Category Breakdown Analytics": test_category_breakdown_analytics(),
        "PDF Import Date Extraction": test_pdf_import_date_extraction(),
        "PDF Parsing Function": test_pdf_parsing_function()
    }
    
    print("\n" + "=" * 40)
    print("TEST SUMMARY")
    print("=" * 40)
    
    all_passed = True
    for test_name, result in test_results.items():
        status = "PASSED" if result else "FAILED"
        if not result:
            all_passed = False
        print(f"{test_name}: {status}")
    
    print("\nOVERALL RESULT: " + ("PASSED" if all_passed else "FAILED"))
    print("=" * 40 + "\n")
    
    return all_passed

if __name__ == "__main__":
    run_issue_tests()