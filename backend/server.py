from fastapi import FastAPI, APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, date
import pandas as pd
import io
import json
import re
from collections import defaultdict
import pdfplumber
import PyPDF2

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Security
security = HTTPBearer(auto_error=False)

# Define Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    email: str
    household_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class UserCreate(BaseModel):
    name: str
    email: str
    household_name: Optional[str] = None

class Category(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    color: str = "#3B82F6"
    user_id: str
    household_id: Optional[str] = None
    is_default: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

class CategoryCreate(BaseModel):
    name: str
    color: str = "#3B82F6"

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None

class Transaction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    date: date
    description: str
    category: str
    amount: float
    account_type: str = "credit_card"
    user_id: str
    household_id: Optional[str] = None
    pdf_source: Optional[str] = None  # Track if imported from PDF and source filename
    user_name: Optional[str] = None  # Extracted user name from PDF
    created_at: datetime = Field(default_factory=datetime.utcnow)

class TransactionCreate(BaseModel):
    date: date
    description: str
    category: str
    amount: float
    account_type: str = "credit_card"
    user_id: Optional[str] = "default_user"

class MonthlyReport(BaseModel):
    month: str
    year: int
    categories: dict
    total_spent: float
    transaction_count: int

class CategorySpending(BaseModel):
    category: str
    amount: float
    count: int
    percentage: float

# PDF Processing Functions
def extract_text_from_pdf(file_content: bytes) -> str:
    """Extract text from PDF using multiple methods for better reliability"""
    text = ""
    
    try:
        # Method 1: Using pdfplumber (better for tables and structured data)
        with pdfplumber.open(io.BytesIO(file_content)) as pdf:
            print(f"PDF has {len(pdf.pages)} pages")
            for page_num, page in enumerate(pdf.pages):
                print(f"Processing page {page_num + 1}")
                page_text = page.extract_text()
                if page_text:
                    print(f"Page {page_num + 1} extracted {len(page_text)} characters")
                    text += f"\n--- PAGE {page_num + 1} ---\n" + page_text + "\n"
                else:
                    print(f"Page {page_num + 1} - no text extracted")
                    
                # Also try to extract tables
                tables = page.extract_tables()
                if tables:
                    print(f"Page {page_num + 1} has {len(tables)} tables")
                    for table_num, table in enumerate(tables):
                        text += f"\n--- TABLE {table_num + 1} ON PAGE {page_num + 1} ---\n"
                        for row in table:
                            if row and any(cell for cell in row if cell):  # Skip empty rows
                                text += " | ".join(str(cell) if cell else "" for cell in row) + "\n"
    
    except Exception as e:
        logging.warning(f"pdfplumber extraction failed: {e}")
        
        # Method 2: Fallback to PyPDF2
        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
            print(f"PyPDF2: PDF has {len(pdf_reader.pages)} pages")
            for page_num, page in enumerate(pdf_reader.pages):
                page_text = page.extract_text()
                text += f"\n--- PYPDF2 PAGE {page_num + 1} ---\n" + page_text + "\n"
        except Exception as e2:
            logging.error(f"PyPDF2 extraction also failed: {e2}")
            raise HTTPException(status_code=400, detail="Could not extract text from PDF")
    
    print(f"Total extracted text length: {len(text)}")
    print("EXTRACTED TEXT PREVIEW:")
    print("=" * 80)
    print(text[:2000])  # Print first 2000 characters for debugging
    print("=" * 80)
    
    return text

def extract_pdf_metadata(text: str) -> dict:
    """Extract user name and statement period from PDF header"""
    metadata = {
        'user_name': None,
        'statement_start': None,
        'statement_end': None,
        'statement_year': None
    }
    
    lines = text.split('\n')
    
    # Look for user name in first few lines
    for i, line in enumerate(lines[:10]):
        line = line.strip()
        # Look for name patterns (all caps, likely a person's name)
        if re.match(r'^[A-Z\s]{10,50}$', line) and ' ' in line and len(line.split()) >= 2:
            # Skip common bank terms
            if not any(term in line.upper() for term in ['ACCOUNT', 'STATEMENT', 'CARD', 'BANK', 'DIVIDEND']):
                metadata['user_name'] = line.strip()
                break
    
    # Look for statement period
    for line in lines[:20]:
        line = line.strip()
        # Pattern: "October 16to November 15, 2024" or "October 16 to November 15, 2024"
        period_match = re.search(r'(\w+)\s+(\d+)\s*to\s*(\w+)\s+(\d+),?\s*(\d{4})', line, re.IGNORECASE)
        if period_match:
            start_month, start_day, end_month, end_day, year = period_match.groups()
            metadata['statement_start'] = f"{start_month} {start_day}"
            metadata['statement_end'] = f"{end_month} {end_day}"
            metadata['statement_year'] = int(year)
            break
        
        # Alternative pattern: "November 15, 2024" for statement date
        date_match = re.search(r'(\w+)\s+(\d+),?\s*(\d{4})', line)
        if date_match and 'statement' in line.lower():
            month, day, year = date_match.groups()
            metadata['statement_end'] = f"{month} {day}"
            metadata['statement_year'] = int(year)
    
    return metadata

def parse_transactions_from_text(text: str, user_id: str, source_filename: str = None) -> List[dict]:
    """Parse transactions from extracted PDF text - enhanced for multiple bank formats"""
    transactions = []
    
    # Extract metadata first
    metadata = extract_pdf_metadata(text)
    statement_year = metadata.get('statement_year', datetime.now().year)
    user_name = metadata.get('user_name', 'Unknown User')
    
    print(f"Extracted metadata: User: {user_name}, Year: {statement_year}")
    
    # Enhanced patterns for CIBC format specifically
    # The correct format should be: Trans Date, Post Date, Description, Category, Amount
    patterns = [
        # Main CIBC pattern - Trans Date, Post Date, Description, Spend Category, Amount
        r'(\w{3}\s+\d{1,2})\s+(\w{3}\s+\d{1,2})\s+([A-Z0-9\s\#\*\.\-\/\&\(\)]+?)\s+([A-Za-z\s,&]+?)\s+(\d+\.\d{2})(?:\s|$)',
        # Alternative pattern for transactions without clear category
        r'(\w{3}\s+\d{1,2})\s+(\w{3}\s+\d{1,2})\s+([A-Z0-9\s\#\*\.\-\/\&\(\)]+?)\s+(\d+\.\d{2})(?:\s|$)',
        # Catch remaining patterns
        r'(\w{3}\s+\d{1,2})\s+([A-Z0-9\s\#\*\.\-\/\&\(\)]{10,})\s+(\d+\.\d{2})(?:\s|$)'
    ]
    
def parse_transactions_from_text(text: str, user_id: str, source_filename: str = None) -> List[dict]:
    """Parse transactions from extracted PDF text - enhanced for CIBC format"""
    transactions = []
    
    # Extract metadata first
    metadata = extract_pdf_metadata(text)
    statement_year = metadata.get('statement_year', datetime.now().year)
    user_name = metadata.get('user_name', 'Unknown User')
    
    print(f"Extracted metadata: User: {user_name}, Year: {statement_year}")
    
    # Split by pages and tables to process each section
    sections = text.split('--- PAGE')
    
    for section_num, section in enumerate(sections):
        if not section.strip():
            continue
            
        print(f"\n=== PROCESSING SECTION {section_num} ===")
        print(f"Section preview: {section[:500]}...")
        
        lines = section.split('\n')
        
        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line or len(line) < 15:
                continue
                
            # Skip header lines
            if any(header in line.upper() for header in [
                'TRANS', 'POST', 'DESCRIPTION', 'SPEND CATEGORIES', 'AMOUNT',
                'CARD NUMBER', 'PAGE', 'CIBC', 'DIVIDEND', 'VISA'
            ]):
                continue
            
            # Look for transaction patterns - be more comprehensive
            # Debug: Check if this line looks like a transaction
            has_date_pattern = re.search(r'\w{3}\s+\d{1,2}', line)
            has_amount = re.search(r'\d+\.\d{2}', line)
            
            if has_date_pattern and has_amount:
                print(f"POTENTIAL TRANSACTION LINE: {line}")
                
                transaction_match = None
                
                # Strategy 1: Look for clear amount at the end
                amount_at_end = re.search(r'(\d+\.\d{2})(?:\s*)$', line)
                if amount_at_end:
                    amount_str = amount_at_end.group(1)
                    line_without_amount = line[:amount_at_end.start()].strip()
                    
                    # Now extract dates from the beginning
                    date_pattern = re.match(r'(\w{3}\s+\d{1,2})\s+(\w{3}\s+\d{1,2})\s+(.+)', line_without_amount)
                    if date_pattern:
                        trans_date_str, post_date_str, description_and_category = date_pattern.groups()
                        
                        # Try to split description and category
                        desc_and_cat = description_and_category.strip()
                        
                        # Look for known categories at the end
                        category_str = ""
                        description = desc_and_cat
                        
                        # Check for category keywords at the end
                        known_categories = [
                            'Foreign Currency Transactions',
                            'Hotel, Entertainment and Recreation', 
                            'Professional and Financial Services',
                            'Home and Office Improvement',
                            'Health and Education',
                            'Retail and Grocery',
                            'Transportation',
                            'Restaurants',
                            'Personal and Household Expenses'
                        ]
                        
                        for cat in known_categories:
                            if desc_and_cat.endswith(cat):
                                category_str = cat
                                description = desc_and_cat[:-len(cat)].strip()
                                break
                        
                        transaction_match = (trans_date_str, post_date_str, description, category_str, amount_str)
                        print(f"STRATEGY 1 PARSED: Trans={trans_date_str}, Desc='{description}', Cat='{category_str}', Amt={amount_str}")
                
                # Strategy 2: If strategy 1 didn't work, use original regex patterns
                if not transaction_match:
                    # Pattern 1: With clear category separation (multiple spaces)
                    transaction_match = re.search(
                        r'(\w{3}\s+\d{1,2})\s+(\w{3}\s+\d{1,2})\s+([A-Z0-9\*\#\s\.\-\/\&\(\)]+?)\s{2,}([A-Za-z\s,&]+?)\s+(\d+\.\d{2})(?:\s|$)',
                        line
                    )
                    
                    if transaction_match:
                        print(f"STRATEGY 2A MATCH: {transaction_match.groups()}")
                    
                    # Pattern 2: If pattern 1 doesn't work, try with single space separation
                    if not transaction_match:
                        transaction_match = re.search(
                            r'(\w{3}\s+\d{1,2})\s+(\w{3}\s+\d{1,2})\s+(.+?)\s+([A-Z][a-z]+(?:\s+[a-z]+)*(?:\s+and\s+[A-Z][a-z]+)*)\s+(\d+\.\d{2})(?:\s|$)',
                            line
                        )
                        if transaction_match:
                            print(f"STRATEGY 2B MATCH: {transaction_match.groups()}")
            
            # If we found a transaction match, process it
            if transaction_match:
                trans_date_str, post_date_str, description, category_str, amount_str = transaction_match.groups()
                
                print(f"LINE {line_num}: {line}")
                print(f"MATCHED: Trans={trans_date_str}, Post={post_date_str}, Desc='{description}', Cat='{category_str}', Amt={amount_str}")
                
                try:
                    # Parse amount
                    amount = float(amount_str)
                    if amount < 0.01 or amount > 50000:
                        print(f"Skipping amount {amount} (out of range)")
                        continue
                    
                    # Clean description
                    description = re.sub(r'\s+', ' ', description.strip())
                    
                    # Parse transaction date (use trans_date, not post_date!)
                    transaction_date = parse_date_string(trans_date_str, statement_year)
                    if not transaction_date:
                        print(f"Failed to parse date: {trans_date_str}")
                        continue
                    
                    # Clean and categorize
                    category = clean_category(category_str, description)
                    
                    # Create transaction
                    transaction = {
                        'date': transaction_date.isoformat(),
                        'description': description,
                        'category': category,
                        'amount': amount,
                        'account_type': 'credit_card',
                        'user_id': user_id,
                        'pdf_source': source_filename or 'pdf_import',
                        'user_name': user_name
                    }
                    
                    transactions.append(transaction)
                    print(f"✅ ADDED: {description} -> ${amount} on {transaction_date} ({category})")
                    
                except Exception as e:
                    print(f"❌ Error processing transaction: {e}")
                    continue
            
            # Alternative pattern for table rows with | separators
            elif '|' in line and re.search(r'\d+\.\d{2}', line):
                print(f"TABLE ROW: {line}")
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 5:
                    try:
                        # Assume format: trans_date | post_date | description | category | amount
                        trans_date_str = parts[0]
                        description = parts[2] if len(parts) > 2 else ""
                        category_str = parts[3] if len(parts) > 3 else ""
                        amount_str = parts[-1]  # Last part should be amount
                        
                        # Extract numeric amount
                        amount_match = re.search(r'(\d+\.\d{2})', amount_str)
                        if amount_match:
                            amount = float(amount_match.group(1))
                            
                            transaction_date = parse_date_string(trans_date_str, statement_year)
                            if transaction_date and amount > 0.01:
                                category = clean_category(category_str, description)
                                
                                transaction = {
                                    'date': transaction_date.isoformat(),
                                    'description': description.strip(),
                                    'category': category,
                                    'amount': amount,
                                    'account_type': 'credit_card',
                                    'user_id': user_id,
                                    'pdf_source': source_filename or 'pdf_import',
                                    'user_name': user_name
                                }
                                
                                transactions.append(transaction)
                                print(f"✅ TABLE ADDED: {description} -> ${amount} on {transaction_date}")
                                
                    except Exception as e:
                        print(f"❌ Error processing table row: {e}")
                        continue
    
    print(f"\n=== TOTAL TRANSACTIONS FOUND: {len(transactions)} ===")
    
    # Remove duplicates
    unique_transactions = remove_duplicates(transactions)
    
    return unique_transactions

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
                # If no statement year provided, use current year or 2024 for reasonable defaults
                year = statement_year if statement_year else 2024
                
                # Smart year logic: if we're in July 2025 and see Oct/Nov dates, they're likely from 2024
                current_year = datetime.now().year
                if not statement_year:
                    if month in [10, 11, 12] and datetime.now().month < 6:  # Oct/Nov/Dec but we're early in year
                        year = current_year - 1
                    elif month in [1, 2, 3] and datetime.now().month > 6:  # Jan/Feb/Mar but we're late in year  
                        year = current_year + 1
                    else:
                        year = current_year
                
                return date(year, month, int(day))
    except Exception as e:
        print(f"Date parsing error: {e}")
    return None

def clean_category(category_str: str, description: str) -> str:
    """Clean and standardize category"""
    # Category mapping
    category_keywords = {
        'Retail and Grocery': ['superstore', 'grocery', 'dollarama', 'walmart', 'costco', 'loblaws', 'metro', 'sobeys', 'john & ross', 't&t'],
        'Restaurants': ['restaurant', 'coffee', 'starbucks', 'tim hortons', 'mcdonalds', 'pizza', 'food', 'dining', 'cafe', 'a&w', 'forest lawn'],
        'Transportation': ['lyft', 'uber', 'taxi', 'gas', 'petro', 'shell', 'esso', 'transit', 'ride'],
        'Home and Office Improvement': ['home depot', 'lowes', 'staples', 'canadian tire', 'ikea', 'office', 'stokes'],
        'Hotel, Entertainment and Recreation': ['hotel', 'movie', 'netflix', 'spotify', 'apple.com', 'entertainment', 'apple.com/bill'],
        'Professional and Financial Services': ['bank', 'fee', 'transfer', 'mortgage', 'insurance', 'legal', 'openai', 'chatgpt'],
        'Health and Education': ['pharmacy', 'doctor', 'dental', 'hospital', 'school', 'university'],
        'Foreign Currency Transactions': ['foreign', 'currency', 'exchange', 'international', 'usd']
    }
    
    # First try to use provided category if it looks valid
    if category_str and len(category_str.strip()) > 2:
        category_clean = category_str.strip()
        # Check if it matches known categories
        for known_cat in category_keywords.keys():
            if known_cat.lower() in category_clean.lower():
                return known_cat
    
    # Auto-categorize based on description
    description_lower = description.lower()
    
    for cat, keywords in category_keywords.items():
        if any(keyword in description_lower for keyword in keywords):
            return cat
    
    return 'Personal and Household Expenses'  # Default

def remove_duplicates(transactions: List[dict]) -> List[dict]:
    """Remove duplicate transactions"""
    seen = set()
    unique_transactions = []
    
    for transaction in transactions:
        # Create key using date, first few words of description, and amount
        desc_key = ' '.join(transaction['description'].split()[:3])
        key = (transaction['date'], desc_key, transaction['amount'])
        
        if key not in seen:
            seen.add(key)
            unique_transactions.append(transaction)
        else:
            print(f"Skipping duplicate: {transaction['description']} on {transaction['date']}")
    
    print(f"Total parsed: {len(transactions)}, Unique: {len(unique_transactions)}")
    return unique_transactions

# Helper function to get user (for now, use default user)
async def get_current_user_id() -> str:
    return "default_user"

# Initialize default categories
DEFAULT_CATEGORIES = [
    "Retail and Grocery",
    "Restaurants", 
    "Transportation",
    "Home and Office Improvement",
    "Hotel, Entertainment and Recreation",
    "Professional and Financial Services",
    "Health and Education",
    "Foreign Currency Transactions",
    "Personal and Household Expenses"
]

async def initialize_default_categories(user_id: str):
    """Initialize default categories for a user"""
    existing_categories = await db.categories.find({"user_id": user_id}).to_list(100)
    if not existing_categories:
        default_categories = []
        colors = ["#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#06B6D4", "#84CC16", "#F97316", "#6B7280"]
        
        for i, cat_name in enumerate(DEFAULT_CATEGORIES):
            category = Category(
                name=cat_name,
                color=colors[i % len(colors)],
                user_id=user_id,
                is_default=True
            )
            default_categories.append(category.dict())
        
        if default_categories:
            await db.categories.insert_many(default_categories)

# API Routes
@api_router.get("/")
async def root():
    return {"message": "LifeTracker Banking Dashboard API v2.0"}

# User Management
@api_router.post("/users", response_model=User)
async def create_user(user: UserCreate):
    user_data = user.dict()
    user_obj = User(**user_data)
    
    # Convert datetime to string for MongoDB
    user_dict = user_obj.dict()
    user_dict['created_at'] = user_dict['created_at'].isoformat()
    
    await db.users.insert_one(user_dict)
    
    # Initialize default categories for the user
    await initialize_default_categories(user_obj.id)
    
    return user_obj

@api_router.get("/users", response_model=List[User])
async def get_users():
    users = await db.users.find().to_list(100)
    return [User(**user) for user in users]

# Category Management
@api_router.get("/categories", response_model=List[Category])
async def get_categories(user_id: str = Depends(get_current_user_id)):
    await initialize_default_categories(user_id)  # Ensure categories exist
    categories = await db.categories.find({"user_id": user_id}).to_list(100)
    return [Category(**category) for category in categories]

@api_router.post("/categories", response_model=Category)
async def create_category(category: CategoryCreate, user_id: str = Depends(get_current_user_id)):
    category_data = category.dict()
    category_obj = Category(**category_data, user_id=user_id)
    
    # Convert datetime to string for MongoDB
    category_dict = category_obj.dict()
    category_dict['created_at'] = category_dict['created_at'].isoformat()
    
    await db.categories.insert_one(category_dict)
    return category_obj

@api_router.put("/categories/{category_id}", response_model=Category)
async def update_category(category_id: str, category_update: CategoryUpdate, user_id: str = Depends(get_current_user_id)):
    update_data = {k: v for k, v in category_update.dict().items() if v is not None}
    
    result = await db.categories.update_one(
        {"id": category_id, "user_id": user_id},
        {"$set": update_data}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Category not found")
    
    updated_category = await db.categories.find_one({"id": category_id, "user_id": user_id})
    return Category(**updated_category)

@api_router.delete("/categories/{category_id}")
async def delete_category(category_id: str, user_id: str = Depends(get_current_user_id)):
    # Check if category is being used by transactions
    transactions_using_category = await db.transactions.count_documents({"category": category_id, "user_id": user_id})
    
    if transactions_using_category > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete category. It is used by {transactions_using_category} transactions."
        )
    
    result = await db.categories.delete_one({"id": category_id, "user_id": user_id, "is_default": {"$ne": True}})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Category not found or cannot delete default category")
    
    return {"message": "Category deleted successfully"}

# Transaction Management (Enhanced)
@api_router.post("/transactions", response_model=Transaction)
async def create_transaction(transaction: TransactionCreate):
    transaction_dict = transaction.dict()
    if not transaction_dict.get('user_id'):
        transaction_dict['user_id'] = await get_current_user_id()
    
    transaction_obj = Transaction(**transaction_dict)
    
    # Convert date to string for MongoDB storage
    transaction_data = transaction_obj.dict()
    transaction_data['date'] = transaction_data['date'].isoformat()
    transaction_data['created_at'] = transaction_data['created_at'].isoformat()
    
    await db.transactions.insert_one(transaction_data)
    return transaction_obj

@api_router.get("/transactions", response_model=List[Transaction])
async def get_transactions(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category: Optional[str] = None,
    pdf_source: Optional[str] = None,
    sort_by: Optional[str] = "date",
    sort_order: Optional[str] = "desc",
    user_id: str = Depends(get_current_user_id)
):
    filter_dict = {"user_id": user_id}
    
    if start_date:
        filter_dict["date"] = {"$gte": start_date}
    if end_date:
        if "date" in filter_dict:
            filter_dict["date"]["$lte"] = end_date
        else:
            filter_dict["date"] = {"$lte": end_date}
    if category:
        filter_dict["category"] = category
    if pdf_source:
        filter_dict["pdf_source"] = pdf_source
    
    # Handle sorting
    sort_direction = -1 if sort_order == "desc" else 1
    sort_field = sort_by if sort_by in ["date", "amount", "description", "category"] else "date"
    
    transactions = await db.transactions.find(filter_dict).sort(sort_field, sort_direction).to_list(1000)
    return [Transaction(**transaction) for transaction in transactions]

@api_router.get("/transactions/sources")
async def get_pdf_sources(user_id: str = Depends(get_current_user_id)):
    """Get list of unique PDF sources for filtering"""
    sources = await db.transactions.distinct("pdf_source", {"user_id": user_id, "pdf_source": {"$ne": None}})
    return {"sources": sources}

@api_router.delete("/transactions/{transaction_id}")
async def delete_transaction(transaction_id: str, user_id: str = Depends(get_current_user_id)):
    result = await db.transactions.delete_one({"id": transaction_id, "user_id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return {"message": "Transaction deleted successfully"}

# PDF Processing Endpoint
@api_router.post("/transactions/pdf-import")
async def import_transactions_from_pdf(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id)
):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    try:
        # Read PDF content
        content = await file.read()
        
        # Extract text from PDF
        text = extract_text_from_pdf(content)
        
        if not text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from PDF")
        
        # Parse transactions from text - pass the filename
        parsed_transactions = parse_transactions_from_text(text, user_id, file.filename)
        
        if not parsed_transactions:
            return {
                "message": "No transactions found in PDF", 
                "imported_count": 0,
                "extracted_text_preview": text[:500] + "..." if len(text) > 500 else text
            }
        
        # Check for duplicates and insert new transactions
        new_transactions = []
        duplicate_count = 0
        
        for trans_data in parsed_transactions:
            # Check if transaction already exists
            existing = await db.transactions.find_one({
                "user_id": user_id,
                "date": trans_data["date"],
                "description": trans_data["description"],
                "amount": trans_data["amount"]
            })
            
            if not existing:
                transaction_obj = Transaction(**trans_data)
                trans_dict = transaction_obj.dict()
                trans_dict['date'] = trans_dict['date'].isoformat() if hasattr(trans_dict['date'], 'isoformat') else trans_dict['date']
                trans_dict['created_at'] = trans_dict['created_at'].isoformat()
                new_transactions.append(trans_dict)
            else:
                duplicate_count += 1
        
        # Insert new transactions
        if new_transactions:
            await db.transactions.insert_many(new_transactions)
        
        return {
            "message": f"Successfully processed PDF: {file.filename}",
            "imported_count": len(new_transactions),
            "duplicate_count": duplicate_count,
            "total_found": len(parsed_transactions),
            "source_file": file.filename
        }
        
    except Exception as e:
        logging.error(f"PDF processing error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")

# Enhanced Analytics (with user filtering)
@api_router.get("/analytics/monthly-report")
async def get_monthly_report(year: Optional[int] = None, user_id: str = Depends(get_current_user_id)):
    current_year = year or datetime.now().year
    
    # Get all transactions for the year
    start_date = f"{current_year}-01-01"
    end_date = f"{current_year}-12-31"
    
    transactions = await db.transactions.find({
        "user_id": user_id,
        "date": {"$gte": start_date, "$lte": end_date}
    }).to_list(1000)
    
    # Group by month
    monthly_data = defaultdict(lambda: {
        "categories": defaultdict(float),
        "total_spent": 0,
        "transaction_count": 0
    })
    
    for transaction in transactions:
        trans_date = datetime.fromisoformat(transaction["date"]).date()
        month_key = f"{trans_date.year}-{trans_date.month:02d}"
        
        monthly_data[month_key]["categories"][transaction["category"]] += abs(transaction["amount"])
        monthly_data[month_key]["total_spent"] += abs(transaction["amount"])
        monthly_data[month_key]["transaction_count"] += 1
    
    # Convert to list format
    reports = []
    for month_key, data in monthly_data.items():
        year, month = month_key.split("-")
        reports.append({
            "month": month_key,
            "year": int(year),
            "categories": dict(data["categories"]),
            "total_spent": data["total_spent"],
            "transaction_count": data["transaction_count"]
        })
    
    return sorted(reports, key=lambda x: x["month"])

@api_router.get("/analytics/category-breakdown")
async def get_category_breakdown(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user_id: str = Depends(get_current_user_id)
):
    filter_dict = {"user_id": user_id}
    if start_date:
        filter_dict["date"] = {"$gte": start_date}
    if end_date:
        if "date" in filter_dict:
            filter_dict["date"]["$lte"] = end_date
        else:
            filter_dict["date"] = {"$lte": end_date}
    
    transactions = await db.transactions.find(filter_dict).to_list(1000)
    
    category_data = defaultdict(lambda: {"amount": 0, "count": 0})
    total_spending = 0
    
    for transaction in transactions:
        amount = abs(transaction["amount"])
        category_data[transaction["category"]]["amount"] += amount
        category_data[transaction["category"]]["count"] += 1
        total_spending += amount
    
    # Calculate percentages and format response
    result = []
    for category, data in category_data.items():
        percentage = (data["amount"] / total_spending * 100) if total_spending > 0 else 0
        result.append({
            "category": category,
            "amount": data["amount"],
            "count": data["count"],
            "percentage": round(percentage, 2)
        })
    
    return sorted(result, key=lambda x: x["amount"], reverse=True)

# Enhanced bulk import with user support
@api_router.post("/transactions/bulk-import")
async def bulk_import_transactions(file: UploadFile = File(...), user_id: str = Depends(get_current_user_id)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")
    
    try:
        content = await file.read()
        df = pd.read_csv(io.StringIO(content.decode('utf-8')))
        
        # Expected columns: date, description, category, amount
        required_columns = ['date', 'description', 'category', 'amount']
        if not all(col in df.columns for col in required_columns):
            raise HTTPException(
                status_code=400, 
                detail=f"CSV must contain columns: {', '.join(required_columns)}"
            )
        
        transactions = []
        for _, row in df.iterrows():
            # Convert date to string if it's a datetime object
            date_value = row['date']
            if hasattr(date_value, 'isoformat'):
                date_value = date_value.isoformat()
            elif hasattr(date_value, 'strftime'):
                date_value = date_value.strftime('%Y-%m-%d')
            
            transaction_data = {
                "date": str(date_value),
                "description": str(row['description']),
                "category": str(row['category']),
                "amount": float(row['amount']),
                "account_type": str(row.get('account_type', 'credit_card')),
                "user_id": user_id
            }
            transaction_obj = Transaction(**transaction_data)
            transaction_dict = transaction_obj.dict()
            # Ensure dates are strings for MongoDB
            if hasattr(transaction_dict['date'], 'isoformat'):
                transaction_dict['date'] = transaction_dict['date'].isoformat()
            if hasattr(transaction_dict['created_at'], 'isoformat'):
                transaction_dict['created_at'] = transaction_dict['created_at'].isoformat()
            transactions.append(transaction_dict)
        
        # Insert all transactions
        if transactions:
            await db.transactions.insert_many(transactions)
        
        return {"message": f"Successfully imported {len(transactions)} transactions"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@api_router.get("/analytics/spending-trends")
async def get_spending_trends(months: int = 12, user_id: str = Depends(get_current_user_id)):
    # Get transactions from the last N months
    end_date = datetime.now().date()
    start_date = end_date.replace(month=end_date.month - months + 1 if end_date.month > months else 12 - (months - end_date.month - 1), 
                                  year=end_date.year if end_date.month > months else end_date.year - 1)
    
    transactions = await db.transactions.find({
        "user_id": user_id,
        "date": {"$gte": start_date.isoformat(), "$lte": end_date.isoformat()}
    }).to_list(1000)
    
    # Group by month for trend analysis
    monthly_trends = defaultdict(lambda: {"total": 0, "categories": defaultdict(float)})
    
    for transaction in transactions:
        trans_date = datetime.fromisoformat(transaction["date"]).date()
        month_key = f"{trans_date.year}-{trans_date.month:02d}"
        amount = abs(transaction["amount"])
        
        monthly_trends[month_key]["total"] += amount
        monthly_trends[month_key]["categories"][transaction["category"]] += amount
    
    return dict(monthly_trends)

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()