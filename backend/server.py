from fastapi import FastAPI, APIRouter, UploadFile, File, Form, HTTPException, Depends, status, Request, Header, Query
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, OAuth2PasswordBearer, OAuth2PasswordRequestForm
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import Any, Dict, List, Optional
import uuid
from datetime import datetime, date, timedelta
import pandas as pd
import io
import json
import re
from collections import Counter, defaultdict
import pdfplumber
import PyPDF2
import tempfile
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils.dataframe import dataframe_to_rows
from passlib.context import CryptContext
from jose import JWTError, jwt
import secrets
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random
import string
from authlib.integrations.starlette_client import OAuth
import httpx
import anthropic
import asyncio

try:
    import plaid
    from plaid.api import plaid_api
    from plaid.api_client import ApiClient
    from plaid.configuration import Configuration
    from plaid.model.accounts_get_request import AccountsGetRequest
    from plaid.model.country_code import CountryCode
    from plaid.model.institutions_get_by_id_request import InstitutionsGetByIdRequest
    from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
    from plaid.model.link_token_create_request import LinkTokenCreateRequest
    from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
    from plaid.model.products import Products
    from plaid.model.transactions_sync_request import TransactionsSyncRequest
    PLAID_SDK_AVAILABLE = True
except Exception:
    plaid = None
    plaid_api = None
    ApiClient = None
    Configuration = None
    AccountsGetRequest = None
    CountryCode = None
    InstitutionsGetByIdRequest = None
    ItemPublicTokenExchangeRequest = None
    LinkTokenCreateRequest = None
    LinkTokenCreateRequestUser = None
    Products = None
    TransactionsSyncRequest = None
    PLAID_SDK_AVAILABLE = False

try:
    import numpy as np
    import pypdfium2 as pdfium
    from rapidocr_onnxruntime import RapidOCR
    OCR_RUNTIME_AVAILABLE = True
except Exception:
    np = None
    pdfium = None
    RapidOCR = None
    OCR_RUNTIME_AVAILABLE = False



ROOT_DIR = Path(__file__).parent
# Load environment variables - prefer .env.local for development
load_dotenv(ROOT_DIR / '.env.local')  # Load local secrets first
load_dotenv(ROOT_DIR / '.env')        # Load template as fallback

# Security configuration
SECRET_KEY = os.environ.get("SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30 * 24 * 60  # 30 days

# Gmail SMTP Configuration
GMAIL_EMAIL = os.environ.get("GMAIL_EMAIL")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")

# Google OAuth Configuration
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")

# Plaid Configuration
PLAID_CLIENT_ID = os.environ.get("PLAID_CLIENT_ID", "")
PLAID_SECRET = os.environ.get("PLAID_SECRET", "")
PLAID_ENV = os.environ.get("PLAID_ENV", "sandbox").strip().lower()
PLAID_CLIENT_NAME = os.environ.get("PLAID_CLIENT_NAME", "LifeTracker")
PLAID_PRODUCTS = [
    value.strip().lower()
    for value in os.environ.get("PLAID_PRODUCTS", "transactions").split(",")
    if value.strip()
]
PLAID_COUNTRY_CODES = [
    value.strip().upper()
    for value in os.environ.get("PLAID_COUNTRY_CODES", "CA,US").split(",")
    if value.strip()
]
PLAID_REDIRECT_URI = os.environ.get("PLAID_REDIRECT_URI")
PLAID_WEBHOOK_URL = os.environ.get("PLAID_WEBHOOK_URL")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

oauth = OAuth()
google_oauth = oauth.register(
    name='google',
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)
# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

PLAID_ENVIRONMENT_HOSTS = (
    {
        "sandbox": plaid.Environment.Sandbox,
        "development": getattr(plaid.Environment, "Development", plaid.Environment.Sandbox),
        "production": plaid.Environment.Production,
    }
    if PLAID_SDK_AVAILABLE
    else {}
)
plaid_client = None
if PLAID_SDK_AVAILABLE and PLAID_CLIENT_ID and PLAID_SECRET:
    plaid_host = PLAID_ENVIRONMENT_HOSTS.get(PLAID_ENV, plaid.Environment.Sandbox)
    plaid_configuration = Configuration(
        host=plaid_host,
        api_key={
            "clientId": PLAID_CLIENT_ID,
            "secret": PLAID_SECRET,
        },
    )
    plaid_client = plaid_api.PlaidApi(ApiClient(plaid_configuration))

# Create the main app without a prefix
app = FastAPI()

# Add session middleware for OAuth
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

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
    merchant_signature: Optional[str] = None
    is_inflow: Optional[bool] = None
    is_internal_transfer: Optional[bool] = None
    original_amount: Optional[float] = None
    updated_at: Optional[datetime] = None
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
    total_received: float = 0
    net: float = 0
    transaction_count: int

class CategorySpending(BaseModel):
    category: str
    amount: float
    count: int
    percentage: float

# Subscription Models
class Subscription(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    name: str
    amount: float
    currency: str = "CAD"
    billing_cycle: str = "monthly"  # monthly, yearly, weekly
    next_billing_date: Optional[str] = None
    category: str = "Professional and Financial Services"
    status: str = "active"  # active, paused, cancelled
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class SubscriptionCreate(BaseModel):
    name: str
    amount: float
    billing_cycle: str = "monthly"
    next_billing_date: Optional[str] = None
    category: str = "Professional and Financial Services"
    notes: Optional[str] = None

class SubscriptionUpdate(BaseModel):
    name: Optional[str] = None
    amount: Optional[float] = None
    billing_cycle: Optional[str] = None
    next_billing_date: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None

# Authentication Models
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    username: Optional[str] = None

class User(BaseModel):
    id: str
    email: str
    username: str
    full_name: str
    role: str = "user"
    household_id: Optional[str] = None
    created_at: datetime
    last_login: Optional[datetime] = None

class UserLogin(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

# Household Models
class HouseholdCreate(BaseModel):
    name: str

class Household(BaseModel):
    id: str
    name: str
    created_by: str
    members: List[str]
    created_at: datetime

# Password Reset Models
class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    email: EmailStr
    reset_code: str
    new_password: str

# User Profile Models
class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    username: Optional[str] = None

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str

class PlaidPublicTokenExchangeRequestBody(BaseModel):
    public_token: str

class PlaidSyncRequestBody(BaseModel):
    item_id: Optional[str] = None

# Authentication utility functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_user_by_email(email: str):
    user = await db.users.find_one({"email": email})
    if user:
        return user
    return None

async def authenticate_user(email: str, password: str):
    user = await get_user_by_email(email)
    if not user:
        return False
    if not verify_password(password, user["password_hash"]):
        return False
    return user

# Email utility functions
async def send_email(to_email: str, subject: str, body: str):
    """Send email using Gmail SMTP"""
    try:
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = GMAIL_EMAIL
        message["To"] = to_email
        
        # Create the HTML content
        html_part = MIMEText(body, "html")
        message.attach(html_part)
        
        # Send the email
        await aiosmtplib.send(
            message,
            hostname="smtp.gmail.com",
            port=587,
            start_tls=True,
            username=GMAIL_EMAIL,
            password=GMAIL_APP_PASSWORD,
        )
        return True
    except Exception as e:
        logging.error(f"Failed to send email: {e}")
        return False

def generate_reset_code():
    """Generate a 6-digit reset code"""
    return ''.join(random.choices(string.digits, k=6))

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception
    user = await get_user_by_email(email=token_data.email)
    if user is None:
        raise credentials_exception
    return user

async def get_current_user_id(current_user: dict = Depends(get_current_user)):
    return current_user["id"]

# Enhanced function for multi-user support
async def get_view_user_id(
    view_user_id: Optional[str] = Query(None, alias="view_user_id"),
    view_user_id_header: Optional[str] = Header(None, alias="X-View-User-ID"),
    current_user: dict = Depends(get_current_user)
):
    """Get the user ID for data viewing - supports switching between household members"""
    if view_user_id_header:
        view_user_id = view_user_id_header

    if not view_user_id or view_user_id == 'personal':
        return current_user["id"]
    
    if view_user_id == 'family_view':
        # Return special identifier for family view
        return 'family_view'
    
    # Check if the requested user is in the same household
    if current_user.get("household_id"):
        target_user = await db.users.find_one({"id": view_user_id})
        if target_user and target_user.get("household_id") == current_user["household_id"]:
            return view_user_id
    
    # Default to current user if not authorized
    return current_user["id"]

async def resolve_view_user_ids(current_user: dict, view_user_id: str) -> List[str]:
    """Resolve authorized user IDs for analytics/list views."""
    if view_user_id != 'family_view':
        return [view_user_id]

    household_id = current_user.get("household_id")
    if not household_id:
        return [current_user["id"]]

    member_ids = await db.users.distinct("id", {"household_id": household_id})
    return member_ids or [current_user["id"]]

async def build_view_filter(current_user: dict, view_user_id: str) -> dict:
    """Build Mongo user filter for personal/member/family views."""
    view_user_ids = await resolve_view_user_ids(current_user, view_user_id)
    if len(view_user_ids) == 1:
        return {"user_id": view_user_ids[0]}
    return {"user_id": {"$in": view_user_ids}}

def get_ai_scope_id(current_user: dict, view_user_id: str) -> str:
    """Scope AI artifacts by view mode so personal/member/family data stay separated."""
    if view_user_id == "family_view":
        household_id = current_user.get("household_id")
        if household_id:
            return f"household:{household_id}"
        return f"user:{current_user['id']}"
    return f"user:{view_user_id}"

def build_ai_scope_filter(current_user: dict, view_user_id: str) -> dict:
    """
    Match AI items for the active scope.
    Includes legacy records without scope_id for personal/member views.
    """
    scope_id = get_ai_scope_id(current_user, view_user_id)
    conditions = [{"scope_id": scope_id}]

    # Backward compatibility for pre-scope records.
    if view_user_id != "family_view":
        conditions.append({"scope_id": {"$exists": False}, "user_id": view_user_id})

    return {"$or": conditions}

# Migration compatibility function  
async def get_current_user_id_flexible(authorization: Optional[str] = Depends(oauth2_scheme)):
    """Flexible user ID function for migration - supports both auth and legacy"""
    if not authorization:
        return "default_user"  # Legacy support
    
    try:
        current_user = await get_current_user(authorization)
        return current_user["id"]
    except HTTPException:
        return "default_user"  # Fallback for invalid tokens

# PDF Processing Functions
MONTH_ABBREVIATIONS = {"jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"}
AMOUNT_TOKEN_PATTERN = re.compile(r"^\(?-?\$?\d{1,3}(?:,\d{3})*\.\d{2}\)?$")
DATE_TOKEN_PATTERN = re.compile(r"^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}$", re.IGNORECASE)
OCR_AMOUNT_PATTERN = re.compile(r"\$?\d[\dA-Za-z,]*(?:[\. ]\d{2})")
GENERIC_AMOUNT_PATTERN = re.compile(r"\(?-?\$?\d{1,3}(?:,\d{3})*\.\d{2}\)?")

_ocr_engine = None

def get_ocr_engine():
    """Lazily initialize OCR engine for image-only PDFs."""
    global _ocr_engine
    if not OCR_RUNTIME_AVAILABLE:
        return None
    if _ocr_engine is None:
        _ocr_engine = RapidOCR()
    return _ocr_engine

def ocr_extract_text_from_pdf(file_content: bytes, render_scale: float = 2.5) -> str:
    """Run OCR over each PDF page and return plain text suitable for downstream parsing."""
    ocr_engine = get_ocr_engine()
    if ocr_engine is None:
        return ""

    try:
        pdf_doc = pdfium.PdfDocument(io.BytesIO(file_content))
    except Exception as e:
        logging.warning(f"OCR renderer failed to open PDF: {e}")
        return ""

    all_pages_text = []
    for page_index in range(len(pdf_doc)):
        try:
            page = pdf_doc[page_index]
            rendered = page.render(scale=render_scale).to_pil()
            image_array = np.array(rendered)
            ocr_result, _ = ocr_engine(image_array)
        except Exception as e:
            logging.warning(f"OCR failed on page {page_index + 1}: {e}")
            continue

        if not ocr_result:
            continue

        # Group OCR segments by y-position so table columns are merged back into row lines.
        grouped_rows = []
        y_tolerance = 8.0
        for item in ocr_result:
            if len(item) < 2:
                continue
            text_value = str(item[1]).strip()
            if not text_value:
                continue

            box = item[0] if item and item[0] else []
            x0 = min(point[0] for point in box) if box else 0.0
            y0 = min(point[1] for point in box) if box else 0.0

            matched_row = None
            for row in grouped_rows:
                if abs(y0 - row["y"]) <= y_tolerance:
                    matched_row = row
                    break

            if matched_row is None:
                matched_row = {"y": y0, "items": []}
                grouped_rows.append(matched_row)

            matched_row["items"].append((x0, text_value))

        ordered_rows = sorted(grouped_rows, key=lambda row: row["y"])
        row_lines = []
        for row in ordered_rows:
            merged_row = " ".join(text for _, text in sorted(row["items"], key=lambda pair: pair[0])).strip()
            if merged_row:
                row_lines.append(merged_row)
        if row_lines:
            page_text = "\n".join(row_lines)
            all_pages_text.append(f"--- OCR PAGE {page_index + 1} ---\n{page_text}")

    return "\n".join(all_pages_text)

def group_pdf_words_into_rows(words: List[dict], y_tolerance: float = 3.0) -> List[dict]:
    """Group pdfplumber words into visual rows using their y position."""
    if not words:
        return []

    sorted_words = sorted(
        [word for word in words if word.get("text")],
        key=lambda word: (round(word.get("top", 0), 1), word.get("x0", 0))
    )

    grouped_rows = []
    current_row = None

    for word in sorted_words:
        word_top = float(word.get("top", 0))
        if current_row is None or abs(word_top - current_row["top"]) > y_tolerance:
            current_row = {"top": word_top, "words": [word]}
            grouped_rows.append(current_row)
        else:
            current_row["words"].append(word)

    rows = []
    for row in grouped_rows:
        row_words = sorted(row["words"], key=lambda word: word.get("x0", 0))
        row_text = " ".join(str(word.get("text", "")).strip() for word in row_words if str(word.get("text", "")).strip())
        if row_text:
            rows.append({
                "top": row["top"],
                "words": row_words,
                "text": row_text
            })

    return rows

def extract_pdf_document(file_content: bytes) -> dict:
    """Extract text and layout information from a PDF for deterministic parsing."""
    document = {
        "text": "",
        "pages": [],
        "method": None,
        "ocr_needed": False,
        "ocr_used": False,
    }

    try:
        with pdfplumber.open(io.BytesIO(file_content)) as pdf:
            document["method"] = "pdfplumber"
            print(f"PDF has {len(pdf.pages)} pages")

            for page_num, page in enumerate(pdf.pages, start=1):
                print(f"Processing page {page_num}")
                page_text = page.extract_text() or ""
                page_words = page.extract_words(
                    x_tolerance=2,
                    y_tolerance=2,
                    keep_blank_chars=False,
                    use_text_flow=False
                ) or []
                page_rows = group_pdf_words_into_rows(page_words)

                page_text_for_document = page_text or "\n".join(row["text"] for row in page_rows)
                if page_text_for_document:
                    document["text"] += f"\n--- PAGE {page_num} ---\n{page_text_for_document}\n"

                document["pages"].append({
                    "page_number": page_num,
                    "text": page_text_for_document,
                    "rows": page_rows,
                    "word_count": len(page_words),
                    "image_count": len(page.images),
                })

                print(
                    f"Page {page_num}: {len(page_text_for_document)} text chars, "
                    f"{len(page_rows)} grouped rows, {len(page_words)} words, {len(page.images)} images"
                )

    except Exception as e:
        logging.warning(f"pdfplumber extraction failed: {e}")

    if not document["pages"]:
        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
            document["method"] = "pypdf2"
            print(f"PyPDF2: PDF has {len(pdf_reader.pages)} pages")
            for page_num, page in enumerate(pdf_reader.pages, start=1):
                page_text = page.extract_text() or ""
                document["text"] += f"\n--- PYPDF2 PAGE {page_num} ---\n{page_text}\n"
                document["pages"].append({
                    "page_number": page_num,
                    "text": page_text,
                    "rows": [],
                    "word_count": 0,
                    "image_count": 0,
                })
        except Exception as e2:
            logging.error(f"PyPDF2 extraction also failed: {e2}")
            raise HTTPException(status_code=400, detail="Could not extract text from PDF")

    total_word_count = sum(page.get("word_count", 0) for page in document["pages"])
    total_image_count = sum(page.get("image_count", 0) for page in document["pages"])
    document["ocr_needed"] = total_word_count == 0 and total_image_count > 0

    if document["ocr_needed"] and OCR_RUNTIME_AVAILABLE:
        ocr_text = ocr_extract_text_from_pdf(file_content)
        if ocr_text.strip():
            document["text"] = ocr_text
            document["ocr_used"] = True
            document["method"] = "ocr" if not document["method"] else f"{document['method']}+ocr"

    print(f"Total extracted text length: {len(document['text'])}")
    print("EXTRACTED TEXT PREVIEW:")
    print("=" * 80)
    print(document["text"][:2000])
    print("=" * 80)

    return document

def extract_text_from_pdf(file_content: bytes) -> str:
    """Backward-compatible text extraction wrapper."""
    return extract_pdf_document(file_content)["text"]

def generate_source_name(user_name: str, account_type: str, original_filename: str = None) -> str:
    """Generate a user-friendly source name like 'JANE'S DEBIT' or 'JOHN'S CREDIT'"""
    if not user_name or user_name == 'Unknown User':
        # Fallback to filename if no user name found
        if original_filename:
            base_name = original_filename.replace('.pdf', '').replace('_', ' ').title()
            return f"{base_name} ({account_type.title()})"
        return f"Unknown {account_type.title()}"
    
    # Clean up the user name -- skip titles like MR, MRS, MS, DR
    titles = {'mr', 'mrs', 'ms', 'dr', 'miss', 'mx'}
    name_parts = user_name.strip().split()
    # Filter out titles
    real_name_parts = [p for p in name_parts if p.lower() not in titles]
    if not real_name_parts:
        real_name_parts = name_parts  # fallback if all parts are titles

    if len(real_name_parts) >= 1:
        first_name = real_name_parts[0].title()
        return f"{first_name}'s {account_type.title()}"
    else:
        clean_name = user_name.title()
        return f"{clean_name}'s {account_type.title()}"

def extract_pdf_metadata(text: str) -> dict:
    """Extract user name and statement period from PDF header - enhanced for multiple formats"""
    metadata = {
        'user_name': None,
        'statement_start': None,
        'statement_end': None,
        'statement_year': None
    }
    
    lines = text.split('\n')
    
    # Enhanced user name extraction for both debit and credit formats
    for i, line in enumerate(lines[:15]):  # Look at more lines
        line = line.strip()
        
        # Method 1: Look for name patterns (all caps, likely a person's name)
        if re.match(r'^[A-Z\s]{8,50}$', line) and ' ' in line and len(line.split()) >= 2:
            # Skip common bank terms
            bank_terms = ['ACCOUNT', 'STATEMENT', 'CARD', 'BANK', 'DIVIDEND', 'CIBC', 'VISA', 'TRANSACTION', 'DETAILS']
            if not any(term in line.upper() for term in bank_terms):
                metadata['user_name'] = line.strip()
                print(f"Found user name (Method 1): {metadata['user_name']}")
                break
        
        # Method 2: Look for "Prepared for:" pattern (credit cards)
        prepared_match = re.search(r'prepared for:?\s*([A-Z\s]+?)(?:\s+[A-Z]{2,}\s+\d|\s*$)', line, re.IGNORECASE)
        if prepared_match:
            name = prepared_match.group(1).strip()
            if len(name) > 5 and ' ' in name:  # Valid name should have space and be reasonable length
                metadata['user_name'] = name
                print(f"Found user name (Method 2): {metadata['user_name']}")
                break
        
        # Method 3: Look for name right after date pattern (debit format)
        # Example: "JANE AGBAOHWO                                For Jul 1 to Jul 31, 2024"
        date_with_name = re.search(r'^([A-Z\s]+?)\s+For\s+(\w+\s+\d+\s+to\s+\w+\s+\d+,?\s+\d{4})', line, re.IGNORECASE)
        if date_with_name:
            name = date_with_name.group(1).strip()
            if len(name) > 5 and ' ' in name:
                metadata['user_name'] = name
                print(f"Found user name (Method 3): {metadata['user_name']}")
                # Also extract the date from this line
                date_part = date_with_name.group(2)
                period_match = re.search(r'(\w+)\s+(\d+)\s*to\s*(\w+)\s+(\d+),?\s*(\d{4})', date_part, re.IGNORECASE)
                if period_match:
                    start_month, start_day, end_month, end_day, year = period_match.groups()
                    metadata['statement_start'] = f"{start_month} {start_day}"
                    metadata['statement_end'] = f"{end_month} {end_day}"
                    metadata['statement_year'] = int(year)
                break

        # Method 4: ATB OCR layout often has the customer name right below branch heading.
        if 'your atb financial branch' in line.lower() and i + 1 < len(lines):
            candidate_line = re.sub(r'\s+', ' ', lines[i + 1]).strip()
            # OCR often merges name and branch code in one line (for example: "Alex Example 07459 Calgary...").
            name_prefix_match = re.match(r'^([A-Za-z][A-Za-z\s\'\.-]{2,}?)(?:\s+\d{3,}.*)?$', candidate_line)
            candidate_name = name_prefix_match.group(1).strip() if name_prefix_match else candidate_line
            if candidate_name and len(candidate_name.split()) >= 2 and len(candidate_name) >= 4:
                metadata['user_name'] = candidate_name
                print(f"Found user name (Method 4): {metadata['user_name']}")
                break
    
    # Look for statement period if not found above
    if not metadata['statement_year']:
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

def normalize_row_text(value: str) -> str:
    """Lowercase and collapse spaces for row-level parsing."""
    return re.sub(r"\s+", " ", str(value).strip().lower())

def is_amount_text(value: str) -> bool:
    """Check whether a token looks like a monetary amount."""
    candidate = str(value).strip().replace(" ", "")
    return bool(AMOUNT_TOKEN_PATTERN.match(candidate))

def parse_amount_text(value: str) -> Optional[float]:
    """Parse a monetary token like 1,234.56 or (53.54)."""
    candidate = str(value).strip().replace("$", "").replace(",", "").replace(" ", "")
    if not candidate:
        return None

    negative = False
    if candidate.startswith("(") and candidate.endswith(")"):
        negative = True
        candidate = candidate[1:-1]
    if candidate.startswith("-"):
        negative = True
        candidate = candidate[1:]

    if not re.fullmatch(r"\d+\.\d{2}", candidate):
        return None

    amount_value = float(candidate)
    return -amount_value if negative else amount_value

def parse_ocr_amount_text(value: str) -> Optional[float]:
    """Parse OCR amount text that may contain spacing or character-recognition noise."""
    candidate = str(value or "").strip().replace("$", "")
    if not candidate:
        return None

    # Fix common OCR substitutions inside numbers.
    translation_map = str.maketrans({
        "O": "0",
        "o": "0",
        "I": "1",
        "l": "1",
        "S": "5",
        "B": "8",
        "A": "4",
    })
    candidate = candidate.translate(translation_map)
    candidate = candidate.replace(",", "")
    candidate = re.sub(r"(?<=\d)\s+(?=\d{2}$)", ".", candidate)
    candidate = candidate.replace(" ", "")

    negative = False
    if candidate.startswith("(") and candidate.endswith(")"):
        negative = True
        candidate = candidate[1:-1]
    if candidate.startswith("-"):
        negative = True
        candidate = candidate[1:]

    if not re.fullmatch(r"\d+\.\d{2}", candidate):
        return None

    amount_value = float(candidate)
    return -amount_value if negative else amount_value

def extract_ocr_amounts_from_line(line_text: str) -> List[float]:
    """Extract all valid OCR amount values from a line."""
    amounts = []
    for match in OCR_AMOUNT_PATTERN.findall(str(line_text or "")):
        parsed_amount = parse_ocr_amount_text(match)
        if parsed_amount is not None:
            amounts.append(parsed_amount)
    return amounts

def infer_atb_transaction_amount(
    description: str,
    amount_candidates: List[float],
    balance_amount: Optional[float],
    previous_balance: Optional[float],
) -> Optional[float]:
    """Infer signed transaction amount for ATB OCR rows."""
    first_candidate = abs(amount_candidates[0]) if amount_candidates else None

    if previous_balance is not None and balance_amount is not None:
        delta_amount = round(previous_balance - balance_amount, 2)
        if abs(delta_amount) > 0.009:
            if first_candidate is None:
                return delta_amount
            if abs(abs(delta_amount) - first_candidate) <= max(2.0, first_candidate * 0.05):
                return delta_amount

    if first_candidate is None:
        return None

    base_amount = first_candidate
    description_upper = description.upper()

    inflow_keywords = [
        "DIRECT DEPOSIT",
        "PAYROLL",
        "RECEIVED",
        "AUTODEPOSIT",
        "DEPOSIT",
        "CREDIT",
        "REFUND",
    ]
    outflow_keywords = [
        "TRANSFER TO",
        "SENT",
        "BILL PAYMENT",
        "LOAN PAYMENT",
        "PRINCIPAL PAYMENT",
        "DEBIT",
        "ADJ MASTERCARD",
        "PAYMENT",
    ]

    if any(keyword in description_upper for keyword in inflow_keywords):
        return -base_amount
    if any(keyword in description_upper for keyword in outflow_keywords):
        return base_amount

    return base_amount

def parse_atb_transactions_from_text(
    text: str,
    user_id: str,
    source_filename: Optional[str],
    statement_year: int,
    user_name: str,
    statement_start: Optional[str] = None,
    statement_end: Optional[str] = None,
) -> List[dict]:
    """Parse ATB statement rows from OCR text."""
    def clean_atb_description_fragment(fragment: str) -> str:
        cleaned = str(fragment or "")
        # Split common OCR merged tokens that hurt category matching.
        cleaned = re.sub(r"\be[\-\s]*transferreceived\b", "e-transfer received", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\be[\-\s]*transfersent\b", "e-transfer sent", cleaned, flags=re.IGNORECASE)

        # Strip statement/page artifacts from row text.
        cleaned = re.sub(r"details of your account transactions(?:\s*\(continued\))?", " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"keep your credentials private.*", " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"trademarks of alberta treasury branches.*", " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"saving i borrowing i investing i know-how", " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"atb0114003_[A-Za-z0-9_\-]+", " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bpage\s+\d+\s+of\s+\d+\b", " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bfind an error\??.*", " ", cleaned, flags=re.IGNORECASE)

        cleaned = re.sub(r"\s+", " ", cleaned).strip(" -,:;.")
        if cleaned.lower() in {"these", "m"}:
            return ""
        return cleaned

    lines = []
    for raw_line in str(text or "").splitlines():
        clean_line = re.sub(r"\s+", " ", raw_line).strip()
        if clean_line:
            lines.append(clean_line)

    in_transaction_section = False
    current_date_str = None
    current_transaction = None
    previous_balance = None
    transactions = []

    def finalize_current_transaction():
        nonlocal current_transaction, previous_balance
        if not current_transaction:
            return

        description = re.sub(r"\s+", " ", current_transaction.get("description", "")).strip()
        description = clean_atb_description_fragment(description)
        balance_amount = current_transaction.get("balance")
        amount_candidates = current_transaction.get("amount_candidates", [])
        parsed_amount = infer_atb_transaction_amount(
            description,
            amount_candidates,
            balance_amount,
            previous_balance,
        )

        if balance_amount is not None:
            previous_balance = balance_amount

        if not description or parsed_amount is None:
            current_transaction = None
            return

        if any(marker in description.lower() for marker in ["balance forward", "closing balance"]):
            current_transaction = None
            return

        transaction_date = parse_date_string(
            current_transaction["date_str"],
            statement_year,
            statement_start=statement_start,
            statement_end=statement_end,
        )
        if not transaction_date:
            current_transaction = None
            return

        transactions.append({
            "date": transaction_date.isoformat(),
            "description": description,
            "category": clean_category("", description),
            "amount": parsed_amount,
            "account_type": "debit",
            "user_id": user_id,
            "pdf_source": generate_source_name(user_name, "debit", source_filename),
            "user_name": user_name,
        })
        current_transaction = None

    noise_markers = [
        "keep your credentials private",
        "trademarks of alberta treasury branches",
        "saving i borrowing i investing i know-how",
        "atb financial",
        "atb0114003_",
        "--- ocr page",
        "details of your account transactions (continued)",
        "find an error?",
        "these.",
        "these",
    ]
    header_markers = [
        "money out of",
        "money into",
        "your account ($)",
        "date description",
    ]

    for line in lines:
        normalized_line = normalize_row_text(line)

        if not in_transaction_section and "details of your account transactions" in normalized_line:
            in_transaction_section = True
            continue

        if not in_transaction_section:
            continue

        if "find an error" in normalized_line:
            break

        if any(noise_marker in normalized_line for noise_marker in noise_markers):
            continue

        if any(header_marker in normalized_line for header_marker in header_markers):
            continue

        if re.search(r"\bpage\s+\d+\s+of\s+\d+\b", normalized_line):
            continue

        date_match = re.match(r"^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s*(\d{1,2})\b", line, re.IGNORECASE)
        if date_match:
            line_date_str = f"{date_match.group(1)[:3].title()} {int(date_match.group(2))}"
            current_date_str = line_date_str

            # Start a new transaction row only if the row includes amount data.
            amount_values = extract_ocr_amounts_from_line(line)
            if amount_values:
                finalize_current_transaction()
                balance_amount = amount_values[-1] if amount_values else None
                description_fragment = re.sub(
                    r"^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s*\d{1,2}\s*",
                    "",
                    line,
                    flags=re.IGNORECASE,
                )
                description_fragment = re.sub(OCR_AMOUNT_PATTERN, "", description_fragment)
                description_fragment = re.sub(r"\b\d{5,}\b", "", description_fragment)
                description_fragment = clean_atb_description_fragment(description_fragment)

                current_transaction = {
                    "date_str": current_date_str,
                    "description": re.sub(r"\s+", " ", description_fragment).strip(),
                    "amount_candidates": amount_values[:-1] if len(amount_values) > 1 else amount_values,
                    "balance": balance_amount,
                }
                continue

        if current_transaction:
            extra_amounts = extract_ocr_amounts_from_line(line)
            if extra_amounts and current_transaction.get("balance") is None:
                current_transaction["balance"] = extra_amounts[-1]
                current_transaction["amount_candidates"].extend(extra_amounts[:-1] if len(extra_amounts) > 1 else extra_amounts)
            else:
                current_transaction["amount_candidates"].extend(extra_amounts)

            continuation_text = re.sub(OCR_AMOUNT_PATTERN, "", line)
            continuation_text = re.sub(r"\b\d{5,}\b", "", continuation_text)
            continuation_text = clean_atb_description_fragment(continuation_text)

            if not continuation_text:
                continue

            current_transaction["description"] = append_text_value(
                current_transaction.get("description", ""),
                continuation_text,
            )
            continue

        if current_date_str and extract_ocr_amounts_from_line(line):
            # Some OCR rows omit the date token but still belong to the current date.
            amount_values = extract_ocr_amounts_from_line(line)
            balance_amount = amount_values[-1] if amount_values else None
            description_fragment = re.sub(OCR_AMOUNT_PATTERN, "", line)
            description_fragment = re.sub(r"\b\d{5,}\b", "", description_fragment)
            description_fragment = clean_atb_description_fragment(description_fragment)
            current_transaction = {
                "date_str": current_date_str,
                "description": re.sub(r"\s+", " ", description_fragment).strip(),
                "amount_candidates": amount_values[:-1] if len(amount_values) > 1 else amount_values,
                "balance": balance_amount,
            }

    finalize_current_transaction()
    return transactions

def extract_generic_amounts_from_line(line_text: str) -> List[float]:
    """Extract amount values from mixed-quality text (OCR or digital PDFs)."""
    values = []
    source_text = str(line_text or "")

    for token in GENERIC_AMOUNT_PATTERN.findall(source_text):
        parsed = parse_amount_text(token)
        if parsed is not None:
            values.append(parsed)

    # OCR parser catches additional variants (e.g., "1 23.45", "l,200.00").
    for parsed in extract_ocr_amounts_from_line(source_text):
        if not any(abs(existing - parsed) <= 0.009 for existing in values):
            values.append(parsed)

    return values

def infer_generic_transaction_amount(
    description: str,
    amount_candidates: List[float],
    balance_amount: Optional[float],
    previous_balance: Optional[float],
) -> Optional[float]:
    """Infer amount sign for generic statement rows."""
    first_candidate = abs(amount_candidates[0]) if amount_candidates else None

    if previous_balance is not None and balance_amount is not None:
        delta_amount = round(previous_balance - balance_amount, 2)
        if abs(delta_amount) > 0.009:
            if first_candidate is None:
                return delta_amount
            if abs(abs(delta_amount) - first_candidate) <= max(2.0, first_candidate * 0.05):
                return delta_amount

    if first_candidate is None:
        return None

    description_upper = str(description or "").upper()
    inflow_keywords = [
        "DIRECT DEPOSIT",
        "PAYROLL",
        "RECEIVED",
        "AUTODEPOSIT",
        "DEPOSIT",
        "CREDIT",
        "REFUND",
        "TRANSFER FROM",
    ]
    outflow_keywords = [
        "TRANSFER TO",
        "SENT",
        "WITHDRAWAL",
        "BILL PAYMENT",
        "LOAN PAYMENT",
        "PRINCIPAL PAYMENT",
        "DEBIT",
        "PURCHASE",
        "FEE",
        "PAYMENT",
    ]

    if any(keyword in description_upper for keyword in inflow_keywords):
        return -first_candidate
    if any(keyword in description_upper for keyword in outflow_keywords):
        return first_candidate

    return first_candidate

def infer_account_type_from_text(text: str) -> str:
    """Infer account_type for generic statements."""
    text_upper = str(text or "").upper()
    if any(marker in text_upper for marker in ["VISA", "MASTERCARD", "CARD STATEMENT", "CREDIT LIMIT"]):
        return "credit_card"
    return "debit"

def parse_generic_transactions_from_text(
    text: str,
    user_id: str,
    source_filename: Optional[str],
    statement_year: int,
    user_name: str,
    statement_start: Optional[str] = None,
    statement_end: Optional[str] = None,
) -> List[dict]:
    """Bank-agnostic parser fallback for transaction rows in text/OCR output."""
    lines = []
    for raw_line in str(text or "").splitlines():
        clean_line = re.sub(r"\s+", " ", raw_line).strip()
        if clean_line:
            lines.append(clean_line)

    account_type = infer_account_type_from_text(text)
    current_date_str = None
    current_transaction = None
    previous_balance = None
    transactions = []

    def clean_fragment(fragment: str) -> str:
        cleaned = str(fragment or "")
        cleaned = re.sub(r"details of your account transactions(?:\s*\(continued\))?", " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"transaction details(?:\s*\(continued\))?", " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"keep your credentials private.*", " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"trademarks of alberta treasury branches.*", " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"saving i borrowing i investing i know-how", " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"atb0114003_[A-Za-z0-9_\-]+", " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bpage\s+\d+\s+of\s+\d+\b", " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bfind an error\??.*", " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\(continued on next page\)", " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bdate\b", " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bdescription\b", " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bwith?drawals?\b", " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bdeposits?\b", " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bbalance\b", " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bitems?\b", " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\baccount\b", " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\$+", " ", cleaned)
        cleaned = re.sub(r"\b\d{6,}\b", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" -,:;.")
        if cleaned.lower() in {"", "these", "m", "continued"}:
            return ""
        return cleaned

    def finalize_current():
        nonlocal current_transaction, previous_balance
        if not current_transaction:
            return

        description = clean_fragment(current_transaction.get("description", ""))
        amount_candidates = current_transaction.get("amount_candidates", [])
        balance_amount = current_transaction.get("balance")
        parsed_amount = infer_generic_transaction_amount(
            description=description,
            amount_candidates=amount_candidates,
            balance_amount=balance_amount,
            previous_balance=previous_balance,
        )

        if balance_amount is not None:
            previous_balance = balance_amount

        if not description or parsed_amount is None:
            current_transaction = None
            return

        if any(marker in description.lower() for marker in ["balance forward", "opening balance", "closing balance"]):
            current_transaction = None
            return

        transaction_date = parse_date_string(
            current_transaction["date_str"],
            statement_year,
            statement_start=statement_start,
            statement_end=statement_end,
        )
        if not transaction_date:
            current_transaction = None
            return

        source_type = "credit" if account_type == "credit_card" else "debit"
        transactions.append({
            "date": transaction_date.isoformat(),
            "description": description,
            "category": clean_category("", description),
            "amount": parsed_amount,
            "account_type": account_type,
            "user_id": user_id,
            "pdf_source": generate_source_name(user_name, source_type, source_filename),
            "user_name": user_name,
        })
        current_transaction = None

    for line in lines:
        normalized_line = normalize_row_text(line)

        if len(normalized_line) < 4:
            continue

        if any(marker in normalized_line for marker in [
            "account summary",
            "opening balance on",
            "closing balance on",
            "transaction details",
            "details of your account transactions",
            "money out of",
            "money into",
            "your account ($)",
            "spend categories",
            "trans post",
            "date date",
            "cibc account statement",
            "deposit account statement",
        ]):
            continue

        if "find an error" in normalized_line:
            finalize_current()
            break

        date_match = re.match(r"^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s*(\d{1,2})\b", line, re.IGNORECASE)
        if date_match:
            line_date_str = f"{date_match.group(1)[:3].title()} {int(date_match.group(2))}"
            current_date_str = line_date_str

            amount_values = extract_generic_amounts_from_line(line)
            if amount_values:
                finalize_current()
                balance_amount = amount_values[-1] if len(amount_values) > 1 else None
                description_fragment = re.sub(
                    r"^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s*\d{1,2}\s*",
                    "",
                    line,
                    flags=re.IGNORECASE,
                )
                description_fragment = re.sub(GENERIC_AMOUNT_PATTERN, " ", description_fragment)
                description_fragment = re.sub(OCR_AMOUNT_PATTERN, " ", description_fragment)
                description_fragment = clean_fragment(description_fragment)

                current_transaction = {
                    "date_str": current_date_str,
                    "description": description_fragment,
                    "amount_candidates": amount_values[:-1] if len(amount_values) > 1 else amount_values,
                    "balance": balance_amount,
                }
                continue

        if current_transaction:
            extra_amounts = extract_generic_amounts_from_line(line)
            if extra_amounts and current_transaction.get("balance") is None and len(extra_amounts) > 1:
                current_transaction["balance"] = extra_amounts[-1]
                current_transaction["amount_candidates"].extend(extra_amounts[:-1])
            else:
                current_transaction["amount_candidates"].extend(extra_amounts)

            continuation_text = re.sub(GENERIC_AMOUNT_PATTERN, " ", line)
            continuation_text = re.sub(OCR_AMOUNT_PATTERN, " ", continuation_text)
            continuation_text = clean_fragment(continuation_text)
            if continuation_text:
                current_transaction["description"] = append_text_value(
                    current_transaction.get("description", ""),
                    continuation_text,
                )
            continue

        if current_date_str:
            amount_values = extract_generic_amounts_from_line(line)
            if amount_values:
                balance_amount = amount_values[-1] if len(amount_values) > 1 else None
                description_fragment = re.sub(GENERIC_AMOUNT_PATTERN, " ", line)
                description_fragment = re.sub(OCR_AMOUNT_PATTERN, " ", description_fragment)
                description_fragment = clean_fragment(description_fragment)
                current_transaction = {
                    "date_str": current_date_str,
                    "description": description_fragment,
                    "amount_candidates": amount_values[:-1] if len(amount_values) > 1 else amount_values,
                    "balance": balance_amount,
                }

    finalize_current()
    return transactions

def extract_compact_date(words: List[dict], start_index: int = 0) -> tuple[Optional[str], int]:
    """Extract a month-day token from one or two adjacent words."""
    if start_index >= len(words):
        return None, start_index

    first_word = str(words[start_index].get("text", "")).strip()
    if not first_word:
        return None, start_index

    if DATE_TOKEN_PATTERN.match(first_word):
        month_text, day_text = first_word.split()
        return f"{month_text[:3].title()} {int(day_text)}", start_index + 1

    if first_word[:3].lower() in MONTH_ABBREVIATIONS and start_index + 1 < len(words):
        day_token = re.sub(r"[^\d]", "", str(words[start_index + 1].get("text", "")))
        if day_token:
            return f"{first_word[:3].title()} {int(day_token)}", start_index + 2

    return None, start_index

def extract_two_leading_dates(words: List[dict]) -> tuple[Optional[str], Optional[str], int]:
    """Extract transaction and post dates from the beginning of a credit-card row."""
    trans_date_str, next_index = extract_compact_date(words, 0)
    if not trans_date_str:
        return None, None, 0

    post_date_str, final_index = extract_compact_date(words, next_index)
    if not post_date_str:
        return None, None, 0

    return trans_date_str, post_date_str, final_index

def append_text_value(existing_text: str, extra_text: str) -> str:
    """Append text fragments without duplicating empty or repeated data."""
    clean_existing = re.sub(r"\s+", " ", str(existing_text or "")).strip()
    clean_extra = re.sub(r"\s+", " ", str(extra_text or "")).strip()

    if not clean_extra:
        return clean_existing
    if not clean_existing:
        return clean_extra
    if clean_extra in clean_existing:
        return clean_existing

    return f"{clean_existing} {clean_extra}".strip()

def build_header_positions(row_words: List[dict], header_map: Dict[str, set]) -> Dict[str, float]:
    """Find x positions for header labels within a row."""
    positions = {}
    for header_name, header_tokens in header_map.items():
        matches = [
            float(word.get("x0", 0))
            for word in row_words
            if normalize_row_text(word.get("text", "")) in header_tokens
        ]
        if matches:
            positions[header_name] = min(matches)
    return positions

def get_words_in_x_range(
    words: List[dict],
    min_x0: Optional[float] = None,
    max_x0: Optional[float] = None,
    start_index: int = 0,
    end_index: Optional[int] = None,
    margin: float = 6.0,
) -> str:
    """Extract row text from a horizontal column range."""
    final_end_index = len(words) if end_index is None else end_index
    selected_tokens = []

    for index in range(start_index, final_end_index):
        word = words[index]
        x0 = float(word.get("x0", 0))
        if min_x0 is not None and x0 < (min_x0 - margin):
            continue
        if max_x0 is not None and x0 >= (max_x0 - margin):
            continue
        word_text = str(word.get("text", "")).strip()
        if word_text:
            selected_tokens.append(word_text)

    return " ".join(selected_tokens).strip()

def select_rightmost_amount_candidate(words: List[dict], min_x0: Optional[float] = None) -> tuple[Optional[int], Optional[float]]:
    """Find the rightmost amount token in a row, optionally preferring a minimum x position."""
    amount_candidates = [
        (index, word)
        for index, word in enumerate(words)
        if is_amount_text(word.get("text", ""))
        and (min_x0 is None or float(word.get("x0", 0)) >= (min_x0 - 30))
    ]

    if not amount_candidates:
        amount_candidates = [
            (index, word)
            for index, word in enumerate(words)
            if is_amount_text(word.get("text", ""))
        ]

    if not amount_candidates:
        return None, None

    amount_index, amount_word = max(amount_candidates, key=lambda item: float(item[1].get("x0", 0)))
    return amount_index, parse_amount_text(amount_word.get("text", ""))

def detect_credit_layout_columns(rows: List[dict]) -> Dict[str, float]:
    """Detect the credit-card statement column layout from header rows."""
    default_columns = {
        "header_index": -1,
        "description_x0": 120.0,
        "category_x0": 350.0,
        "amount_x0": 500.0,
    }

    for row_index, row in enumerate(rows[:40]):
        row_text = normalize_row_text(row.get("text", ""))
        if "description" in row_text and "amount" in row_text and ("spend categories" in row_text or ("spend" in row_text and "categories" in row_text)):
            detected_positions = build_header_positions(
                row.get("words", []),
                {
                    "description_x0": {"description"},
                    "category_x0": {"spend", "categories"},
                    "amount_x0": {"amount", "amount($)"},
                }
            )
            detected_positions["header_index"] = row_index
            return {**default_columns, **detected_positions}

    return default_columns

def detect_debit_layout_columns(rows: List[dict]) -> Dict[str, float]:
    """Detect the debit statement column layout from header rows."""
    default_columns = {
        "header_index": -1,
        "description_x0": 120.0,
        "withdrawal_x0": 360.0,
        "deposit_x0": 450.0,
        "balance_x0": 540.0,
    }

    for row_index, row in enumerate(rows[:40]):
        row_text = normalize_row_text(row.get("text", ""))
        if "description" in row_text and "withdrawals" in row_text and "deposits" in row_text and "balance" in row_text:
            detected_positions = build_header_positions(
                row.get("words", []),
                {
                    "description_x0": {"description"},
                    "withdrawal_x0": {"withdrawals"},
                    "deposit_x0": {"deposits"},
                    "balance_x0": {"balance"},
                }
            )
            detected_positions["header_index"] = row_index
            return {**default_columns, **detected_positions}

    return default_columns

def finalize_credit_layout_transaction(
    transaction_data: Optional[dict],
    transactions: List[dict],
    user_id: str,
    statement_year: int,
    user_name: str,
    source_filename: Optional[str],
    statement_start: Optional[str] = None,
    statement_end: Optional[str] = None,
):
    """Turn a partially parsed credit-card row into a stored transaction."""
    if not transaction_data:
        return

    description = re.sub(r"\s+", " ", str(transaction_data.get("description", "")).strip())
    category_hint = re.sub(r"\s+", " ", str(transaction_data.get("category_hint", "")).strip())
    amount = transaction_data.get("amount")

    if not description or amount is None:
        return

    if any(payment_keyword in description.upper() for payment_keyword in [
        "PAYMENT THANK YOU",
        "PAIEMENT MERCI",
        "PAYMENT - THANK YOU",
        "THANK YOU FOR YOUR PAYMENT",
        "PAYMENT RECEIVED",
    ]):
        return

    if abs(amount) < 0.01 or abs(amount) > 50000:
        return

    transaction_date = parse_date_string(
        transaction_data["trans_date_str"],
        statement_year,
        statement_start=statement_start,
        statement_end=statement_end,
    )
    if not transaction_date:
        return

    transactions.append({
        "date": transaction_date.isoformat(),
        "description": description,
        "category": clean_category(category_hint, description),
        "amount": amount,
        "account_type": "credit_card",
        "user_id": user_id,
        "pdf_source": generate_source_name(user_name, "credit", source_filename),
        "user_name": user_name,
    })

def finalize_debit_layout_transaction(
    transaction_data: Optional[dict],
    transactions: List[dict],
    user_id: str,
    statement_year: int,
    user_name: str,
    source_filename: Optional[str],
    statement_start: Optional[str] = None,
    statement_end: Optional[str] = None,
):
    """Turn a partially parsed debit row into a stored transaction."""
    if not transaction_data:
        return

    description = re.sub(r"\s+", " ", str(transaction_data.get("description", "")).strip())
    amount = transaction_data.get("amount")

    if not description or amount is None:
        return

    if any(skip_keyword in description.lower() for skip_keyword in ["balance forward", "opening balance"]):
        return

    if abs(amount) < 0.01 or abs(amount) > 50000:
        return

    transaction_date = parse_date_string(
        transaction_data["trans_date_str"],
        statement_year,
        statement_start=statement_start,
        statement_end=statement_end,
    )
    if not transaction_date:
        return

    transactions.append({
        "date": transaction_date.isoformat(),
        "description": description,
        "category": clean_category("", description),
        "amount": amount,
        "account_type": "debit",
        "user_id": user_id,
        "pdf_source": generate_source_name(user_name, "debit", source_filename),
        "user_name": user_name,
    })

def parse_cibc_credit_transactions_from_layout(
    pages: List[dict],
    user_id: str,
    source_filename: Optional[str],
    statement_year: int,
    user_name: str,
    statement_start: Optional[str] = None,
    statement_end: Optional[str] = None,
) -> List[dict]:
    """Parse CIBC credit-card statements using PDF layout rows instead of raw text lines."""
    transactions = []

    for page in pages:
        rows = page.get("rows", [])
        if not rows:
            continue

        columns = detect_credit_layout_columns(rows)
        current_transaction = None

        for row_index, row in enumerate(rows):
            row_text = str(row.get("text", "")).strip()
            if not row_text:
                continue

            row_text_normalized = normalize_row_text(row_text)
            if row_index <= columns["header_index"]:
                continue

            if any(header_marker in row_text_normalized for header_marker in [
                "your new charges",
                "trans post",
                "date date",
                "card number",
            ]):
                continue

            trans_date_str, post_date_str, content_start_index = extract_two_leading_dates(row.get("words", []))
            if trans_date_str and post_date_str:
                finalize_credit_layout_transaction(
                    current_transaction,
                    transactions,
                    user_id,
                    statement_year,
                    user_name,
                    source_filename,
                    statement_start,
                    statement_end,
                )

                amount_index, amount_value = select_rightmost_amount_candidate(row.get("words", []), columns.get("amount_x0"))
                if amount_index is None or amount_value is None:
                    current_transaction = None
                    continue

                description_text = get_words_in_x_range(
                    row.get("words", []),
                    min_x0=columns.get("description_x0"),
                    max_x0=columns.get("category_x0"),
                    start_index=content_start_index,
                    end_index=amount_index,
                )
                if not description_text:
                    description_text = get_words_in_x_range(
                        row.get("words", []),
                        min_x0=None,
                        max_x0=columns.get("amount_x0"),
                        start_index=content_start_index,
                        end_index=amount_index,
                    )

                category_hint = get_words_in_x_range(
                    row.get("words", []),
                    min_x0=columns.get("category_x0"),
                    max_x0=columns.get("amount_x0"),
                    start_index=content_start_index,
                    end_index=amount_index,
                )

                current_transaction = {
                    "trans_date_str": trans_date_str,
                    "post_date_str": post_date_str,
                    "description": description_text,
                    "category_hint": category_hint,
                    "amount": amount_value,
                }
                continue

            if not current_transaction:
                continue

            if any(stop_marker in row_text_normalized for stop_marker in [
                "account summary",
                "minimum payment",
                "credit limit",
                "prepared for",
            ]):
                finalize_credit_layout_transaction(
                    current_transaction,
                    transactions,
                    user_id,
                    statement_year,
                    user_name,
                    source_filename,
                    statement_start,
                    statement_end,
                )
                current_transaction = None
                continue

            continuation_description = get_words_in_x_range(
                row.get("words", []),
                min_x0=columns.get("description_x0"),
                max_x0=columns.get("category_x0"),
            )
            if not continuation_description:
                continuation_description = get_words_in_x_range(
                    row.get("words", []),
                    min_x0=None,
                    max_x0=columns.get("category_x0"),
                )

            continuation_category = get_words_in_x_range(
                row.get("words", []),
                min_x0=columns.get("category_x0"),
                max_x0=columns.get("amount_x0"),
            )

            current_transaction["description"] = append_text_value(
                current_transaction.get("description", ""),
                continuation_description,
            )
            current_transaction["category_hint"] = append_text_value(
                current_transaction.get("category_hint", ""),
                continuation_category,
            )

        finalize_credit_layout_transaction(
            current_transaction,
            transactions,
            user_id,
            statement_year,
            user_name,
            source_filename,
            statement_start,
            statement_end,
        )

    return transactions

def assign_debit_amounts(words: List[dict], columns: Dict[str, float]) -> Dict[str, float]:
    """Assign debit-row amounts to withdrawal, deposit, or balance columns by x position."""
    column_positions = {
        "withdrawal": columns.get("withdrawal_x0", 360.0),
        "deposit": columns.get("deposit_x0", 450.0),
        "balance": columns.get("balance_x0", 540.0),
    }
    assigned_amounts = {}

    for word in words:
        amount_value = parse_amount_text(word.get("text", ""))
        if amount_value is None:
            continue

        word_x0 = float(word.get("x0", 0))
        nearest_column_name, nearest_column_x0 = min(
            column_positions.items(),
            key=lambda column_item: abs(word_x0 - column_item[1])
        )

        if abs(word_x0 - nearest_column_x0) <= 80:
            assigned_amounts[nearest_column_name] = abs(amount_value)

    return assigned_amounts

def parse_cibc_debit_transactions_from_layout(
    pages: List[dict],
    user_id: str,
    source_filename: Optional[str],
    statement_year: int,
    user_name: str,
    statement_start: Optional[str] = None,
    statement_end: Optional[str] = None,
) -> List[dict]:
    """Parse CIBC debit statements using word positions and row continuations."""
    transactions = []

    for page in pages:
        rows = page.get("rows", [])
        if not rows:
            continue

        columns = detect_debit_layout_columns(rows)
        description_limit_x0 = min(
            columns.get("withdrawal_x0", 360.0),
            columns.get("deposit_x0", 450.0),
            columns.get("balance_x0", 540.0),
        )
        in_transaction_section = columns["header_index"] != -1
        current_transaction = None
        current_date_str = None

        for row_index, row in enumerate(rows):
            row_text = str(row.get("text", "")).strip()
            if not row_text:
                continue

            row_text_normalized = normalize_row_text(row_text)

            if (
                "continued on next page" in row_text_normalized
                or re.search(r"\bpage\s+\d+\s+of\s+\d+\b", row_text_normalized)
                or re.match(r"^\d+[a-z]+\s+per-\d{4}/\d{2}", row_text_normalized)
            ):
                continue

            if "transaction details" in row_text_normalized:
                in_transaction_section = True
                continue

            if not in_transaction_section:
                continue

            if any(stop_marker in row_text_normalized for stop_marker in [
                "closing balance",
                "important:",
                "free transaction",
                "daily closing balance",
            ]):
                finalize_debit_layout_transaction(
                    current_transaction,
                    transactions,
                    user_id,
                    statement_year,
                    user_name,
                    source_filename,
                    statement_start,
                    statement_end,
                )
                current_transaction = None
                in_transaction_section = False
                continue

            if row_index <= columns["header_index"]:
                continue

            if "description" in row_text_normalized and "withdrawals" in row_text_normalized:
                continue

            trans_date_str, content_start_index = extract_compact_date(row.get("words", []), 0)
            if trans_date_str:
                current_date_str = trans_date_str

            amount_columns = assign_debit_amounts(row.get("words", []), columns)
            has_transaction_amount = "withdrawal" in amount_columns or "deposit" in amount_columns

            if current_date_str and has_transaction_amount:
                finalize_debit_layout_transaction(
                    current_transaction,
                    transactions,
                    user_id,
                    statement_year,
                    user_name,
                    source_filename,
                    statement_start,
                    statement_end,
                )

                transaction_amount = None
                if "withdrawal" in amount_columns:
                    transaction_amount = abs(amount_columns["withdrawal"])
                elif "deposit" in amount_columns:
                    transaction_amount = -abs(amount_columns["deposit"])

                description_text = get_words_in_x_range(
                    row.get("words", []),
                    min_x0=columns.get("description_x0"),
                    max_x0=description_limit_x0,
                    start_index=content_start_index if trans_date_str else 0,
                )
                if not description_text:
                    description_text = get_words_in_x_range(
                        row.get("words", []),
                        min_x0=None,
                        max_x0=description_limit_x0,
                        start_index=content_start_index if trans_date_str else 0,
                    )

                current_transaction = {
                    "trans_date_str": current_date_str,
                    "description": description_text,
                    "amount": transaction_amount,
                }
                continue

            if not current_transaction:
                continue

            continuation_description = get_words_in_x_range(
                row.get("words", []),
                min_x0=columns.get("description_x0"),
                max_x0=description_limit_x0,
            )
            if not continuation_description:
                continuation_description = get_words_in_x_range(
                    row.get("words", []),
                    min_x0=None,
                    max_x0=description_limit_x0,
                )

            current_transaction["description"] = append_text_value(
                current_transaction.get("description", ""),
                continuation_description,
            )

        finalize_debit_layout_transaction(
            current_transaction,
            transactions,
            user_id,
            statement_year,
            user_name,
            source_filename,
            statement_start,
            statement_end,
        )

    return transactions

def parse_transactions_from_pdf_document(document: dict, user_id: str, source_filename: str = None) -> List[dict]:
    """Parse transactions from structured PDF extraction, with text parsing as fallback."""
    text = document.get("text", "")
    metadata = extract_pdf_metadata(text)
    statement_year = metadata.get("statement_year", datetime.now().year)
    statement_start = metadata.get("statement_start")
    statement_end = metadata.get("statement_end")
    user_name = metadata.get("user_name", "Unknown User")

    print(f"Extracted metadata: User: {user_name}, Year: {statement_year}")

    format_type = detect_statement_format(text)
    print(f"Detected format: {format_type}")

    if format_type == "atb_deposit":
        atb_transactions = parse_atb_transactions_from_text(
            text,
            user_id,
            source_filename,
            statement_year,
            user_name,
            statement_start=statement_start,
            statement_end=statement_end,
        )
        if atb_transactions:
            print(f"\n=== ATB OCR PARSING COMPLETE: {len(atb_transactions)} transactions found ===")
            return remove_duplicates(atb_transactions)

    if format_type == "generic":
        generic_transactions = parse_generic_transactions_from_text(
            text,
            user_id,
            source_filename,
            statement_year,
            user_name,
            statement_start=statement_start,
            statement_end=statement_end,
        )
        if generic_transactions:
            print(f"\n=== GENERIC PARSING COMPLETE: {len(generic_transactions)} transactions found ===")
            return remove_duplicates(generic_transactions)

    layout_transactions = []
    if document.get("pages"):
        if format_type == "debit":
            layout_transactions = parse_cibc_debit_transactions_from_layout(
                document["pages"],
                user_id,
                source_filename,
                statement_year,
                user_name,
                statement_start=statement_start,
                statement_end=statement_end,
            )
        elif format_type == "credit":
            layout_transactions = parse_cibc_credit_transactions_from_layout(
                document["pages"],
                user_id,
                source_filename,
                statement_year,
                user_name,
                statement_start=statement_start,
                statement_end=statement_end,
            )

    if layout_transactions:
        print(f"\n=== LAYOUT PARSING COMPLETE: {len(layout_transactions)} transactions found ===")
        # Layout parsing is row-based and can legitimately contain same-day identical transactions
        # (for example duplicate network fees), so keep all parsed rows.
        return layout_transactions

    print("Layout parser found no transactions. Trying generic parser fallback.")
    generic_transactions = parse_generic_transactions_from_text(
        text,
        user_id,
        source_filename,
        statement_year,
        user_name,
        statement_start=statement_start,
        statement_end=statement_end,
    )
    if generic_transactions:
        print(f"\n=== GENERIC FALLBACK COMPLETE: {len(generic_transactions)} transactions found ===")
        return remove_duplicates(generic_transactions)

    print("Generic parser found no transactions. Falling back to text parsing.")
    return parse_transactions_from_text(text, user_id, source_filename)

def detect_statement_format(text: str) -> str:
    """Detect the type of CIBC statement format"""
    text_upper = text.upper()

    # ATB image/OCR statements
    atb_indicators = [
        "ATB FINANCIAL",
        "DEPOSIT ACCOUNT STATEMENT",
        "DETAILS OF YOUR ACCOUNT TRANSACTIONS",
    ]
    if sum(1 for indicator in atb_indicators if indicator in text_upper) >= 2:
        print("Format detection - ATB deposit statement detected")
        return "atb_deposit"
    
    # Check for debit account indicators
    debit_indicators = [
        'TRANSACTION DETAILS',
        'WITHDRAWALS ($)',
        'DEPOSITS ($)',
        'BALANCE ($)',
        'VISA DEBIT RETAIL PURCHASE',
        'ACCOUNT SUMMARY'
    ]
    
    # Check for credit card indicators  
    credit_indicators = [
        'YOUR NEW CHARGES',
        'SPEND CATEGORIES',
        'CARD NUMBER',
        'DIVIDEND',
        'VISA CARD'
    ]
    
    debit_score = sum(1 for indicator in debit_indicators if indicator in text_upper)
    credit_score = sum(1 for indicator in credit_indicators if indicator in text_upper)
    
    print(f"Format detection - Debit score: {debit_score}, Credit score: {credit_score}")
    
    if debit_score == 0 and credit_score == 0:
        return 'generic'
    if debit_score > credit_score:
        return 'debit'
    else:
        return 'credit'

def parse_cibc_debit_transactions(
    text: str,
    user_id: str,
    source_filename: str,
    statement_year: int,
    user_name: str,
    statement_start: Optional[str] = None,
    statement_end: Optional[str] = None,
) -> List[dict]:
    """Parse CIBC debit account transactions with table format"""
    transactions = []
    
    print("Parsing CIBC debit format...")
    
    lines = text.split('\n')
    in_transaction_section = False
    
    for line_num, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
            
        # Look for transaction details section
        if 'transaction details' in line.lower():
            in_transaction_section = True
            print(f"Found transaction details section at line {line_num}")
            continue
            
        # Skip header lines
        if any(header in line.upper() for header in ['DATE', 'DESCRIPTION', 'WITHDRAWALS', 'DEPOSITS', 'BALANCE']):
            continue
            
        # Stop at end indicators
        if any(end_marker in line.lower() for end_marker in ['closing balance', 'important:', 'free transaction']):
            break
            
        if in_transaction_section and line:
            # Try to parse debit transaction line
            # Format: Date | Description | Withdrawals | Deposits | Balance
            
            # Look for date pattern at start of line
            date_match = re.match(r'^(\w{3}\s+\d{1,2})', line)
            if not date_match:
                continue
                
            date_str = date_match.group(1)
            remaining_line = line[len(date_str):].strip()
            
            # Look for amounts (withdrawals, deposits, balance)
            # Balance is usually at the end
            balance_match = re.search(r'(\d+\.\d{2})\s*$', remaining_line)
            if not balance_match:
                continue
                
            balance_amount = balance_match.group(1)
            line_without_balance = remaining_line[:balance_match.start()].strip()
            
            # Look for withdrawal or deposit amount before balance
            amount_pattern = r'(\d+\.\d{2})\s+(\d+\.\d{2})?'
            amounts = re.findall(r'(\d+\.\d{2})', line_without_balance)
            
            if not amounts:
                continue
                
            # The transaction amount is typically the first amount found
            # Enhanced to handle negative amounts and credits
            amount_str = amounts[0].strip()
            
            # Check for negative sign (indicates credit/deposit)
            is_credit = False
            if amount_str.startswith('-') or amount_str.startswith('('):
                is_credit = True
                amount_str = amount_str.replace('-', '').replace('(', '').replace(')', '').strip()
            
            transaction_amount = float(amount_str)
            
            # For debit accounts: negative usually means deposit/credit, positive means withdrawal/debit
            if is_credit:
                transaction_amount = -transaction_amount
                print(f"💳 DEBIT CREDIT/DEPOSIT detected: ${abs(transaction_amount)} (stored as negative)")
            else:
                print(f"💰 DEBIT WITHDRAWAL detected: ${transaction_amount} (stored as positive)")
            
            # Extract description (everything between date and amounts)
            desc_end_pos = line_without_balance.rfind(amounts[0])
            if desc_end_pos == -1:
                continue
                
            description = line_without_balance[:desc_end_pos].strip()
            
            # Clean up description
            description = re.sub(r'\s+', ' ', description)
            
            # Skip if description is too short or looks like header
            if len(description) < 5:
                continue
                
            # Skip certain transaction types
            skip_keywords = ['balance forward', 'opening balance']
            if any(keyword in description.lower() for keyword in skip_keywords):
                continue
                
            # Parse date
            transaction_date = parse_date_string(
                date_str,
                statement_year,
                statement_start=statement_start,
                statement_end=statement_end,
            )
            if not transaction_date:
                continue
                
            # Categorize transaction
            category = clean_category("", description)
            
            # Create enhanced source name
            enhanced_source = generate_source_name(user_name, 'debit', source_filename)
            
            # Create transaction
            transaction = {
                'date': transaction_date.isoformat(),
                'description': description,
                'category': category,
                'amount': transaction_amount,
                'account_type': 'debit',
                'user_id': user_id,
                'pdf_source': enhanced_source,
                'user_name': user_name
            }
            
            transactions.append(transaction)
            print(f"✅ DEBIT ADDED: {description} -> ${transaction_amount} on {transaction_date} ({category})")
    
    return transactions

def parse_transactions_from_text(text: str, user_id: str, source_filename: str = None) -> List[dict]:
    """Parse transactions from extracted PDF text - enhanced for multiple CIBC formats"""
    transactions = []
    
    # Extract metadata first
    metadata = extract_pdf_metadata(text)
    statement_year = metadata.get('statement_year', datetime.now().year)
    statement_start = metadata.get('statement_start')
    statement_end = metadata.get('statement_end')
    user_name = metadata.get('user_name', 'Unknown User')
    
    print(f"Extracted metadata: User: {user_name}, Year: {statement_year}")
    
    # Detect statement format
    format_type = detect_statement_format(text)
    print(f"Detected format: {format_type}")
    
    if format_type == 'atb_deposit':
        transactions = parse_atb_transactions_from_text(
            text,
            user_id,
            source_filename,
            statement_year,
            user_name,
            statement_start=statement_start,
            statement_end=statement_end,
        )
        print(f"\n=== ATB TEXT PARSING COMPLETE: {len(transactions)} transactions found ===")
        return remove_duplicates(transactions)

    if format_type == 'debit':
        # Use debit parsing logic
        transactions = parse_cibc_debit_transactions(
            text,
            user_id,
            source_filename,
            statement_year,
            user_name,
            statement_start=statement_start,
            statement_end=statement_end,
        )
        print(f"\n=== DEBIT PARSING COMPLETE: {len(transactions)} transactions found ===")
        return remove_duplicates(transactions)

    if format_type == 'generic':
        transactions = parse_generic_transactions_from_text(
            text,
            user_id,
            source_filename,
            statement_year,
            user_name,
            statement_start=statement_start,
            statement_end=statement_end,
        )
        print(f"\n=== GENERIC TEXT PARSING COMPLETE: {len(transactions)} transactions found ===")
        return remove_duplicates(transactions)
    
    # Original credit card parsing logic
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
                
            # Debug: Print every non-empty line to catch missing transactions
            print(f"LINE {line_num}: {line}")
                
            # Skip header lines and section headers - be more specific
            skip_line = False
            line_upper = line.upper()
            
            # Only skip if the line is clearly a header (contains multiple header keywords or exact matches)
            # Use word boundaries to avoid false positives (e.g., "LOVISA" containing "VISA")
            header_keywords = [r'\bCARD NUMBER\b', r'\bPAGE\b', r'\bCIBC\b', r'\bDIVIDEND\b', r'\bVISA\b', r'\bYOUR PAYMENTS\b', r'\bYOUR NEW CHARGES\b']
            table_headers = ['TRANS   POST', 'DATE    DATE', 'SPEND CATEGORIES', 'AMOUNT($)']
            
            # Skip if it's clearly a header line
            skip_reason = None
            if any(re.search(header, line_upper) for header in header_keywords):
                skip_line = True
                matching_headers = [h for h in header_keywords if re.search(h, line_upper)]
                skip_reason = f"Contains header keyword: {matching_headers}"
            elif any(header in line_upper for header in table_headers):
                skip_line = True
                skip_reason = f"Contains table header: {[h for h in table_headers if h in line_upper]}"
            elif line_upper.strip() in ['TRANS', 'POST', 'DESCRIPTION', 'AMOUNT', 'SPEND CATEGORIES']:
                skip_line = True
                skip_reason = f"Exact match header: {line_upper.strip()}"
            
            # Special debug for Lovisa line
            if 'lovisa' in line.lower():
                print(f"🔍 LOVISA DEBUG: skip_line={skip_line}, skip_reason={skip_reason}")
                print(f"🔍 LOVISA LINE_UPPER: '{line_upper}'")
                print(f"🔍 LOVISA HEADER_KEYWORDS: {[h for h in header_keywords if h in line_upper]}")
                print(f"🔍 LOVISA TABLE_HEADERS: {[h for h in table_headers if h in line_upper]}")
            
            if skip_line:
                print(f"SKIPPED HEADER: {line} (Reason: {skip_reason})")
                continue
            
            # More aggressive transaction detection
            # Any line with a month abbreviation followed by digits AND a decimal amount
            has_month_day = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}', line)
            has_decimal_amount = re.search(r'\d+\.\d{2}', line)
            
            # Additional check: if line contains "Lovisa" specifically, flag it for debugging
            if 'lovisa' in line.lower():
                print(f"🔍 FOUND LOVISA LINE: {line}")
                print(f"   Has month/day: {bool(has_month_day)}")
                print(f"   Has decimal amount: {bool(has_decimal_amount)}")
            
            transaction_match = None  # Initialize here
            
            if has_month_day and has_decimal_amount:
                print(f"FOUND TRANSACTION LINE {line_num}: {line}")
                
                transaction_match = None
                
                # Strategy 1: Amount at the end approach (most reliable)
                amount_matches = re.findall(r'(\d{1,3}(?:,\d{3})*\.\d{2})', line)
                if amount_matches:
                    # Take the last amount as the transaction amount
                    amount_str = amount_matches[-1]
                    
                    # Remove commas from amount before converting to float
                    clean_amount_str = amount_str.replace(',', '')
                    
                    # Find where this amount starts in the line
                    amount_pos = line.rfind(amount_str)
                    line_without_amount = line[:amount_pos].strip()
                    
                    # Extract dates from the beginning
                    date_pattern = re.match(r'(\w{3}\s+\d{1,2})\s+(\w{3}\s+\d{1,2})\s+(.+)', line_without_amount)
                    if date_pattern:
                        trans_date_str, post_date_str, description_and_category = date_pattern.groups()
                        
                        # Clean up the description and category part
                        desc_and_cat = description_and_category.strip()
                        
                        # Skip payment transactions - these are not expenses
                        if any(payment_keyword in desc_and_cat.upper() for payment_keyword in [
                            'PAYMENT THANK YOU', 'PAIEMENT MERCI', 'PAYMENT - THANK YOU', 
                            'THANK YOU FOR YOUR PAYMENT', 'PAYMENT RECEIVED'
                        ]):
                            print(f"SKIPPED PAYMENT: {desc_and_cat}")
                            continue
                        
                        # Try to identify where description ends and category begins
                        category_str = ""
                        description = desc_and_cat
                        
                        # Known categories (longest first to avoid partial matches)
                        known_categories = [
                            'Insurance and Financial Products',
                            'Hotel, Entertainment and Recreation',
                            'Professional and Financial Services',
                            'Personal and Household Expenses',
                            'Home and Office Improvement',
                            'Foreign Currency Transactions',
                            'Investments and Brokerage',
                            'Banking Fees and ATM',
                            'Transfers and Payments',
                            'Income and Payroll',
                            'Health and Education',
                            'Retail and Grocery',
                            'Transportation',
                            'Restaurants'
                        ]
                        
                        # Try to find category at the end
                        for cat in known_categories:
                            if desc_and_cat.endswith(cat):
                                category_str = cat
                                description = desc_and_cat[:-len(cat)].strip()
                                break
                        
                        # If no category found, try to extract from spacing patterns
                        if not category_str:
                            # Look for multiple spaces that might separate description from category
                            parts = re.split(r'\s{2,}', desc_and_cat)
                            if len(parts) >= 2:
                                description = parts[0].strip()
                                category_str = ' '.join(parts[1:]).strip()
                        
                        transaction_match = (trans_date_str, post_date_str, description, category_str, clean_amount_str)
                        print(f"EXTRACTED: Date={trans_date_str}, Desc='{description}', Cat='{category_str}', Amt={clean_amount_str} (original: {amount_str})")
                    else:
                        print(f"Could not extract dates from: {line_without_amount}")
                
                # If we found a transaction match, process it
            
            # If we found a transaction match, process it
            # If we found a transaction match, process it
            if transaction_match:
                try:
                    # Handle both tuple and regex match objects
                    if isinstance(transaction_match, tuple):
                        trans_date_str, post_date_str, description, category_str, amount_str = transaction_match
                    else:
                        trans_date_str, post_date_str, description, category_str, amount_str = transaction_match.groups()
                    
                    print(f"PROCESSING: Trans={trans_date_str}, Post={post_date_str}, Desc='{description}', Cat='{category_str}', Amt={amount_str}")
                except Exception as e:
                    print(f"Error processing transaction match: {e}")
                    continue
                
                try:
                    # Parse amount - Enhanced to handle negative amounts and credits
                    amount_str_clean = amount_str.strip()
                    
                    # Check for negative sign (indicates credit/payment)
                    is_credit = False
                    if amount_str_clean.startswith('-') or amount_str_clean.startswith('('):
                        is_credit = True
                        amount_str_clean = amount_str_clean.replace('-', '').replace('(', '').replace(')', '').strip()
                    
                    amount = float(amount_str_clean)
                    
                    # Apply negative for credits (payments, refunds)
                    if is_credit:
                        amount = -amount
                        print(f"💳 CREDIT/PAYMENT detected: ${abs(amount)} (stored as negative)")
                    else:
                        print(f"💰 DEBIT/CHARGE detected: ${amount} (stored as positive)")
                    
                    if abs(amount) < 0.01 or abs(amount) > 50000:
                        print(f"Skipping amount {amount} (out of range)")
                        continue
                    
                    # Clean description
                    description = re.sub(r'\s+', ' ', description.strip())
                    
                    # Parse transaction date (use trans_date, not post_date!)
                    transaction_date = parse_date_string(
                        trans_date_str,
                        statement_year,
                        statement_start=statement_start,
                        statement_end=statement_end,
                    )
                    if not transaction_date:
                        print(f"Failed to parse date: {trans_date_str}")
                        continue
                    
                    print(f"🗓️ DATE DEBUG: Input='{trans_date_str}' -> Parsed={transaction_date} -> Final ISO={transaction_date.isoformat()}")
                    
                    # Verify we're using transaction date, not post date
                    post_date_parsed = parse_date_string(
                        post_date_str,
                        statement_year,
                        statement_start=statement_start,
                        statement_end=statement_end,
                    )
                    if post_date_parsed:
                        print(f"🔍 COMPARISON: Transaction={transaction_date} vs Post={post_date_parsed} (using Transaction date)")
                    
                    # Clean and categorize
                    category = clean_category(category_str, description)
                    
                    # Create enhanced source name
                    enhanced_source = generate_source_name(user_name, 'credit', source_filename)
                    
                    # Create transaction
                    transaction = {
                        'date': transaction_date.isoformat(),
                        'description': description,
                        'category': category,
                        'amount': amount,
                        'account_type': 'credit_card',
                        'user_id': user_id,
                        'pdf_source': enhanced_source,
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
                            
                            transaction_date = parse_date_string(
                                trans_date_str,
                                statement_year,
                                statement_start=statement_start,
                                statement_end=statement_end,
                            )
                            if transaction_date and amount > 0.01:
                                # Create enhanced source name
                                enhanced_source = generate_source_name(user_name, 'credit', source_filename)
                                
                                transaction = {
                                    'date': transaction_date.isoformat(),
                                    'description': description.strip(),
                                    'category': category,
                                    'amount': amount,
                                    'account_type': 'credit_card',
                                    'user_id': user_id,
                                    'pdf_source': enhanced_source,
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

def parse_date_string(
    date_str: str,
    statement_year: int,
    statement_start: Optional[str] = None,
    statement_end: Optional[str] = None,
) -> date:
    """Parse date string like 'Oct 22' with statement-period-aware year handling."""
    try:
        month_map = {
            'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
            'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
        }

        compact_match = re.match(r'^\s*([A-Za-z]{3,})\s*(\d{1,2})\s*$', str(date_str or ""))
        if not compact_match:
            return None

        month_name = compact_match.group(1)
        day = int(compact_match.group(2))
        month = month_map.get(month_name[:3].title(), None)
        if not month:
            return None

        current_year = datetime.now().year
        year = statement_year if statement_year else current_year

        start_month = None
        end_month = None
        if statement_start:
            start_match = re.match(r'^\s*([A-Za-z]{3,})\s+\d{1,2}\s*$', str(statement_start))
            if start_match:
                start_month = month_map.get(start_match.group(1)[:3].title())
        if statement_end:
            end_match = re.match(r'^\s*([A-Za-z]{3,})\s+\d{1,2}\s*$', str(statement_end))
            if end_match:
                end_month = month_map.get(end_match.group(1)[:3].title())

        # Cross-year statements (e.g., Dec 15 to Jan 15, 2026):
        # statement_year is end-year; months on/after start_month belong to previous year.
        if statement_year and start_month and end_month and start_month > end_month:
            if month >= start_month:
                year = statement_year - 1
            else:
                year = statement_year
        elif statement_year and end_month and end_month <= 3 and month >= 10:
            # Fallback when only end month is available and statement is likely Jan/Feb/Mar.
            year = statement_year - 1

        parsed_date = date(year, month, day)
        print(f"Date parsing: '{date_str}' -> {parsed_date} (year context: {year})")
        return parsed_date
    except Exception as e:
        print(f"Date parsing error for '{date_str}': {e}")
    return None

GENERIC_CATEGORY_VALUES = {
    "",
    "category",
    "general",
    "misc",
    "miscellaneous",
    "n a",
    "na",
    "none",
    "null",
    "nan",
    "other",
    "uncategorized",
    "unknown",
}

MERCHANT_SIGNATURE_NOISE_WORDS = {
    "ab",
    "bc",
    "ca",
    "cad",
    "card",
    "cdn",
    "com",
    "credit",
    "debit",
    "ecom",
    "merchant",
    "online",
    "payment",
    "pos",
    "purchase",
    "qc",
    "recurring",
    "store",
    "thank",
    "visa",
    "www",
}

CATEGORY_MATCH_RULES = {
    "Retail and Grocery": {
        "phrases": {
            "amzn": 5,
            "amzn mktp": 7,
            "amazon": 4,
            "amazon ca": 6,
            "costco": 6,
            "costco wholesal": 6,
            "dollarama": 6,
            "freshco": 6,
            "indigo": 4,
            "indigopk": 5,
            "instacart": 5,
            "loblaws": 6,
            "metro": 5,
            "nofrills": 6,
            "real canadian superstore": 8,
            "safeway": 6,
            "shopper": 4,
            "sobeys": 6,
            "superstore": 6,
            "tandt": 5,
            "t and t": 5,
            "walmart": 6,
        },
        "tokens": {
            "grocery": 4,
            "groceries": 4,
            "mart": 2,
            "market": 2,
            "supermarket": 4,
        },
    },
    "Restaurants": {
        "phrases": {
            "a and w": 5,
            "a&w": 5,
            "burger king": 5,
            "cafe": 3,
            "coffee": 3,
            "doordash": 6,
            "mcdonald": 6,
            "pizza": 4,
            "restaurant": 4,
            "skip the dishes": 6,
            "starbucks": 6,
            "subway": 5,
            "tim hortons": 6,
            "uber eats": 7,
        },
        "tokens": {
            "bar": 2,
            "bistro": 3,
            "brunch": 3,
            "dining": 3,
            "eatery": 3,
            "food": 2,
            "lunch": 3,
            "restaurant": 4,
        },
    },
    "Transportation": {
        "phrases": {
            "air canada": 6,
            "calgary transit": 7,
            "chevron": 5,
            "esso": 5,
            "lyft": 6,
            "parkplus": 6,
            "parking": 4,
            "petro canada": 7,
            "shell": 5,
            "taxi": 5,
            "uber": 6,
            "westjet": 6,
        },
        "tokens": {
            "flight": 3,
            "fuel": 3,
            "gas": 4,
            "transit": 4,
            "transport": 3,
        },
    },
    "Home and Office Improvement": {
        "phrases": {
            "best buy": 5,
            "canadian tire": 7,
            "home depot": 8,
            "ikea": 6,
            "lowes": 7,
            "rona": 6,
            "staples": 6,
            "stokes": 5,
        },
        "tokens": {
            "furniture": 3,
            "hardware": 4,
            "home": 2,
            "office": 4,
            "supplies": 2,
        },
    },
    "Hotel, Entertainment and Recreation": {
        "phrases": {
            "airbnb": 7,
            "apple com bill": 5,
            "booking com": 6,
            "cineplex": 6,
            "expedia": 6,
            "goodlife": 6,
            "hotel": 6,
            "netflix": 6,
            "spotify": 6,
            "steam": 6,
            "ticketmaster": 6,
            "youtube premium": 6,
        },
        "tokens": {
            "entertainment": 4,
            "gym": 4,
            "movie": 4,
            "recreation": 4,
            "streaming": 4,
        },
    },
    "Transfers and Payments": {
        "phrases": {
            "bill payment": 7,
            "e transfer": 10,
            "e-transfer": 10,
            "interac e transfer": 12,
            "interac e-transfer": 12,
            "internet transfer": 11,
            "transfer from": 8,
            "transfer to": 8,
            "wire transfer": 10,
        },
        "tokens": {
            "autodep": 8,
            "autodeposit": 8,
            "interac": 8,
            "payment": 4,
            "transfer": 8,
        },
    },
    "Income and Payroll": {
        "phrases": {
            "direct deposit payroll": 14,
            "grouphealth": 9,
            "pay humi payroll": 14,
            "payroll deposit": 14,
            "tax refund": 11,
            "pay 2301114 alberta": 16,
            "o/a watts": 14,
        },
        "tokens": {
            "income": 8,
            "payroll": 10,
            "refund": 6,
            "salary": 10,
            "wages": 10,
        },
    },
    "Banking Fees and ATM": {
        "phrases": {
            "atm interac": 11,
            "atm withdrawal": 12,
            "monthly fee": 10,
            "network transaction fee": 14,
            "nsf": 12,
            "record keeping": 10,
            "service charge": 13,
        },
        "tokens": {
            "atm": 10,
            "charge": 5,
            "fee": 8,
            "nsf": 12,
            "withdrawal": 5,
        },
    },
    "Insurance and Financial Products": {
        "phrases": {
            "insurance": 10,
            "intact insurance company": 12,
            "loan payment": 10,
            "mortgage": 10,
            "principal payment": 10,
        },
        "tokens": {
            "insurance": 8,
            "loan": 8,
            "mortgage": 8,
            "principal": 6,
        },
    },
    "Investments and Brokerage": {
        "phrases": {
            "brokerage": 10,
            "questrade": 12,
            "wealthsimple": 14,
        },
        "tokens": {
            "brokerage": 8,
            "investment": 8,
            "investments": 8,
            "rrsp": 8,
            "tfsa": 8,
            "wealthsimple": 12,
        },
    },
    "Professional and Financial Services": {
        "phrases": {
            "adobe": 8,
            "canva": 8,
            "chatgpt": 10,
            "github": 8,
            "notion": 8,
            "openai": 10,
            "paypal": 6,
            "quickbooks": 8,
            "wise": 6,
        },
        "tokens": {
            "accounting": 6,
            "legal": 6,
            "professional": 6,
            "service": 3,
            "subscription": 4,
        },
    },
    "Health and Education": {
        "phrases": {
            "coursera": 6,
            "dental": 7,
            "doctor": 6,
            "hospital": 7,
            "pharmacy": 7,
            "shoppers drug mart": 7,
            "udemy": 6,
            "university": 7,
        },
        "tokens": {
            "clinic": 5,
            "education": 4,
            "health": 4,
            "medical": 5,
            "school": 5,
            "tuition": 5,
        },
    },
    "Foreign Currency Transactions": {
        "phrases": {
            "foreign currency": 10,
            "foreign transaction": 8,
        },
        "tokens": {
            "currency": 6,
            "exchange": 6,
            "foreign": 6,
            "international": 4,
            "usd": 5,
        },
    },
}

def normalize_text(value: Optional[str]) -> str:
    """Normalize text for fuzzy category and merchant matching."""
    if value is None:
        return ""

    normalized = str(value).strip()
    if not normalized:
        return ""

    # OCR strings frequently merge words by casing transitions (e.g. "TransferReceived").
    normalized = re.sub(r"([a-z])([A-Z])", r"\1 \2", normalized)
    normalized = normalized.lower()
    normalized = normalized.replace("&", " and ")
    normalized = re.sub(r"e[\-\s]*transfer\s*received", "e transfer received", normalized)
    normalized = re.sub(r"e[\-\s]*transfer\s*sent", "e transfer sent", normalized)
    normalized = normalized.replace("autodep", "autodeposit")
    normalized = re.sub(r"https?://\S+", " ", normalized)
    normalized = re.sub(r"www\.", " ", normalized)
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()

def resolve_category_name(category_value: Optional[str], available_categories: Optional[List[str]] = None) -> Optional[str]:
    """Resolve a user-provided category string to an existing category name."""
    normalized_value = normalize_text(category_value)
    if not normalized_value or normalized_value in GENERIC_CATEGORY_VALUES:
        return None

    candidate_categories = available_categories or DEFAULT_CATEGORIES
    normalized_candidates = {normalize_text(category): category for category in candidate_categories}

    if normalized_value in normalized_candidates:
        return normalized_candidates[normalized_value]

    normalized_value_tokens = set(normalized_value.split())
    for candidate_normalized, candidate_name in normalized_candidates.items():
        candidate_tokens = set(candidate_normalized.split())
        if normalized_value in candidate_normalized or candidate_normalized in normalized_value:
            return candidate_name
        if candidate_tokens and len(candidate_tokens & normalized_value_tokens) >= max(1, len(candidate_tokens) - 1):
            return candidate_name

    return None

def build_merchant_signature(description: Optional[str]) -> str:
    """Create a stable merchant signature so repeated merchants can reuse past category choices."""
    normalized_description = normalize_text(description)
    if not normalized_description:
        return ""

    signature_tokens = []
    for token in normalized_description.split():
        if token in MERCHANT_SIGNATURE_NOISE_WORDS:
            continue
        if token.isdigit():
            continue
        if len(token) == 1:
            continue
        if re.fullmatch(r"\d+[a-z]*", token):
            continue
        signature_tokens.append(token)
        if len(signature_tokens) == 4:
            break

    return " ".join(signature_tokens)

def score_categories_from_text(text: Optional[str]) -> Dict[str, int]:
    """Score categories against a normalized description or category hint."""
    normalized_text = normalize_text(text)
    if not normalized_text:
        return {}

    padded_text = f" {normalized_text} "
    text_tokens = set(normalized_text.split())
    category_scores = defaultdict(int)

    for category_name, rules in CATEGORY_MATCH_RULES.items():
        for phrase, weight in rules.get("phrases", {}).items():
            normalized_phrase = normalize_text(phrase)
            if not normalized_phrase:
                continue
            if (
                f" {normalized_phrase} " in padded_text
                or normalized_text.startswith(normalized_phrase)
                or normalized_phrase in normalized_text
            ):
                category_scores[category_name] += weight

        for token, weight in rules.get("tokens", {}).items():
            normalized_token = normalize_text(token)
            if normalized_token and normalized_token in text_tokens:
                category_scores[category_name] += weight

    # Boost "Income and Payroll" for descriptions starting with "PAY " (employer payroll deposits)
    if re.match(r"^pay\s", normalized_text):
        category_scores["Income and Payroll"] += 12

    return dict(category_scores)

def infer_category_from_context(
    description: str,
    category_hint: Optional[str] = None,
    available_categories: Optional[List[str]] = None,
    merchant_history: Optional[Dict[str, Counter]] = None,
) -> str:
    """Infer the best category using explicit hints, past user choices, and merchant rules."""
    resolved_hint = resolve_category_name(category_hint, available_categories)
    if resolved_hint:
        return resolved_hint

    merchant_signature = build_merchant_signature(description)
    if merchant_signature and merchant_history and merchant_signature in merchant_history:
        learned_category, _ = merchant_history[merchant_signature].most_common(1)[0]
        resolved_learned_category = resolve_category_name(learned_category, available_categories)
        if resolved_learned_category:
            return resolved_learned_category

    combined_scores = defaultdict(int)
    for candidate_text in [category_hint, description]:
        for category_name, score in score_categories_from_text(candidate_text).items():
            combined_scores[category_name] += score

    if combined_scores:
        best_category, best_score = max(combined_scores.items(), key=lambda item: item[1])
        if best_score >= 3:
            return resolve_category_name(best_category, available_categories) or best_category

    return "Personal and Household Expenses"

async def load_user_category_context(user_id: str) -> tuple[List[str], Dict[str, Counter]]:
    """Load a user's category names and historical merchant-category mappings."""
    await initialize_default_categories(user_id)

    category_docs = await db.categories.find({"user_id": user_id}, {"name": 1}).to_list(200)
    category_names = [category["name"] for category in category_docs if category.get("name")]

    transaction_docs = await db.transactions.find(
        {"user_id": user_id},
        {"description": 1, "category": 1, "merchant_signature": 1}
    ).to_list(5000)

    merchant_history: Dict[str, Counter] = defaultdict(Counter)
    for transaction in transaction_docs:
        category_name = transaction.get("category")
        merchant_signature = transaction.get("merchant_signature") or build_merchant_signature(transaction.get("description", ""))
        if category_name and merchant_signature:
            merchant_history[merchant_signature][category_name] += 1

    return category_names, merchant_history

async def resolve_transaction_category(
    user_id: str,
    description: str,
    category_hint: Optional[str] = None,
    category_names: Optional[List[str]] = None,
    merchant_history: Optional[Dict[str, Counter]] = None,
) -> str:
    """Resolve the best category for a transaction using user-specific context."""
    if category_names is None or merchant_history is None:
        category_names, merchant_history = await load_user_category_context(user_id)

    return infer_category_from_context(
        description=description,
        category_hint=category_hint,
        available_categories=category_names,
        merchant_history=merchant_history,
    )

def clean_category(category_str: str, description: str) -> str:
    """Clean and standardize category for synchronous PDF parsing helpers."""
    return infer_category_from_context(description=description, category_hint=category_str)

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

PLAID_PRIMARY_CATEGORY_MAP = {
    "BANK_FEES": "Banking Fees and ATM",
    "ENTERTAINMENT": "Hotel, Entertainment and Recreation",
    "FOOD_AND_DRINK": "Restaurants",
    "GENERAL_MERCHANDISE": "Retail and Grocery",
    "GENERAL_SERVICES": "Professional and Financial Services",
    "GOVERNMENT_AND_NON_PROFIT": "Professional and Financial Services",
    "HOME_IMPROVEMENT": "Home and Office Improvement",
    "INCOME": "Income and Payroll",
    "LOAN_PAYMENTS": "Transfers and Payments",
    "MEDICAL": "Health and Education",
    "PERSONAL_CARE": "Personal and Household Expenses",
    "RENT_AND_UTILITIES": "Home and Office Improvement",
    "TRANSPORTATION": "Transportation",
    "TRANSFER_IN": "Transfers and Payments",
    "TRANSFER_OUT": "Transfers and Payments",
    "TRAVEL": "Hotel, Entertainment and Recreation",
}

def plaid_enabled() -> bool:
    return bool(PLAID_SDK_AVAILABLE and plaid_client and PLAID_CLIENT_ID and PLAID_SECRET)

def require_plaid_client():
    if plaid_enabled():
        return plaid_client
    if not PLAID_SDK_AVAILABLE:
        raise HTTPException(status_code=503, detail="Plaid SDK is not installed on this server.")
    raise HTTPException(
        status_code=503,
        detail="Plaid is not configured. Set PLAID_CLIENT_ID, PLAID_SECRET, and PLAID_ENV.",
    )

async def call_plaid(request_fn, request_body):
    return await asyncio.to_thread(request_fn, request_body)

def parse_plaid_error(api_error: Exception) -> tuple[str, Optional[str]]:
    error_message = str(api_error)
    error_code = None
    raw_body = getattr(api_error, "body", None)
    if raw_body:
        try:
            payload = json.loads(raw_body)
            error_message = (
                payload.get("error_message")
                or payload.get("display_message")
                or payload.get("error_code")
                or error_message
            )
            error_code = payload.get("error_code")
            error_type = payload.get("error_type")
            if error_type:
                error_message = f"{error_type}: {error_message}"
        except Exception:
            pass
    return error_message, error_code

def safe_iso(value: Any) -> Optional[str]:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)

def serialize_connection_document(document: dict) -> dict:
    clean_doc = dict(document)
    clean_doc.pop("_id", None)
    clean_doc.pop("access_token", None)
    for field_name in ["created_at", "updated_at", "last_successful_sync", "last_error_at"]:
        clean_doc[field_name] = safe_iso(clean_doc.get(field_name))
    clean_doc["account_count"] = len(clean_doc.get("accounts") or [])
    return clean_doc

def map_plaid_account_type(account_type: Optional[str], account_subtype: Optional[str]) -> str:
    type_value = str(account_type or "").lower()
    subtype_value = str(account_subtype or "").lower()
    if type_value == "credit" or "credit" in subtype_value:
        return "credit_card"
    return "debit"

def map_plaid_category_hint(
    primary_category: Optional[str],
    detailed_category: Optional[str],
    description: Optional[str] = None,
) -> Optional[str]:
    primary = str(primary_category or "").upper()
    detailed = str(detailed_category or "").upper()
    description_text = normalize_text(description)

    if detailed.startswith("INCOME_"):
        return "Income and Payroll"
    if detailed.startswith("BANK_FEES_"):
        return "Banking Fees and ATM"
    if detailed.startswith("TRANSFER_"):
        return "Transfers and Payments"
    if detailed.startswith("LOAN_PAYMENTS_"):
        return "Transfers and Payments"
    if detailed.startswith("INVESTMENT_"):
        return "Investments and Brokerage"
    if detailed.startswith("INSURANCE_"):
        return "Insurance and Financial Products"
    if detailed.startswith("MEDICAL_"):
        return "Health and Education"
    if detailed.startswith("TRAVEL_"):
        return "Hotel, Entertainment and Recreation"
    if detailed.startswith("FOOD_AND_DRINK_GROCERIES"):
        return "Retail and Grocery"

    if primary in PLAID_PRIMARY_CATEGORY_MAP:
        return PLAID_PRIMARY_CATEGORY_MAP[primary]

    if "subscription" in description_text:
        return "Professional and Financial Services"
    return None

def infer_plaid_internal_transfer_flag(
    primary_category: Optional[str],
    detailed_category: Optional[str],
) -> Optional[bool]:
    primary = str(primary_category or "").upper()
    detailed = str(detailed_category or "").upper()
    category_blob = f"{primary}:{detailed}"
    if "ACCOUNT_TRANSFER" in category_blob:
        return True
    if category_blob.startswith("TRANSFER_"):
        return None
    return None

def build_plaid_source_name(institution_name: Optional[str], account_name: Optional[str]) -> str:
    bank_label = (institution_name or "Connected Bank").strip()
    account_label = (account_name or "Account").strip()
    return f"Plaid - {bank_label} - {account_label}"

def build_account_snapshot(account_obj: Any) -> dict:
    return {
        "account_id": getattr(account_obj, "account_id", None),
        "name": getattr(account_obj, "name", None),
        "official_name": getattr(account_obj, "official_name", None),
        "mask": getattr(account_obj, "mask", None),
        "type": getattr(account_obj, "type", None),
        "subtype": getattr(account_obj, "subtype", None),
    }

async def fetch_plaid_accounts_for_item(access_token: str) -> tuple[List[Any], Optional[Any]]:
    plaid_api_client = require_plaid_client()
    accounts_request = AccountsGetRequest(access_token=access_token)
    accounts_response = await call_plaid(plaid_api_client.accounts_get, accounts_request)
    accounts = list(getattr(accounts_response, "accounts", []) or [])
    item = getattr(accounts_response, "item", None)
    return accounts, item

async def resolve_plaid_institution_name(institution_id: Optional[str], fallback_name: Optional[str]) -> Optional[str]:
    if fallback_name:
        return fallback_name
    if not institution_id:
        return None

    plaid_api_client = require_plaid_client()
    try:
        institution_request = InstitutionsGetByIdRequest(
            institution_id=institution_id,
            country_codes=[CountryCode(code) for code in PLAID_COUNTRY_CODES],
        )
        institution_response = await call_plaid(plaid_api_client.institutions_get_by_id, institution_request)
        institution = getattr(institution_response, "institution", None)
        return getattr(institution, "name", None) if institution else None
    except Exception:
        return None

async def upsert_plaid_transaction_record(
    user_id: str,
    user_name: Optional[str],
    item_id: str,
    institution_name: Optional[str],
    plaid_transaction: Any,
    accounts_by_id: Dict[str, Any],
    category_names: List[str],
    merchant_history: Dict[str, Counter],
) -> str:
    plaid_transaction_id = getattr(plaid_transaction, "transaction_id", None)
    if not plaid_transaction_id:
        return "skipped"

    transaction_date_raw = getattr(plaid_transaction, "date", None)
    if not transaction_date_raw:
        return "skipped"
    transaction_date = safe_iso(transaction_date_raw)
    if not transaction_date:
        return "skipped"
    transaction_date = transaction_date.split("T")[0]

    amount_value = float(getattr(plaid_transaction, "amount", 0) or 0)
    description = re.sub(
        r"\s+",
        " ",
        str(getattr(plaid_transaction, "merchant_name", None) or getattr(plaid_transaction, "name", "") or "").strip(),
    )
    if not description:
        description = "Plaid Transaction"

    plaid_account_id = getattr(plaid_transaction, "account_id", None)
    account_obj = accounts_by_id.get(plaid_account_id)
    account_name = (
        str(getattr(account_obj, "official_name", None) or getattr(account_obj, "name", None) or "Account").strip()
    )
    account_mask = getattr(account_obj, "mask", None)
    account_type = map_plaid_account_type(
        getattr(account_obj, "type", None),
        getattr(account_obj, "subtype", None),
    )

    personal_finance_category = getattr(plaid_transaction, "personal_finance_category", None)
    primary_category = getattr(personal_finance_category, "primary", None) if personal_finance_category else None
    detailed_category = getattr(personal_finance_category, "detailed", None) if personal_finance_category else None
    category_hint = map_plaid_category_hint(primary_category, detailed_category, description)
    resolved_category = await resolve_transaction_category(
        user_id=user_id,
        description=description,
        category_hint=category_hint,
        category_names=category_names,
        merchant_history=merchant_history,
    )

    merchant_signature = build_merchant_signature(description)
    if merchant_signature:
        merchant_history[merchant_signature][resolved_category] += 1

    update_doc = {
        "date": transaction_date,
        "description": description,
        "category": resolved_category,
        "amount": amount_value,
        "account_type": account_type,
        "user_id": user_id,
        "pdf_source": build_plaid_source_name(institution_name, account_name),
        "user_name": user_name,
        "merchant_signature": merchant_signature,
        "is_internal_transfer": infer_plaid_internal_transfer_flag(primary_category, detailed_category),
        "plaid_transaction_id": plaid_transaction_id,
        "plaid_pending_transaction_id": getattr(plaid_transaction, "pending_transaction_id", None),
        "plaid_account_id": plaid_account_id,
        "plaid_item_id": item_id,
        "plaid_institution_name": institution_name,
        "plaid_account_name": account_name,
        "plaid_account_mask": account_mask,
        "plaid_personal_finance_primary": primary_category,
        "plaid_personal_finance_detailed": detailed_category,
        "plaid_pending": bool(getattr(plaid_transaction, "pending", False)),
        "source_type": "plaid",
        "source_provider": "plaid",
        "updated_at": datetime.utcnow(),
    }

    existing_plaid = await db.transactions.find_one({
        "user_id": user_id,
        "plaid_transaction_id": plaid_transaction_id,
    })
    if existing_plaid:
        if existing_plaid.get("is_internal_transfer") in [True, False]:
            update_doc["is_internal_transfer"] = existing_plaid.get("is_internal_transfer")
        if existing_plaid.get("is_inflow") in [True, False]:
            update_doc["is_inflow"] = existing_plaid.get("is_inflow")

        await db.transactions.update_one(
            {"id": existing_plaid["id"], "user_id": user_id},
            {"$set": update_doc},
        )
        return "modified"

    existing_shape_match = await db.transactions.find_one({
        "user_id": user_id,
        "date": transaction_date,
        "description": description,
        "amount": amount_value,
        "$or": [
            {"plaid_transaction_id": {"$exists": False}},
            {"plaid_transaction_id": None},
        ],
    })
    if existing_shape_match:
        if existing_shape_match.get("category"):
            update_doc["category"] = existing_shape_match["category"]
        if existing_shape_match.get("is_internal_transfer") in [True, False]:
            update_doc["is_internal_transfer"] = existing_shape_match.get("is_internal_transfer")
        if existing_shape_match.get("is_inflow") in [True, False]:
            update_doc["is_inflow"] = existing_shape_match.get("is_inflow")

        await db.transactions.update_one(
            {"id": existing_shape_match["id"], "user_id": user_id},
            {"$set": update_doc},
        )
        return "merged"

    new_transaction = {
        "id": str(uuid.uuid4()),
        "created_at": datetime.utcnow(),
        **update_doc,
    }
    await db.transactions.insert_one(new_transaction)
    return "added"

async def sync_single_plaid_item(item_doc: dict, user_id: str, user_name: Optional[str]) -> dict:
    plaid_api_client = require_plaid_client()
    access_token = item_doc.get("access_token")
    item_id = item_doc.get("item_id")
    if not access_token or not item_id:
        raise HTTPException(status_code=400, detail="Plaid connection is missing required credentials.")

    try:
        accounts, account_item = await fetch_plaid_accounts_for_item(access_token)
    except plaid.ApiException as plaid_error:
        message, _ = parse_plaid_error(plaid_error)
        raise HTTPException(status_code=502, detail=f"Plaid accounts fetch failed: {message}")

    institution_id = item_doc.get("institution_id") or getattr(account_item, "institution_id", None)
    institution_name = await resolve_plaid_institution_name(
        institution_id,
        item_doc.get("institution_name") or getattr(account_item, "institution_name", None),
    )
    accounts_by_id = {
        getattr(account_obj, "account_id", None): account_obj
        for account_obj in accounts
        if getattr(account_obj, "account_id", None)
    }

    cursor = item_doc.get("cursor")
    initial_cursor = cursor
    pagination_retry_used = False
    added_transactions: List[Any] = []
    modified_transactions: List[Any] = []
    removed_transactions: List[Any] = []
    next_cursor = cursor

    while True:
        try:
            working_cursor = initial_cursor if pagination_retry_used else cursor
            added_transactions = []
            modified_transactions = []
            removed_transactions = []

            has_more = True
            while has_more:
                sync_request_payload = {
                    "access_token": access_token,
                    "count": 500,
                }
                if working_cursor:
                    sync_request_payload["cursor"] = working_cursor

                sync_request = TransactionsSyncRequest(**sync_request_payload)
                sync_response = await call_plaid(plaid_api_client.transactions_sync, sync_request)

                added_transactions.extend(list(getattr(sync_response, "added", []) or []))
                modified_transactions.extend(list(getattr(sync_response, "modified", []) or []))
                removed_transactions.extend(list(getattr(sync_response, "removed", []) or []))
                working_cursor = getattr(sync_response, "next_cursor", working_cursor)
                has_more = bool(getattr(sync_response, "has_more", False))

            next_cursor = working_cursor
            break
        except plaid.ApiException as plaid_error:
            error_message, error_code = parse_plaid_error(plaid_error)
            if error_code == "TRANSACTIONS_SYNC_MUTATION_DURING_PAGINATION" and not pagination_retry_used:
                pagination_retry_used = True
                continue
            raise HTTPException(status_code=502, detail=f"Plaid transaction sync failed: {error_message}")

    removed_count = 0
    for removed_tx in removed_transactions:
        removed_transaction_id = getattr(removed_tx, "transaction_id", None)
        if not removed_transaction_id:
            continue
        delete_result = await db.transactions.delete_many({
            "user_id": user_id,
            "plaid_transaction_id": removed_transaction_id,
        })
        removed_count += delete_result.deleted_count

    category_names, merchant_history = await load_user_category_context(user_id)
    added_count = 0
    modified_count = 0
    merged_count = 0

    for plaid_transaction in added_transactions:
        result_type = await upsert_plaid_transaction_record(
            user_id=user_id,
            user_name=user_name,
            item_id=item_id,
            institution_name=institution_name,
            plaid_transaction=plaid_transaction,
            accounts_by_id=accounts_by_id,
            category_names=category_names,
            merchant_history=merchant_history,
        )
        if result_type == "added":
            added_count += 1
        elif result_type == "modified":
            modified_count += 1
        elif result_type == "merged":
            merged_count += 1

    for plaid_transaction in modified_transactions:
        result_type = await upsert_plaid_transaction_record(
            user_id=user_id,
            user_name=user_name,
            item_id=item_id,
            institution_name=institution_name,
            plaid_transaction=plaid_transaction,
            accounts_by_id=accounts_by_id,
            category_names=category_names,
            merchant_history=merchant_history,
        )
        if result_type == "added":
            added_count += 1
        elif result_type == "modified":
            modified_count += 1
        elif result_type == "merged":
            merged_count += 1

    now_utc = datetime.utcnow()
    await db.plaid_items.update_one(
        {"id": item_doc["id"], "user_id": user_id},
        {
            "$set": {
                "institution_id": institution_id,
                "institution_name": institution_name,
                "accounts": [build_account_snapshot(account_obj) for account_obj in accounts],
                "cursor": next_cursor,
                "status": "active",
                "last_successful_sync": now_utc,
                "updated_at": now_utc,
            },
            "$unset": {
                "last_error": "",
                "last_error_at": "",
            },
        },
    )

    return {
        "item_id": item_id,
        "institution_name": institution_name,
        "accounts_synced": len(accounts),
        "added_count": added_count,
        "modified_count": modified_count,
        "merged_count": merged_count,
        "removed_count": removed_count,
        "next_cursor": next_cursor,
    }

# Initialize default categories
DEFAULT_CATEGORIES = [
    "Retail and Grocery",
    "Restaurants",
    "Transportation",
    "Home and Office Improvement",
    "Hotel, Entertainment and Recreation",
    "Transfers and Payments",
    "Income and Payroll",
    "Banking Fees and ATM",
    "Insurance and Financial Products",
    "Investments and Brokerage",
    "Professional and Financial Services",
    "Health and Education",
    "Foreign Currency Transactions",
    "Personal and Household Expenses"
]

async def initialize_default_categories(user_id: str):
    """Initialize default categories for a user"""
    existing_categories = await db.categories.find({"user_id": user_id}, {"name": 1}).to_list(200)
    existing_names = {category.get("name") for category in existing_categories if category.get("name")}
    default_categories = []
    colors = [
        "#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#06B6D4", "#84CC16",
        "#F97316", "#6B7280", "#0EA5E9", "#14B8A6", "#F43F5E", "#A855F7", "#22C55E"
    ]

    for i, cat_name in enumerate(DEFAULT_CATEGORIES):
        if cat_name in existing_names:
            continue

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
    existing_category = await db.categories.find_one({"id": category_id, "user_id": user_id})

    if not existing_category:
        raise HTTPException(status_code=404, detail="Category not found")

    old_name = existing_category.get("name")
    new_name = update_data.get("name", old_name)

    if not update_data:
        return Category(**existing_category)
    
    result = await db.categories.update_one(
        {"id": category_id, "user_id": user_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Category not found")

    if new_name and old_name and new_name != old_name:
        await db.transactions.update_many(
            {"user_id": user_id, "category": old_name},
            {"$set": {"category": new_name, "updated_at": datetime.utcnow()}}
        )
    
    updated_category = await db.categories.find_one({"id": category_id, "user_id": user_id})
    return Category(**updated_category)

@api_router.delete("/categories/{category_id}")
async def delete_category(category_id: str, user_id: str = Depends(get_current_user_id)):
    existing_category = await db.categories.find_one({"id": category_id, "user_id": user_id})
    if not existing_category:
        raise HTTPException(status_code=404, detail="Category not found")

    if existing_category.get("is_default"):
        raise HTTPException(status_code=400, detail="Default categories cannot be deleted")

    # Transactions store category names, not category ids.
    transactions_using_category = await db.transactions.count_documents({
        "category": existing_category.get("name"),
        "user_id": user_id
    })
    
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
@api_router.post("/transactions")
async def create_transaction(
    transaction: dict, 
    current_user_id: str = Depends(get_current_user_id)
):
    try:
        description = re.sub(r"\s+", " ", str(transaction["description"]).strip())
        category_names, merchant_history = await load_user_category_context(current_user_id)
        resolved_category = await resolve_transaction_category(
            user_id=current_user_id,
            description=description,
            category_hint=transaction.get("category"),
            category_names=category_names,
            merchant_history=merchant_history,
        )

        # Create transaction document with manual inflow/outflow override
        transaction_doc = {
            "id": str(uuid.uuid4()),
            "user_id": current_user_id,
            "date": transaction["date"],
            "description": description,
            "category": resolved_category,
            "amount": float(transaction["amount"]),
            "account_type": transaction.get("account_type", "credit_card"),
            "pdf_source": transaction.get("pdf_source", "Manual"),
            "created_at": datetime.utcnow(),
            # NEW: Allow manual override of inflow/outflow
            "is_inflow": transaction.get("is_inflow", None),  # None means auto-detect
            "is_internal_transfer": transaction.get("is_internal_transfer", None),
            "original_amount": float(transaction["amount"]),  # Store original for reference
            "merchant_signature": build_merchant_signature(description),
        }
        
        # If is_inflow is manually set, respect that override
        if transaction_doc["is_inflow"] is not None:
            if transaction_doc["is_inflow"] and transaction_doc["amount"] > 0:
                transaction_doc["amount"] = -abs(transaction_doc["amount"])
            elif not transaction_doc["is_inflow"] and transaction_doc["amount"] < 0:
                transaction_doc["amount"] = abs(transaction_doc["amount"])
        
        await db.transactions.insert_one(transaction_doc)
        
        return {"message": "Transaction created successfully", "id": transaction_doc["id"]}
    except Exception as e:
        logging.error(f"Error creating transaction: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/transactions", response_model=List[Transaction])
async def get_transactions(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category: Optional[str] = None,
    pdf_source: Optional[str] = None,
    account_type: Optional[str] = None,
    sort_by: Optional[str] = "date",
    sort_order: Optional[str] = "desc",
    current_user: dict = Depends(get_current_user),
    view_user_id: str = Depends(get_view_user_id),
):
    filter_dict = await build_view_filter(current_user, view_user_id)
    
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
    if account_type:
        filter_dict["account_type"] = account_type
    
    # Handle sorting
    sort_direction = -1 if sort_order == "desc" else 1
    sort_field = sort_by if sort_by in ["date", "amount", "description", "category"] else "date"
    
    transactions = await db.transactions.find(filter_dict).sort(sort_field, sort_direction).to_list(1000)
    return [Transaction(**transaction) for transaction in transactions]

@api_router.get("/transactions/sources")
async def get_pdf_sources(
    current_user: dict = Depends(get_current_user),
    view_user_id: str = Depends(get_view_user_id),
):
    """Get list of unique PDF sources for filtering"""
    view_filter = await build_view_filter(current_user, view_user_id)
    source_filter = {**view_filter, "pdf_source": {"$ne": None}}
    sources = await db.transactions.distinct("pdf_source", source_filter)
    return {"sources": sources}

@api_router.get("/plaid/status")
async def get_plaid_status(current_user: dict = Depends(get_current_user)):
    return {
        "enabled": plaid_enabled(),
        "sdk_available": PLAID_SDK_AVAILABLE,
        "configured": bool(PLAID_CLIENT_ID and PLAID_SECRET),
        "environment": PLAID_ENV,
        "products": PLAID_PRODUCTS,
        "country_codes": PLAID_COUNTRY_CODES,
    }

@api_router.post("/plaid/link-token/create")
async def create_plaid_link_token(current_user: dict = Depends(get_current_user)):
    plaid_api_client = require_plaid_client()
    try:
        product_values = []
        for product in PLAID_PRODUCTS or ["transactions"]:
            try:
                product_values.append(Products(product))
            except Exception:
                continue
        if not product_values:
            product_values = [Products("transactions")]

        country_values = []
        for country_code in PLAID_COUNTRY_CODES or ["CA"]:
            try:
                country_values.append(CountryCode(country_code))
            except Exception:
                continue
        if not country_values:
            country_values = [CountryCode("CA")]

        request_payload = {
            "products": product_values,
            "client_name": PLAID_CLIENT_NAME,
            "country_codes": country_values,
            "language": "en",
            "user": LinkTokenCreateRequestUser(client_user_id=current_user["id"]),
        }
        if PLAID_REDIRECT_URI:
            request_payload["redirect_uri"] = PLAID_REDIRECT_URI
        if PLAID_WEBHOOK_URL:
            request_payload["webhook"] = PLAID_WEBHOOK_URL

        link_request = LinkTokenCreateRequest(**request_payload)
        link_response = await call_plaid(plaid_api_client.link_token_create, link_request)
        return {
            "link_token": link_response.link_token,
            "expiration": safe_iso(getattr(link_response, "expiration", None)),
            "request_id": getattr(link_response, "request_id", None),
        }
    except plaid.ApiException as plaid_error:
        error_message, _ = parse_plaid_error(plaid_error)
        raise HTTPException(status_code=502, detail=f"Plaid link token error: {error_message}")
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Plaid link-token error: {e}")
        raise HTTPException(status_code=500, detail="Unable to create Plaid link token.")

@api_router.post("/plaid/exchange-public-token")
async def exchange_plaid_public_token(
    payload: PlaidPublicTokenExchangeRequestBody,
    current_user: dict = Depends(get_current_user),
):
    plaid_api_client = require_plaid_client()
    user_id = current_user["id"]

    try:
        exchange_request = ItemPublicTokenExchangeRequest(public_token=payload.public_token)
        exchange_response = await call_plaid(plaid_api_client.item_public_token_exchange, exchange_request)
    except plaid.ApiException as plaid_error:
        error_message, _ = parse_plaid_error(plaid_error)
        raise HTTPException(status_code=502, detail=f"Plaid exchange error: {error_message}")

    item_id = getattr(exchange_response, "item_id", None)
    access_token = getattr(exchange_response, "access_token", None)
    if not item_id or not access_token:
        raise HTTPException(status_code=502, detail="Plaid exchange failed: missing item/access token.")

    now_utc = datetime.utcnow()
    existing_connection = await db.plaid_items.find_one({"user_id": user_id, "item_id": item_id})
    connection_id = existing_connection["id"] if existing_connection else str(uuid.uuid4())

    institution_id = None
    institution_name = None
    accounts_snapshot: List[dict] = []
    try:
        accounts, account_item = await fetch_plaid_accounts_for_item(access_token)
        institution_id = getattr(account_item, "institution_id", None)
        institution_name = await resolve_plaid_institution_name(
            institution_id,
            getattr(account_item, "institution_name", None),
        )
        accounts_snapshot = [build_account_snapshot(account_obj) for account_obj in accounts]
    except Exception as accounts_error:
        logging.warning(f"Plaid accounts load after exchange failed: {accounts_error}")

    connection_doc = {
        "id": connection_id,
        "user_id": user_id,
        "item_id": item_id,
        "access_token": access_token,
        "institution_id": institution_id,
        "institution_name": institution_name,
        "accounts": accounts_snapshot,
        "cursor": existing_connection.get("cursor") if existing_connection else None,
        "status": "active",
        "updated_at": now_utc,
        "created_at": existing_connection.get("created_at", now_utc) if existing_connection else now_utc,
    }

    await db.plaid_items.update_one(
        {"id": connection_id, "user_id": user_id},
        {"$set": connection_doc},
        upsert=True,
    )

    sync_summary = None
    try:
        sync_summary = await sync_single_plaid_item(
            item_doc=connection_doc,
            user_id=user_id,
            user_name=current_user.get("full_name"),
        )
    except HTTPException as sync_error:
        await db.plaid_items.update_one(
            {"id": connection_id, "user_id": user_id},
            {
                "$set": {
                    "status": "error",
                    "last_error": str(sync_error.detail),
                    "last_error_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                }
            },
        )
        raise

    latest_connection = await db.plaid_items.find_one({"id": connection_id, "user_id": user_id})
    return {
        "message": "Plaid account connected successfully.",
        "connection": serialize_connection_document(latest_connection or connection_doc),
        "sync": sync_summary,
    }

@api_router.post("/plaid/sync")
async def sync_plaid_connections(
    payload: Optional[PlaidSyncRequestBody] = None,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["id"]
    item_id = payload.item_id if payload else None
    query = {"user_id": user_id}
    if item_id:
        query["item_id"] = item_id

    plaid_items = await db.plaid_items.find(query).sort("created_at", 1).to_list(100)
    if not plaid_items:
        raise HTTPException(status_code=404, detail="No Plaid connections found.")

    sync_results = []
    sync_errors = []
    for item_doc in plaid_items:
        try:
            sync_result = await sync_single_plaid_item(
                item_doc=item_doc,
                user_id=user_id,
                user_name=current_user.get("full_name"),
            )
            sync_results.append(sync_result)
        except HTTPException as sync_error:
            sync_errors.append({
                "item_id": item_doc.get("item_id"),
                "error": str(sync_error.detail),
            })
            await db.plaid_items.update_one(
                {"id": item_doc["id"], "user_id": user_id},
                {
                    "$set": {
                        "status": "error",
                        "last_error": str(sync_error.detail),
                        "last_error_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow(),
                    }
                },
            )

    if not sync_results and sync_errors:
        raise HTTPException(status_code=502, detail=sync_errors[0]["error"])

    return {
        "synced_connections": len(sync_results),
        "errors": sync_errors,
        "total_added": sum(item.get("added_count", 0) for item in sync_results),
        "total_modified": sum(item.get("modified_count", 0) for item in sync_results),
        "total_merged": sum(item.get("merged_count", 0) for item in sync_results),
        "total_removed": sum(item.get("removed_count", 0) for item in sync_results),
        "results": sync_results,
    }

@api_router.get("/plaid/connections")
async def list_plaid_connections(user_id: str = Depends(get_current_user_id)):
    plaid_items = await db.plaid_items.find({"user_id": user_id}).sort("created_at", -1).to_list(100)
    return {
        "count": len(plaid_items),
        "items": [serialize_connection_document(item_doc) for item_doc in plaid_items],
    }

@api_router.delete("/plaid/item/{item_id}")
async def disconnect_plaid_item(
    item_id: str,
    remove_transactions: bool = False,
    user_id: str = Depends(get_current_user_id),
):
    existing_item = await db.plaid_items.find_one({"user_id": user_id, "item_id": item_id})
    if not existing_item:
        raise HTTPException(status_code=404, detail="Plaid connection not found.")

    await db.plaid_items.delete_one({"user_id": user_id, "item_id": item_id})
    removed_transaction_count = 0
    if remove_transactions:
        delete_result = await db.transactions.delete_many({
            "user_id": user_id,
            "plaid_item_id": item_id,
        })
        removed_transaction_count = delete_result.deleted_count

    return {
        "message": "Plaid connection removed.",
        "removed_transactions": removed_transaction_count,
    }

@api_router.delete("/transactions/{transaction_id}")
async def delete_transaction(transaction_id: str, user_id: str = Depends(get_current_user_id)):
    result = await db.transactions.delete_one({"id": transaction_id, "user_id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return {"message": "Transaction deleted successfully"}

class TransactionUpdate(BaseModel):
    category: Optional[str] = None
    description: Optional[str] = None
    amount: Optional[float] = None
    is_inflow: Optional[bool] = None  # NEW: Allow manual inflow/outflow override
    is_internal_transfer: Optional[bool] = None

@api_router.put("/transactions/{transaction_id}")
async def update_transaction(
    transaction_id: str, 
    transaction_update: TransactionUpdate,
    user_id: str = Depends(get_current_user_id)
):
    """Update a transaction's category, description, amount, or inflow/outflow status"""
    update_data = {}
    current_transaction = None
    
    if transaction_update.category is not None or transaction_update.description is not None:
        current_transaction = await db.transactions.find_one({"id": transaction_id, "user_id": user_id})
        if not current_transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")

    if transaction_update.description is not None:
        new_description = re.sub(r"\s+", " ", transaction_update.description.strip())
        update_data["description"] = new_description
        update_data["merchant_signature"] = build_merchant_signature(new_description)
    elif current_transaction:
        new_description = current_transaction.get("description", "")
    else:
        new_description = ""

    if transaction_update.category is not None:
        category_names, merchant_history = await load_user_category_context(user_id)
        update_data["category"] = await resolve_transaction_category(
            user_id=user_id,
            description=new_description,
            category_hint=transaction_update.category,
            category_names=category_names,
            merchant_history=merchant_history,
        )
    
    # Handle amount and inflow/outflow logic
    amount = transaction_update.amount
    is_inflow = transaction_update.is_inflow
    is_internal_transfer = transaction_update.is_internal_transfer

    if amount is not None or is_inflow is not None:
        # Get current transaction to understand current state
        if current_transaction is None:
            current_transaction = await db.transactions.find_one({"id": transaction_id, "user_id": user_id})
        if not current_transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        # Use current amount if not updating amount
        final_amount = amount if amount is not None else current_transaction.get("amount", 0)
        
        # If is_inflow is specified, apply the inflow/outflow logic
        if is_inflow is not None:
            if is_inflow and final_amount > 0:
                final_amount = -abs(final_amount)  # Make it negative for inflow
            elif not is_inflow and final_amount < 0:
                final_amount = abs(final_amount)   # Make it positive for outflow
            update_data["is_inflow"] = is_inflow
        
        update_data["amount"] = final_amount
        
        # Store original amount for reference
        if amount is not None:
            update_data["original_amount"] = amount

    if is_internal_transfer is not None:
        update_data["is_internal_transfer"] = is_internal_transfer
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No update data provided")
    
    # Add update timestamp
    update_data["updated_at"] = datetime.utcnow()
    
    result = await db.transactions.update_one(
        {"id": transaction_id, "user_id": user_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Return updated transaction
    updated_transaction = await db.transactions.find_one({"id": transaction_id, "user_id": user_id})
    if updated_transaction:
        # Remove MongoDB's _id field and convert datetime if needed
        if '_id' in updated_transaction:
            del updated_transaction['_id']
        if 'created_at' in updated_transaction and hasattr(updated_transaction['created_at'], 'isoformat'):
            updated_transaction['created_at'] = updated_transaction['created_at'].isoformat()
        if 'updated_at' in updated_transaction and hasattr(updated_transaction['updated_at'], 'isoformat'):
            updated_transaction['updated_at'] = updated_transaction['updated_at'].isoformat()
        return updated_transaction
    else:
        raise HTTPException(status_code=404, detail="Updated transaction not found")

@api_router.post("/transactions/recategorize")
async def recategorize_transactions(user_id: str = Depends(get_current_user_id)):
    """Re-run smart categorization across a user's existing transactions."""
    await initialize_default_categories(user_id)
    category_docs = await db.categories.find({"user_id": user_id}, {"name": 1, "is_default": 1}).to_list(200)
    category_names = [category["name"] for category in category_docs if category.get("name")]
    custom_category_names = {
        category["name"]
        for category in category_docs
        if category.get("name") and not category.get("is_default")
    }

    transactions = await db.transactions.find({"user_id": user_id}).sort("created_at", 1).to_list(5000)
    merchant_history: Dict[str, Counter] = defaultdict(Counter)
    updated_count = 0

    for transaction in transactions:
        description = re.sub(r"\s+", " ", str(transaction.get("description", "")).strip())
        current_category = transaction.get("category")
        category_hint = current_category if current_category in custom_category_names else None
        merchant_signature = build_merchant_signature(description)

        resolved_category = infer_category_from_context(
            description=description,
            category_hint=category_hint,
            available_categories=category_names,
            merchant_history=merchant_history,
        )

        if (
            transaction.get("description") != description
            or transaction.get("category") != resolved_category
            or transaction.get("merchant_signature") != merchant_signature
        ):
            await db.transactions.update_one(
                {"id": transaction["id"], "user_id": user_id},
                {
                    "$set": {
                        "description": description,
                        "category": resolved_category,
                        "merchant_signature": merchant_signature,
                        "updated_at": datetime.utcnow(),
                    }
                }
            )
            updated_count += 1

        if merchant_signature:
            merchant_history[merchant_signature][resolved_category] += 1

    return {
        "message": f"Re-categorized {updated_count} transactions",
        "updated_count": updated_count,
        "total_transactions": len(transactions),
    }

class BulkDeleteRequest(BaseModel):
    transaction_ids: List[str]

@api_router.post("/transactions/bulk-delete")
async def bulk_delete_transactions(
    request: BulkDeleteRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Delete multiple transactions at once"""
    if not request.transaction_ids:
        raise HTTPException(status_code=400, detail="No transaction IDs provided")
    
    result = await db.transactions.delete_many({
        "id": {"$in": request.transaction_ids}, 
        "user_id": user_id
    })
    
    return {
        "message": f"Successfully deleted {result.deleted_count} transactions",
        "deleted_count": result.deleted_count
    }

# Subscription Management Endpoints
@api_router.get("/subscriptions")
async def get_subscriptions(
    current_user: dict = Depends(get_current_user),
    view_user_id: str = Depends(get_view_user_id),
):
    """Get all subscriptions for the current user."""
    view_filter = await build_view_filter(current_user, view_user_id)
    subscriptions = await db.subscriptions.find(view_filter).sort("name", 1).to_list(200)
    return subscriptions

@api_router.post("/subscriptions")
async def create_subscription(
    subscription: SubscriptionCreate,
    user_id: str = Depends(get_current_user_id)
):
    """Create a new subscription."""
    sub_doc = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "name": subscription.name,
        "amount": subscription.amount,
        "currency": "CAD",
        "billing_cycle": subscription.billing_cycle,
        "next_billing_date": subscription.next_billing_date,
        "category": subscription.category,
        "status": "active",
        "notes": subscription.notes,
        "created_at": datetime.utcnow(),
    }
    await db.subscriptions.insert_one(sub_doc)
    return {"message": "Subscription created", "id": sub_doc["id"]}

@api_router.put("/subscriptions/{subscription_id}")
async def update_subscription(
    subscription_id: str,
    updates: SubscriptionUpdate,
    user_id: str = Depends(get_current_user_id)
):
    """Update a subscription."""
    update_data = {k: v for k, v in updates.dict().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    update_data["updated_at"] = datetime.utcnow()
    result = await db.subscriptions.update_one(
        {"id": subscription_id, "user_id": user_id},
        {"$set": update_data}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return {"message": "Subscription updated"}

@api_router.delete("/subscriptions/{subscription_id}")
async def delete_subscription(
    subscription_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Delete a subscription."""
    result = await db.subscriptions.delete_one({"id": subscription_id, "user_id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return {"message": "Subscription deleted"}

@api_router.get("/subscriptions/summary")
async def get_subscription_summary(
    current_user: dict = Depends(get_current_user),
    view_user_id: str = Depends(get_view_user_id),
):
    """Get subscription spending summary."""
    view_filter = await build_view_filter(current_user, view_user_id)
    summary_filter = {**view_filter, "status": "active"}
    subscriptions = await db.subscriptions.find(summary_filter).to_list(200)
    monthly_total = 0.0
    yearly_total = 0.0
    for sub in subscriptions:
        amt = sub.get("amount", 0)
        cycle = sub.get("billing_cycle", "monthly")
        if cycle == "monthly":
            monthly_total += amt
            yearly_total += amt * 12
        elif cycle == "yearly":
            monthly_total += amt / 12
            yearly_total += amt
        elif cycle == "weekly":
            monthly_total += amt * 4.33
            yearly_total += amt * 52
    return {
        "active_count": len(subscriptions),
        "monthly_total": round(monthly_total, 2),
        "yearly_total": round(yearly_total, 2),
    }

# Excel Export Endpoint
@api_router.get("/transactions/export/excel")
async def export_transactions_to_excel(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category: Optional[str] = None,
    pdf_source: Optional[str] = None,
    account_type: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    view_user_id: str = Depends(get_view_user_id),
):
    """Export transactions to Excel file with filters"""
    # Use the same filtering logic as get_transactions
    filter_dict = await build_view_filter(current_user, view_user_id)
    
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
    if account_type:
        filter_dict["account_type"] = account_type
    
    # Get transactions sorted by date (newest first)
    transactions = await db.transactions.find(filter_dict).sort("date", -1).to_list(10000)
    
    if not transactions:
        raise HTTPException(status_code=404, detail="No transactions found for export")
    
    # Create Excel workbook
    wb = Workbook()
    
    # Main transactions sheet
    ws_main = wb.active
    ws_main.title = "Transactions"
    
    # Convert transactions to DataFrame for easier manipulation
    df_data = []
    for transaction in transactions:
        df_data.append({
            'Date': transaction.get('date', ''),
            'Description': transaction.get('description', ''),
            'Category': transaction.get('category', ''),
            'Amount': transaction.get('amount', 0),
            'Account Type': 'Credit Card' if transaction.get('account_type') == 'credit_card' else 'Debit Account',
            'Source': transaction.get('pdf_source', 'Manual'),
            'User': transaction.get('user_name', '')
        })
    
    df = pd.DataFrame(df_data)
    
    # Add headers with styling
    headers = ['Date', 'Description', 'Category', 'Amount', 'Account Type', 'Source', 'User']
    for col_num, header in enumerate(headers, 1):
        cell = ws_main.cell(row=1, column=col_num, value=header)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        cell.alignment = Alignment(horizontal="center")
    
    # Add data rows
    for row_num, (_, row_data) in enumerate(df.iterrows(), 2):
        for col_num, value in enumerate(row_data, 1):
            cell = ws_main.cell(row=row_num, column=col_num, value=value)
            if col_num == 4:  # Amount column
                cell.number_format = '"$"#,##0.00'
    
    # Auto-adjust column widths
    for column in ws_main.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 50)
        ws_main.column_dimensions[column_letter].width = adjusted_width
    
    # Create summary sheet
    ws_summary = wb.create_sheet("Summary")
    
    # Summary statistics
    total_amount = df['Amount'].sum()
    transaction_count = len(df)
    date_range = f"{df['Date'].min()} to {df['Date'].max()}" if not df.empty else "No data"
    
    # Category breakdown
    category_summary = df.groupby('Category')['Amount'].agg(['count', 'sum']).reset_index()
    
    # Account type breakdown
    account_summary = df.groupby('Account Type')['Amount'].agg(['count', 'sum']).reset_index()
    
    # Add summary data
    summary_data = [
        ["Export Summary", ""],
        ["Total Transactions", transaction_count],
        ["Total Amount", f"${total_amount:,.2f}"],
        ["Date Range", date_range],
        ["Export Date", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        ["", ""],
        ["Category Breakdown", ""],
        ["Category", "Count", "Total Amount"]
    ]
    
    # Add category data
    for _, row in category_summary.iterrows():
        summary_data.append([row['Category'], row['count'], f"${row['sum']:,.2f}"])
    
    summary_data.extend([
        ["", ""],
        ["Account Type Breakdown", ""],
        ["Account Type", "Count", "Total Amount"]
    ])
    
    # Add account type data
    for _, row in account_summary.iterrows():
        summary_data.append([row['Account Type'], row['count'], f"${row['sum']:,.2f}"])
    
    # Write summary data
    for row_num, row_data in enumerate(summary_data, 1):
        for col_num, value in enumerate(row_data, 1):
            cell = ws_summary.cell(row=row_num, column=col_num, value=value)
            if row_num == 1 or (len(row_data) > 2 and value in ["Category Breakdown", "Account Type Breakdown"]):
                cell.font = Font(bold=True)
    
    # Auto-adjust summary column widths
    for column in ws_summary.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 30)
        ws_summary.column_dimensions[column_letter].width = adjusted_width
    
    # Save to BytesIO
    excel_buffer = io.BytesIO()
    wb.save(excel_buffer)
    excel_buffer.seek(0)
    
    # Generate filename
    filename = f"lifetracker_transactions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    # Return as streaming response
    return StreamingResponse(
        io.BytesIO(excel_buffer.getvalue()),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

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

        # Extract structured PDF content once and reuse it for parsing and previews.
        pdf_document = extract_pdf_document(content)
        text = pdf_document.get("text", "")
        
        if not text.strip():
            if pdf_document.get("ocr_needed"):
                if not OCR_RUNTIME_AVAILABLE:
                    raise HTTPException(
                        status_code=400,
                        detail="This PDF appears to be image-only. OCR support is not installed on the server."
                    )
                raise HTTPException(
                    status_code=400,
                    detail="This PDF appears to be image-only and OCR could not recover readable text."
                )
            raise HTTPException(status_code=400, detail="Could not extract text from PDF")
        
        parsed_transactions = parse_transactions_from_pdf_document(pdf_document, user_id, file.filename)
        
        if not parsed_transactions:
            return {
                "message": "No transactions found in PDF", 
                "imported_count": 0,
                "extracted_text_preview": text[:500] + "..." if len(text) > 500 else text
            }

        category_names, merchant_history = await load_user_category_context(user_id)
        prepared_transactions = []
        for trans_data in parsed_transactions:
            clean_description = re.sub(r"\s+", " ", str(trans_data.get("description", "")).strip())
            resolved_category = await resolve_transaction_category(
                user_id=user_id,
                description=clean_description,
                category_hint=trans_data.get("category"),
                category_names=category_names,
                merchant_history=merchant_history,
            )
            merchant_signature = build_merchant_signature(clean_description)

            trans_data["description"] = clean_description
            trans_data["category"] = resolved_category
            trans_data["merchant_signature"] = merchant_signature
            prepared_transactions.append(trans_data)

            if merchant_signature:
                merchant_history[merchant_signature][resolved_category] += 1
        
        # Check for duplicates and insert new transactions
        new_transactions = []
        duplicate_count = 0
        
        for trans_data in prepared_transactions:
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
            "source_file": file.filename,
            "ocr_used": bool(pdf_document.get("ocr_used")),
            "ocr_needed": bool(pdf_document.get("ocr_needed")),
            "extraction_method": pdf_document.get("method"),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"PDF processing error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")

# LLM-powered categorization
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

CATEGORIZATION_SYSTEM_PROMPT = """You are a Canadian personal finance categorization engine for a banking dashboard.
You categorize bank transactions from Canadian institutions (ATB, RBC, CIBC, TD, BMO, Scotiabank) into predefined categories.

## Category Definitions

- **Retail and Grocery**: Supermarkets, grocery stores ONLY. Costco, Walmart, Safeway, FreshCo, Dollarama, No Frills, Loblaws, Superstore. Does NOT include Amazon/AMZN (that goes to Personal and Household Expenses unless clearly grocery). Does NOT include SHEIN (that's Personal and Household Expenses — clothing).
- **Restaurants**: Restaurants, fast food, cafes, coffee shops, food delivery. Tim Hortons, Subway, Skip the Dishes, DoorDash, UberEats food orders.
- **Transportation**: Gas stations (Petro-Canada, Shell, Esso), Uber/Lyft rides, transit passes, parking, car washes, vehicle fuel. Note: "UBER CANADA/UBE" is ride-hailing, not food.
- **Home and Office Improvement**: Home Depot, Canadian Tire (hardware), furniture, office supplies, home renovation, Best Buy electronics.
- **Hotel, Entertainment and Recreation**: Hotels, Airbnb, movie theaters, streaming services (Netflix, Spotify, Disney+, Apple), gyms, sports, concerts, recreation.
- **Transfers and Payments**: Interac e-Transfers (sent and received), bank transfers, wire transfers, bill payments, "FULFILL REQUEST", "E-TRANSFER", "INTERNET TRANSFER". These are money movements, not purchases.
- **Income and Payroll**: Payroll deposits, salary, employer payments. Descriptions starting with "PAY" followed by a company name, "Direct Deposit Payroll", any payroll service (Humi, ADP, Ceridian, etc.), tax refunds, group health/benefits deposits. These are always inflows.
- **Banking Fees and ATM**: ATM withdrawals, ATM fees, monthly service charges, NSF fees, "NETWORK TRANSACTION FEE", "SERVICE CHARGE", "RECORD-KEEPING". ATM cash withdrawals go here, not Transfers.
- **Insurance and Financial Products**: Insurance premiums (Intact, Manulife, Sun Life), loan payments, mortgage payments, "PREAUTHORIZED DEBIT" to insurance companies.
- **Investments and Brokerage**: Wealthsimple, Questrade, RRSP/TFSA contributions, investment purchases, brokerage transactions.
- **Professional and Financial Services**: Software subscriptions (Adobe, GitHub, ChatGPT, Notion, Canva), professional tools, accounting software, SaaS products, Google services.
- **Health and Education**: Pharmacies (Shoppers Drug Mart), medical, dental, tuition, textbooks, courses, health-related purchases.
- **Foreign Currency Transactions**: Any transaction with foreign currency indicators, international purchases, forex fees.
- **Personal and Household Expenses**: Telecom (Telus, Bell, Rogers), personal care, clothing (SHEIN, H&M), Amazon/AMZN purchases (general online shopping), pet expenses, auction houses, specialty retailers, miscellaneous personal spending that doesn't fit other categories.

## Canadian Banking Patterns
- "VISA DEBIT RETAIL PURCHASE" or "VISA DEBIT PURCHASE" = debit card purchase at the merchant named after it
- "PREAUTHORIZED DEBIT" = automatic recurring payment (check the company name for category)
- "E-TRANSFER" / "INTERAC e-Transfer" = person-to-person money transfer → Transfers and Payments
- "FULFILL REQUEST" = Interac e-Transfer request fulfilled → Transfers and Payments
- "INTERNET TRANSFER" = online banking transfer between accounts → Transfers and Payments
- "DEPOSIT" followed by GROUPHEALTH = insurance/benefits deposit → Income and Payroll
- "PAY" at the start = employer payroll → Income and Payroll
- "CORRECTION" = reversal of a previous transaction — categorize same as the original
- "MDSE RETURN" / "CREDIT MEMO" / "PURCHASE REVERSAL" = refund — categorize same as original purchase type
- Amounts: negative = inflow (money received), positive = outflow (money spent)

## Examples of Tricky Categorizations
- "VISA DEBIT RETAIL PURCHASE UBER CANADA/UBE 609014211368" → Transportation (ride, not food)
- "VISA DEBIT RETAIL PURCHASE GOOGLE *Google 608004594592" → Professional and Financial Services (Google subscription)
- "ATM WITHDRAWAL INTERAC/RBC SCD 0003" → Banking Fees and ATM (cash withdrawal)
- "PREAUTHORIZED DEBIT INTACT INSURANCE COMPANY" → Insurance and Financial Products
- "PAY [number] [Province] [Company] Ltd o/a [Employer]" → Income and Payroll (employer payroll)
- "DEPOSIT Rembours. d'impôt/Tax Refund" → Income and Payroll
- "FULFILL REQUEST [number] [Person Name]" → Transfers and Payments
- "PREAUTHORIZED DEBIT Telus Mobility" → Personal and Household Expenses (telecom)
- "VISA DEBIT RETAIL PURCHASE Wealthsimple 533910598194" → Investments and Brokerage
- "CORRECTION UBER CANADA/UBE 609008110561" → Transportation (reversal of ride charge)
- "RETAIL PURCHASE [num] [AUCTION HOUSE]" → Personal and Household Expenses (auction purchase)
- "VISA DEBIT RETAIL PURCHASE AMZN Mktp CA [num]" → Personal and Household Expenses (Amazon online shopping, not grocery)
- "VISA DEBIT RETAIL PURCHASE Amazon.ca [num]" → Personal and Household Expenses (Amazon, not grocery)
- "VISA DEBIT RETAIL PURCHASE SHEIN [num]" → Personal and Household Expenses (clothing)
- "RETAIL PURCHASE [num] SAFEWAY #[num]" → Retail and Grocery (grocery store)
- "RETAIL PURCHASE [num] COSTCO WHOLESAL" → Retail and Grocery (grocery/warehouse store)
- "RETAIL PURCHASE [num] [RESTAURANT NAME]" → Restaurants (restaurant/pub/cafe)
- "RETAIL PURCHASE [num] FRESHCO #[num]" → Retail and Grocery (grocery store)
- "RETAIL PURCHASE [num] COSTCO GAS [loc]" → Transportation (fuel purchase, not grocery)
- "RETAIL PURCHASE [num] [CAR WASH]" → Transportation (vehicle maintenance)
- "[LOAN/PRINCIPAL] Payment Transfer To [acct]" → Insurance and Financial Products (not banking fee)

Respond with ONLY valid JSON. No markdown, no explanation, no code blocks."""

def get_anthropic_client():
    """Get a reusable Anthropic client."""
    if not ANTHROPIC_API_KEY:
        return None
    return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

async def llm_categorize_transactions(transactions: list, available_categories: list) -> dict:
    """Use Claude to categorize a batch of transaction descriptions."""
    client = get_anthropic_client()
    if not client:
        return {}

    categories_str = ", ".join(available_categories)

    descriptions = []
    for i, t in enumerate(transactions):
        desc = t.get("description", "")
        amount = t.get("amount", 0)
        flow = "inflow" if amount < 0 else "outflow"
        descriptions.append(f"{i}: {desc} (${abs(amount):.2f}, {flow})")

    user_prompt = f"""Categorize each transaction into one of: {categories_str}

{chr(10).join(descriptions)}

Return JSON mapping index to category name. Example: {{"0": "Retail and Grocery", "1": "Transportation"}}"""

    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2048,
            system=CATEGORIZATION_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}]
        )
        response_text = message.content[0].text.strip()
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        result = json.loads(response_text)
        return {int(k): v for k, v in result.items() if v in available_categories}
    except Exception as e:
        logging.error(f"LLM categorization error: {e}")
        return {}


async def llm_generate_insights(transactions: list, existing_insight_texts: list = None, format_currency=None) -> dict:
    """Generate smart spending insights using Claude."""
    client = get_anthropic_client()
    if not client or not transactions:
        return {"insights": [], "anomalies": []}

    # Ignore matched internal transfer pairs so they don't inflate spending insights.
    internal_transfer_ids = detect_internal_transfer_transaction_ids(transactions)
    scoped_transactions = [
        transaction for transaction in transactions
        if transaction.get("id") not in internal_transfer_ids
    ]
    if not scoped_transactions:
        return {"insights": [], "anomalies": []}

    # Build a spending summary for the LLM
    from collections import Counter as Ctr
    cat_outflows = defaultdict(float)
    cat_outflow_counts = defaultdict(int)
    cat_inflows = defaultdict(float)
    cat_inflow_counts = defaultdict(int)
    monthly_outflows = defaultdict(float)
    monthly_inflows = defaultdict(float)
    total_outflow = 0.0
    total_inflow = 0.0
    recent_transactions = []

    for t in scoped_transactions:
        amt = float(t.get("amount", 0))
        cat = t.get("category", "Unknown")
        date_str = str(t.get("date", ""))
        month_key = date_str[:7] if len(date_str) >= 7 else "unknown"

        if amt > 0:  # outflow (money spent)
            cat_outflows[cat] += amt
            cat_outflow_counts[cat] += 1
            monthly_outflows[month_key] += amt
            total_outflow += amt
        else:  # inflow (money received)
            cat_inflows[cat] += abs(amt)
            cat_inflow_counts[cat] += 1
            monthly_inflows[month_key] += abs(amt)
            total_inflow += abs(amt)

    # Get last 50 transactions for anomaly detection
    sorted_trans = sorted(scoped_transactions, key=lambda x: str(x.get("date", "")), reverse=True)[:50]
    for t in sorted_trans:
        amt = float(t.get("amount", 0))
        if amt < 0:
            flow_label = "RECEIVED (money IN)"
            display_amount = f"+${abs(amt):.2f}"
        else:
            flow_label = "SPENT (money OUT)"
            display_amount = f"-${amt:.2f}"
        recent_transactions.append({
            "date": str(t.get("date", "")),
            "description": t.get("description", "")[:50],
            "display_amount": display_amount,
            "direction": flow_label,
            "category": t.get("category", ""),
        })

    # Build outflow summary
    outflow_summary = []
    for cat, total in sorted(cat_outflows.items(), key=lambda x: -x[1]):
        pct = (total / total_outflow * 100) if total_outflow > 0 else 0
        outflow_summary.append(f"- {cat}: ${total:.2f} ({cat_outflow_counts[cat]} tx, {pct:.1f}%)")

    # Build inflow summary
    inflow_summary = []
    for cat, total in sorted(cat_inflows.items(), key=lambda x: -x[1]):
        inflow_summary.append(f"- {cat}: ${total:.2f} ({cat_inflow_counts[cat]} tx)")

    # Monthly trend
    monthly_summary = []
    for month in sorted(set(list(monthly_outflows.keys()) + list(monthly_inflows.keys()))):
        out = monthly_outflows.get(month, 0)
        inc = monthly_inflows.get(month, 0)
        monthly_summary.append(f"- {month}: spent ${out:.2f}, received ${inc:.2f}, net ${inc - out:.2f}")

    prompt = f"""Analyze this Canadian user's banking data and provide insights.

IMPORTANT: Amounts > 0 are OUTFLOWS (money spent). Amounts < 0 are INFLOWS (money received).
Total outflows (spending): ${total_outflow:.2f}
Total inflows (income): ${total_inflow:.2f}
Net: ${total_inflow - total_outflow:.2f}

## OUTFLOWS by Category (money SPENT — use these numbers for spending analysis)
{chr(10).join(outflow_summary) if outflow_summary else "No spending data"}

## INFLOWS by Category (money RECEIVED — income, refunds, deposits)
{chr(10).join(inflow_summary) if inflow_summary else "No income data"}

## Monthly Breakdown (spending vs income)
{chr(10).join(monthly_summary[-6:]) if monthly_summary else "No monthly data"}

## Recent Transactions (last 50, "direction" field shows money flow)
{json.dumps(recent_transactions, indent=2)}

## ALREADY TRACKED INSIGHTS (do NOT repeat these — generate only NEW observations)
{chr(10).join(f'- {t}' for t in (existing_insight_texts or [])[:20]) if existing_insight_texts else 'None yet'}

Provide a JSON response with ONLY genuinely new insights not covered above:
1. "insights": Array of 3-5 objects, each with:
   - "text": Short insight (~20 words max), specific with dollar amounts
   - "search_query": A natural language query to find the related transactions (e.g. "Uber rides", "ATM withdrawals", "Amazon purchases")
   - "category_hint": The main category this insight relates to, or null
   - "fixable": boolean, true if the insight suggests a categorization problem that AI could fix
2. "anomalies": Array of 0-3 unusual transactions with {{"description": "...", "reason": "...", "amount": ...}}. Only flag genuinely unusual amounts or patterns. Empty array if nothing unusual.

Return ONLY valid JSON, no markdown or explanation."""

    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system="""You are a concise Canadian personal finance analyst. Analyze spending patterns and flag anomalies. Be specific with dollar amounts and percentages. No fluff.

CRITICAL RULES:
- Canadian banks often show BOTH sides of an internal account transfer (e.g. internet transfer OUT and e-transfer IN same day, same amount). This is normal — do NOT flag as suspicious, money laundering, or pass-through.
- E-transfers between the user's own accounts or to/from family members are routine, not anomalies.
- Same-day matching in/out amounts are inter-account transfers (e.g. line of credit draw + payment). Normal banking.
- Only flag genuinely unusual spending: amounts 5x+ above category average, or sudden spikes in a category.
- Never make accusations or use alarming language (money laundering, fraud, suspicious). Be professional and helpful.
- Focus on actionable savings opportunities and spending optimization.""",
            messages=[{"role": "user", "content": prompt}]
        )
        response_text = message.content[0].text.strip()
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        return json.loads(response_text)
    except Exception as e:
        logging.error(f"LLM insights error: {e}")
        return {"insights": [], "anomalies": []}


async def llm_detect_subscriptions(transactions: list, existing_subs: list) -> list:
    """Detect recurring subscriptions from transaction history."""
    client = get_anthropic_client()
    if not client or not transactions:
        return []

    # Find potential recurring transactions (same description, multiple months)
    desc_occurrences = defaultdict(list)
    for t in transactions:
        desc = t.get("description", "")
        # Normalize: strip transaction IDs and numbers at end
        clean_desc = re.sub(r'\s+\d{6,}.*$', '', desc).strip()
        clean_desc = re.sub(r'\s+\*\d+$', '', clean_desc).strip()
        if float(t.get("amount", 0)) > 0:  # outflows only
            desc_occurrences[clean_desc].append({
                "date": str(t.get("date", "")),
                "amount": t.get("amount", 0),
                "description": desc[:60]
            })

    # Filter to descriptions that appear 2+ times
    recurring_candidates = []
    for desc, occurrences in desc_occurrences.items():
        if len(occurrences) >= 2:
            amounts = [o["amount"] for o in occurrences]
            avg_amount = sum(amounts) / len(amounts)
            # Check if amounts are consistent (within 20%)
            if all(abs(a - avg_amount) / avg_amount < 0.2 for a in amounts):
                recurring_candidates.append({
                    "description": desc[:60],
                    "occurrences": len(occurrences),
                    "avg_amount": round(avg_amount, 2),
                    "dates": [o["date"] for o in sorted(occurrences, key=lambda x: x["date"])]
                })

    if not recurring_candidates:
        return []

    existing_names = [s.get("name", "").lower() for s in existing_subs]

    prompt = f"""Analyze these recurring bank transactions and identify which ones are subscriptions or recurring bills.

## Recurring Transaction Patterns
{json.dumps(recurring_candidates, indent=2)}

## Already Tracked Subscriptions
{json.dumps(existing_names) if existing_names else "None"}

For each genuine subscription/recurring bill (NOT one-time purchases that happened to repeat, NOT e-transfers to people, NOT payroll), return a JSON array:
[{{"name": "Service Name", "amount": 12.99, "billing_cycle": "monthly", "category": "category name"}}]

Rules:
- "name" should be a clean, human-readable service name (e.g. "Telus Mobility" not "PREAUTHORIZED DEBIT Telus Mobility")
- "billing_cycle": "monthly", "yearly", or "weekly"
- Skip anything already in the tracked list
- Skip e-transfers, payroll, ATM withdrawals, one-off purchases
- Only include genuine recurring services/bills

Return ONLY valid JSON array. Empty array [] if no subscriptions found."""

    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system="You are a subscription detection engine. Identify recurring bills and subscriptions from Canadian bank transaction patterns. Be conservative — only flag clear recurring services.",
            messages=[{"role": "user", "content": prompt}]
        )
        response_text = message.content[0].text.strip()
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        return json.loads(response_text)
    except Exception as e:
        logging.error(f"LLM subscription detection error: {e}")
        return []


async def llm_search_transactions(query: str, transactions: list) -> list:
    """Natural language search over transactions using Claude."""
    client = get_anthropic_client()
    if not client or not transactions:
        return []

    # Send a sample of transaction IDs and descriptions
    trans_list = []
    for t in transactions:
        trans_list.append({
            "id": t.get("id", ""),
            "date": str(t.get("date", "")),
            "description": t.get("description", "")[:60],
            "amount": t.get("amount", 0),
            "category": t.get("category", ""),
        })

    prompt = f"""User search query: "{query}"

Here are the user's transactions:
{json.dumps(trans_list, indent=2)}

Return a JSON array of transaction IDs that match the user's query. Interpret the query naturally:
- "food spending" → restaurants + grocery
- "money I sent to family" → e-transfers to household members
- "big purchases over $500" → transactions above $500
- "what did I spend on gas" → gas station transactions
- "last paycheck" → most recent payroll deposit

Return ONLY a JSON array of matching transaction ID strings. Empty array if no matches."""

    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2048,
            system="You are a transaction search engine. Match the user's natural language query to their bank transactions. Be inclusive — return all plausible matches. Return only a JSON array of ID strings.",
            messages=[{"role": "user", "content": prompt}]
        )
        response_text = message.content[0].text.strip()
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        return json.loads(response_text)
    except Exception as e:
        logging.error(f"LLM search error: {e}")
        return []


@api_router.post("/transactions/pdf-import-stream")
async def import_transactions_from_pdf_stream(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id)
):
    """Import PDF with LLM categorization, returning progress via SSE stream."""
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    content = await file.read()

    async def event_stream():
        def send_event(data):
            return f"data: {json.dumps(data)}\n\n"

        try:
            # Step 1: Extract PDF
            yield send_event({"step": "extracting", "message": "Extracting text from PDF..."})

            pdf_document = extract_pdf_document(content)
            text = pdf_document.get("text", "")

            if not text.strip():
                yield send_event({"step": "error", "message": "Could not extract text from PDF"})
                return

            yield send_event({"step": "parsing", "message": "Parsing transactions..."})

            parsed_transactions = parse_transactions_from_pdf_document(pdf_document, user_id, file.filename)

            if not parsed_transactions:
                yield send_event({"step": "done", "message": "No transactions found in PDF", "imported_count": 0})
                return

            total = len(parsed_transactions)
            yield send_event({
                "step": "parsed",
                "message": f"Found {total} transactions",
                "total": total,
                "transactions": [
                    {"description": t.get("description", "")[:60], "amount": t.get("amount", 0), "index": i}
                    for i, t in enumerate(parsed_transactions)
                ]
            })

            # Step 2: Clean descriptions
            for t in parsed_transactions:
                t["description"] = re.sub(r"\s+", " ", str(t.get("description", "")).strip())

            # Step 3: LLM Categorization
            await initialize_default_categories(user_id)
            category_docs = await db.categories.find({"user_id": user_id}, {"name": 1}).to_list(200)
            category_names = [c["name"] for c in category_docs if c.get("name")]

            use_llm = bool(ANTHROPIC_API_KEY)
            llm_results = {}

            if use_llm:
                yield send_event({"step": "categorizing", "message": "AI is categorizing transactions...", "method": "llm"})

                # Process in batches of 20
                batch_size = 20
                for batch_start in range(0, total, batch_size):
                    batch_end = min(batch_start + batch_size, total)
                    batch = parsed_transactions[batch_start:batch_end]

                    batch_results = await llm_categorize_transactions(batch, category_names)

                    for local_idx, category in batch_results.items():
                        global_idx = batch_start + local_idx
                        llm_results[global_idx] = category
                        yield send_event({
                            "step": "categorized",
                            "index": global_idx,
                            "category": category,
                            "description": parsed_transactions[global_idx].get("description", "")[:60],
                            "progress": len(llm_results),
                            "total": total
                        })

                    # Small delay between batches
                    await asyncio.sleep(0.1)
            else:
                yield send_event({"step": "categorizing", "message": "Categorizing with rules (no API key set)...", "method": "rules"})

            # Step 4: Apply categories (LLM results + rule fallback)
            _, merchant_history = await load_user_category_context(user_id)

            for i, trans_data in enumerate(parsed_transactions):
                if i in llm_results:
                    trans_data["category"] = llm_results[i]
                else:
                    resolved_category = infer_category_from_context(
                        description=trans_data["description"],
                        category_hint=trans_data.get("category"),
                        available_categories=category_names,
                        merchant_history=merchant_history,
                    )
                    trans_data["category"] = resolved_category

                    if not use_llm:
                        yield send_event({
                            "step": "categorized",
                            "index": i,
                            "category": resolved_category,
                            "description": trans_data["description"][:60],
                            "progress": i + 1,
                            "total": total
                        })

                trans_data["merchant_signature"] = build_merchant_signature(trans_data["description"])
                sig = trans_data["merchant_signature"]
                if sig:
                    merchant_history[sig][trans_data["category"]] += 1

            # Step 5: Deduplicate and insert
            yield send_event({"step": "saving", "message": "Checking for duplicates and saving..."})

            new_transactions = []
            duplicate_count = 0

            for trans_data in parsed_transactions:
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

            if new_transactions:
                await db.transactions.insert_many(new_transactions)

            yield send_event({
                "step": "done",
                "message": f"Imported {len(new_transactions)} transactions ({duplicate_count} duplicates skipped)",
                "imported_count": len(new_transactions),
                "duplicate_count": duplicate_count,
                "total_found": total,
                "method": "llm" if use_llm else "rules"
            })

        except Exception as e:
            logging.error(f"Streaming PDF import error: {e}")
            yield send_event({"step": "error", "message": str(e)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )

# LLM-powered API endpoints
@api_router.get("/ai/insights")
async def get_ai_insights(
    current_user: dict = Depends(get_current_user),
    view_user_id: str = Depends(get_view_user_id),
):
    """Get all insights for this user -- the full append-only log."""
    scope_filter = build_ai_scope_filter(current_user, view_user_id)
    items = await db.ai_insight_items.find(scope_filter).sort("created_at", -1).to_list(200)
    for item in items:
        item.pop("_id", None)
    return {"items": items}

def extract_dedup_keywords(text: str) -> set:
    """Extract significant keywords for deduplication."""
    stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'in', 'on', 'at', 'to', 'for', 'of', 'and', 'or', 'your', 'you', 'this', 'that', 'with', 'from', 'by', 'as', 'it', 'be', 'has', 'have', 'had', 'not', 'but', 'if', 'its', 'per', 'vs', 'than'}
    words = re.sub(r'[^a-z0-9\s]', '', text.lower()).split()
    return {w for w in words if w not in stop_words and len(w) > 2}

def is_duplicate_insight(new_text: str, existing_texts: list) -> bool:
    """Check if a new insight is semantically similar to any existing one."""
    new_keywords = extract_dedup_keywords(new_text)
    if not new_keywords:
        return False
    for existing_text in existing_texts:
        existing_keywords = extract_dedup_keywords(existing_text)
        if not existing_keywords:
            continue
        overlap = len(new_keywords & existing_keywords)
        smaller = min(len(new_keywords), len(existing_keywords))
        if smaller > 0 and overlap / smaller >= 0.5:
            return True
    return False

@api_router.post("/ai/insights/generate")
async def generate_new_insights(
    current_user: dict = Depends(get_current_user),
    view_user_id: str = Depends(get_view_user_id),
):
    """Generate NEW insights and append them to the log. Does not replace old ones."""
    scope_id = get_ai_scope_id(current_user, view_user_id)
    scope_filter = build_ai_scope_filter(current_user, view_user_id)
    view_filter = await build_view_filter(current_user, view_user_id)

    # Get existing insights to pass to LLM and for dedup
    existing = await db.ai_insight_items.find(scope_filter, {"text": 1, "status": 1}).to_list(500)
    existing_texts = [item.get("text", "") for item in existing if item.get("text")]

    transactions = await db.transactions.find(view_filter).sort("date", -1).to_list(500)
    result = await llm_generate_insights(transactions, existing_texts)

    new_items = []
    now = datetime.utcnow()

    for i, insight in enumerate(result.get("insights", [])):
        if isinstance(insight, str):
            insight = {"text": insight}
        # Smart keyword-based dedup
        if is_duplicate_insight(insight.get("text", ""), existing_texts):
            continue
        item = {
            "id": f"insight_{scope_id.replace(':', '_')}_{int(now.timestamp())}_{i}",
            "user_id": current_user["id"],
            "scope_id": scope_id,
            "type": "insight",
            "text": insight.get("text", ""),
            "search_query": insight.get("search_query"),
            "category_hint": insight.get("category_hint"),
            "fixable": insight.get("fixable", False),
            "status": "open",
            "notes": None,
            "created_at": now,
        }
        new_items.append(item)

    for i, anomaly in enumerate(result.get("anomalies", [])):
        desc = anomaly.get("description", "")
        if is_duplicate_insight(desc, existing_texts):
            continue
        item = {
            "id": f"anomaly_{scope_id.replace(':', '_')}_{int(now.timestamp())}_{i}",
            "user_id": current_user["id"],
            "scope_id": scope_id,
            "type": "anomaly",
            "text": desc,
            "reason": anomaly.get("reason", ""),
            "amount": anomaly.get("amount"),
            "status": "open",
            "notes": None,
            "created_at": now,
        }
        new_items.append(item)

    if new_items:
        await db.ai_insight_items.insert_many(new_items)

    return {"added": len(new_items), "message": f"Added {len(new_items)} new insights"}

@api_router.get("/ai/insights/month/{month_key}")
async def get_month_insights(
    month_key: str,
    current_user: dict = Depends(get_current_user),
    view_user_id: str = Depends(get_view_user_id),
):
    """Get insights for a specific month. Returns cached or generates new."""
    scope_filter = build_ai_scope_filter(current_user, view_user_id)
    # Check for existing
    items = await db.ai_insight_items.find({"$and": [scope_filter, {"month": month_key}]}).sort("created_at", -1).to_list(50)
    if items:
        for item in items:
            item.pop("_id", None)
        return {"items": items, "month": month_key}
    return {"items": [], "month": month_key}

@api_router.post("/ai/insights/month/{month_key}/generate")
async def generate_month_insights(
    month_key: str,
    current_user: dict = Depends(get_current_user),
    view_user_id: str = Depends(get_view_user_id),
):
    """Generate insights scoped to a specific month."""
    scope_id = get_ai_scope_id(current_user, view_user_id)
    scope_filter = build_ai_scope_filter(current_user, view_user_id)
    view_filter = await build_view_filter(current_user, view_user_id)

    start_date = f"{month_key}-01"
    # Calculate end of month
    year, month = int(month_key[:4]), int(month_key[5:7])
    if month == 12:
        end_date = f"{year + 1}-01-01"
    else:
        end_date = f"{year}-{month + 1:02d}-01"

    transactions_filter = {
        **view_filter,
        "date": {"$gte": start_date, "$lt": end_date}
    }
    transactions = await db.transactions.find(transactions_filter).sort("date", -1).to_list(500)

    if not transactions:
        return {"added": 0, "message": "No transactions for this month"}

    existing = await db.ai_insight_items.find(
        {"$and": [scope_filter, {"month": month_key}]},
        {"text": 1}
    ).to_list(100)
    existing_texts = [item.get("text", "") for item in existing]

    result = await llm_generate_insights(transactions, existing_texts)

    new_items = []
    now = datetime.utcnow()

    for i, insight in enumerate(result.get("insights", [])):
        if isinstance(insight, str):
            insight = {"text": insight}
        if is_duplicate_insight(insight.get("text", ""), existing_texts):
            continue
        item = {
            "id": f"insight_{scope_id.replace(':', '_')}_{month_key}_{int(now.timestamp())}_{i}",
            "user_id": current_user["id"],
            "scope_id": scope_id,
            "month": month_key,
            "type": "insight",
            "text": insight.get("text", ""),
            "search_query": insight.get("search_query"),
            "category_hint": insight.get("category_hint"),
            "fixable": insight.get("fixable", False),
            "status": "open",
            "notes": None,
            "created_at": now,
        }
        new_items.append(item)

    for i, anomaly in enumerate(result.get("anomalies", [])):
        desc = anomaly.get("description", "")
        if is_duplicate_insight(desc, existing_texts):
            continue
        item = {
            "id": f"anomaly_{scope_id.replace(':', '_')}_{month_key}_{int(now.timestamp())}_{i}",
            "user_id": current_user["id"],
            "scope_id": scope_id,
            "month": month_key,
            "type": "anomaly",
            "text": desc,
            "reason": anomaly.get("reason", ""),
            "amount": anomaly.get("amount"),
            "status": "open",
            "notes": None,
            "created_at": now,
        }
        new_items.append(item)

    if new_items:
        await db.ai_insight_items.insert_many(new_items)

    return {"added": len(new_items), "message": f"Added {len(new_items)} insights for {month_key}"}

@api_router.post("/ai/insights/update-status")
async def update_insight_status(
    request: dict,
    current_user: dict = Depends(get_current_user),
    view_user_id: str = Depends(get_view_user_id),
):
    """Update the status of an insight item."""
    scope_filter = build_ai_scope_filter(current_user, view_user_id)
    insight_id = request.get("insight_id", "")
    new_status = request.get("status", "")
    notes = request.get("notes", None)

    if new_status not in ("open", "addressed", "dismissed"):
        raise HTTPException(status_code=400, detail="Invalid status")

    update_fields = {"status": new_status}
    if notes is not None:
        update_fields["notes"] = notes

    result = await db.ai_insight_items.update_one(
        {"$and": [scope_filter, {"id": insight_id}]},
        {"$set": update_fields}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Insight not found")
    return {"message": "Status updated"}

@api_router.get("/ai/detect-subscriptions")
async def detect_subscriptions(
    current_user: dict = Depends(get_current_user),
    view_user_id: str = Depends(get_view_user_id),
):
    """Auto-detect subscriptions from transaction history."""
    view_filter = await build_view_filter(current_user, view_user_id)
    transactions = await db.transactions.find(view_filter).sort("date", -1).to_list(1000)
    existing_subs = await db.subscriptions.find(view_filter).to_list(100)
    detected = await llm_detect_subscriptions(transactions, existing_subs)
    return {"detected": detected}

@api_router.post("/ai/detect-subscriptions/save")
async def save_detected_subscriptions(
    subscriptions: list,
    current_user: dict = Depends(get_current_user),
    view_user_id: str = Depends(get_view_user_id),
):
    """Save detected subscriptions."""
    if view_user_id == "family_view":
        raise HTTPException(
            status_code=400,
            detail="Switch to a personal/member view to save subscriptions."
        )

    target_user_id = view_user_id or current_user["id"]

    saved = []
    for sub in subscriptions:
        sub_doc = {
            "id": str(uuid.uuid4()),
            "user_id": target_user_id,
            "name": sub.get("name", "Unknown"),
            "amount": float(sub.get("amount", 0)),
            "currency": "CAD",
            "billing_cycle": sub.get("billing_cycle", "monthly"),
            "next_billing_date": None,
            "category": sub.get("category", "Personal and Household Expenses"),
            "status": "active",
            "notes": "Auto-detected by AI",
            "created_at": datetime.utcnow(),
        }
        await db.subscriptions.insert_one(sub_doc)
        saved.append(sub_doc["name"])
    return {"message": f"Saved {len(saved)} subscriptions", "saved": saved}

async def llm_categorize_with_reasoning(transactions: list, available_categories: list) -> dict:
    """Use Claude to categorize transactions AND explain why, returning {index: {category, reason}}."""
    client = get_anthropic_client()
    if not client:
        return {}

    categories_str = ", ".join(available_categories)
    descriptions = []
    for i, t in enumerate(transactions):
        desc = t.get("description", "")
        amount = t.get("amount", 0)
        current_cat = t.get("category", "Unknown")
        flow = "inflow" if amount < 0 else "outflow"
        descriptions.append(f"{i}: {desc} (${abs(amount):.2f}, {flow}, currently: {current_cat})")

    user_prompt = f"""Re-categorize each transaction into one of: {categories_str}

{chr(10).join(descriptions)}

Return JSON mapping index to an object with "category" and "reason" (short explanation, max 12 words).
Only include transactions where the category SHOULD CHANGE. Skip ones already correct.
Example: {{"0": {{"category": "Transportation", "reason": "Uber is ride-hailing, not food delivery"}}, "3": {{"category": "Personal and Household Expenses", "reason": "Amazon is online shopping, not grocery"}}}}"""

    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4096,
            system=CATEGORIZATION_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}]
        )
        response_text = message.content[0].text.strip()
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        result = json.loads(response_text)
        return {
            int(k): v for k, v in result.items()
            if isinstance(v, dict) and v.get("category") in available_categories
        }
    except Exception as e:
        logging.error(f"LLM categorize with reasoning error: {e}")
        return {}


@api_router.post("/ai/recategorize")
async def ai_recategorize_transactions(user_id: str = Depends(get_current_user_id)):
    """Preview re-categorization using LLM. Does NOT save -- returns proposed changes via SSE."""
    client = get_anthropic_client()
    if not client:
        raise HTTPException(status_code=400, detail="Anthropic API key not configured")

    await initialize_default_categories(user_id)
    category_docs = await db.categories.find({"user_id": user_id}, {"name": 1}).to_list(200)
    category_names = [c["name"] for c in category_docs if c.get("name")]

    transactions = await db.transactions.find({"user_id": user_id}).sort("date", 1).to_list(5000)

    async def event_stream():
        def send_event(data):
            return f"data: {json.dumps(data)}\n\n"

        if not transactions:
            yield send_event({"step": "done", "message": "No transactions", "changes_count": 0, "total": 0})
            return

        total = len(transactions)
        yield send_event({"step": "starting", "message": f"Analyzing {total} transactions...", "total": total})

        all_changes = []
        batch_size = 20
        processed = 0

        for batch_start in range(0, total, batch_size):
            batch_end = min(batch_start + batch_size, total)
            batch = transactions[batch_start:batch_end]
            batch_for_llm = [
                {"description": t.get("description", ""), "amount": t.get("amount", 0), "category": t.get("category", "")}
                for t in batch
            ]

            yield send_event({
                "step": "analyzing",
                "progress": processed,
                "total": total
            })

            llm_results = await llm_categorize_with_reasoning(batch_for_llm, category_names)

            for local_idx, result in llm_results.items():
                global_idx = batch_start + local_idx
                t = transactions[global_idx]
                new_category = result.get("category", "")
                reason = result.get("reason", "")
                old_category = t.get("category", "")

                if old_category != new_category:
                    change = {
                        "transaction_id": t.get("id", ""),
                        "description": t.get("description", "")[:60],
                        "amount": t.get("amount", 0),
                        "date": str(t.get("date", "")),
                        "old_category": old_category,
                        "new_category": new_category,
                        "reason": reason,
                    }
                    all_changes.append(change)
                    yield send_event({"step": "proposed", "change": change, "changes_count": len(all_changes), "progress": processed + local_idx + 1, "total": total})

            processed = batch_end
            yield send_event({"step": "progress", "progress": processed, "total": total, "changes_count": len(all_changes)})
            await asyncio.sleep(0.1)

        yield send_event({
            "step": "done",
            "message": f"Found {len(all_changes)} proposed changes out of {total} transactions",
            "changes_count": len(all_changes),
            "total": total,
        })

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"}
    )


@api_router.post("/ai/recategorize/apply")
async def apply_recategorize_changes(
    request: dict,
    user_id: str = Depends(get_current_user_id)
):
    """Apply selected recategorization changes."""
    changes = request.get("changes", [])
    if not changes:
        return {"message": "No changes to apply", "applied_count": 0}

    applied = 0
    for change in changes:
        tid = change.get("transaction_id")
        new_cat = change.get("new_category")
        if tid and new_cat:
            result = await db.transactions.update_one(
                {"id": tid, "user_id": user_id},
                {"$set": {"category": new_cat, "updated_at": datetime.utcnow()}}
            )
            if result.modified_count > 0:
                applied += 1

    return {"message": f"Applied {applied} changes", "applied_count": applied}

@api_router.post("/ai/insight-detail")
async def get_insight_detail(
    request: dict,
    current_user: dict = Depends(get_current_user),
    view_user_id: str = Depends(get_view_user_id),
):
    """Get a deeper analysis of a specific insight, with persistent conversation."""
    client = get_anthropic_client()
    if not client:
        raise HTTPException(status_code=400, detail="Anthropic API key not configured")

    scope_filter = build_ai_scope_filter(current_user, view_user_id)
    view_filter = await build_view_filter(current_user, view_user_id)

    insight_text = request.get("insight", "")
    insight_id = request.get("insight_id", "")
    follow_up = request.get("follow_up", "")
    previous_analysis = request.get("previous_analysis", "")
    if not insight_text:
        raise HTTPException(status_code=400, detail="Insight text required")

    # Load existing conversation thread for this insight
    existing_thread = []
    if insight_id:
        item = await db.ai_insight_items.find_one({"$and": [scope_filter, {"id": insight_id}]})
        if item:
            existing_thread = item.get("thread", [])

    transactions = await db.transactions.find(view_filter).sort("date", -1).to_list(500)

    # Build context
    cat_totals = defaultdict(float)
    cat_counts = defaultdict(int)
    for t in transactions:
        amt = float(t.get("amount", 0))
        cat = t.get("category", "")
        if amt > 0:
            cat_totals[cat] += amt
            cat_counts[cat] += 1

    cat_summary = [f"- {cat}: ${total:.2f} ({cat_counts[cat]} tx)" for cat, total in sorted(cat_totals.items(), key=lambda x: -x[1])]

    recent = []
    for t in transactions[:50]:
        amt = float(t.get("amount", 0))
        recent.append({
            "date": str(t.get("date", "")),
            "desc": t.get("description", "")[:50],
            "display_amount": f"+${abs(amt):.2f}" if amt < 0 else f"-${amt:.2f}",
            "direction": "RECEIVED (money IN)" if amt < 0 else "SPENT (money OUT)",
            "category": t.get("category", ""),
        })

    context_block = f"""INSIGHT: "{insight_text}"

IMPORTANT: Amounts > 0 are OUTFLOWS (money spent). Amounts < 0 are INFLOWS (money received). Do NOT count inflows as spending.

Their spending data (outflows only):
{chr(10).join(cat_summary)}

Recent transactions (50 most recent):
{json.dumps(recent, indent=2)}"""

    json_format = """{
  "deep_dive": "2-4 short bullet points. No essays. Be direct.",
  "search_query": "query to find related transactions",
  "suggested_actions": ["1-2 specific actions, one sentence each"],
  "resolved": false,
  "follow_up_question": "question for user, or null"
}"""

    system_prompt = """You are a concise Canadian personal finance advisor. You speak in short bullet points, not paragraphs.

RULES:
- 'RECEIVED (money IN)' = user GOT money. 'SPENT (money OUT)' = user PAID money.
- Same-day matching in/out = inter-account transfers. Normal.
- Never say money laundering, fraud, suspicious. Be professional.
- Use exact dollar amounts.

STYLE:
- deep_dive: 2-4 bullet points max. Each bullet 1-2 sentences. No walls of text.
- suggested_actions: 1-2 actions max. One sentence each.
- On follow-ups: respond in 1-2 bullet points only. Don't restate the full analysis.
- If user says resolved/done/fixed: set "resolved": true, give ONE sentence closing. That's it.
- follow_up_question: ask ONLY if genuinely needed. Otherwise null."""

    # Build conversation messages
    messages = [
        {"role": "user", "content": f"Analyze this insight from my spending dashboard:\n\n{context_block}\n\nReturn JSON:\n{json_format}"}
    ]

    # Add existing thread
    for entry in existing_thread:
        if entry.get("role") == "assistant":
            messages.append({"role": "assistant", "content": json.dumps(entry.get("content", {}))})
        elif entry.get("role") == "user":
            messages.append({"role": "user", "content": entry.get("content", "")})

    # Add new follow-up if provided
    if follow_up:
        messages.append({"role": "user", "content": f"{follow_up}\n\nReturn updated JSON:\n{json_format}"})

    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1500,
            system=system_prompt,
            messages=messages
        )
        response_text = message.content[0].text.strip()
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        result = json.loads(response_text)

        # Persist conversation thread
        if insight_id:
            new_thread = list(existing_thread)
            if follow_up:
                new_thread.append({"role": "user", "content": follow_up, "timestamp": datetime.utcnow().isoformat()})
            new_thread.append({"role": "assistant", "content": result, "timestamp": datetime.utcnow().isoformat()})

            update_fields = {"thread": new_thread}
            # Auto-close if resolved
            if result.get("resolved"):
                update_fields["status"] = "addressed"

            await db.ai_insight_items.update_one(
                {"$and": [scope_filter, {"id": insight_id}]},
                {"$set": update_fields}
            )

        return result
    except Exception as e:
        logging.error(f"Insight detail error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate detailed analysis")

@api_router.post("/ai/resolve-category")
async def resolve_category_from_input(
    request: dict,
    user_id: str = Depends(get_current_user_id)
):
    """Resolve a natural language user suggestion into a category."""
    client = get_anthropic_client()
    if not client:
        raise HTTPException(status_code=400, detail="Anthropic API key not configured")

    description = request.get("description", "")
    user_input = request.get("user_input", "")
    current_category = request.get("current_category", "")

    category_docs = await db.categories.find({"user_id": user_id}, {"name": 1}).to_list(200)
    category_names = [c["name"] for c in category_docs if c.get("name")]

    prompt = f"""Transaction: "{description}"
Currently categorized as: "{current_category}"
User says: "{user_input}"

Available categories: {', '.join(category_names)}

Based on what the user said, which category should this transaction be in?
Return JSON: {{"category": "exact category name from the list", "reason": "short explanation incorporating user's input"}}
Return ONLY valid JSON."""

    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            system="You resolve user descriptions into exact category names. Always pick from the provided list. Be concise.",
            messages=[{"role": "user", "content": prompt}]
        )
        response_text = message.content[0].text.strip()
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        result = json.loads(response_text)
        if result.get("category") not in category_names:
            result["category"] = current_category
        return result
    except Exception as e:
        logging.error(f"Resolve category error: {e}")
        raise HTTPException(status_code=500, detail="Failed to resolve category")

@api_router.post("/ai/search")
async def ai_search_transactions(
    request: dict,
    current_user: dict = Depends(get_current_user),
    view_user_id: str = Depends(get_view_user_id),
):
    """Natural language transaction search."""
    query = request.get("query", "")
    if not query:
        raise HTTPException(status_code=400, detail="Query is required")

    view_filter = await build_view_filter(current_user, view_user_id)
    transactions = await db.transactions.find(view_filter).sort("date", -1).to_list(500)
    matching_ids = await llm_search_transactions(query, transactions)

    # Return the full transaction objects for matching IDs
    results = [t for t in transactions if t.get("id") in matching_ids]
    # Clean for JSON serialization
    for r in results:
        r.pop("_id", None)
        if isinstance(r.get("created_at"), datetime):
            r["created_at"] = r["created_at"].isoformat()
        if hasattr(r.get("date"), "isoformat"):
            r["date"] = r["date"].isoformat()
    return {"results": results, "count": len(results), "query": query}

# Enhanced Analytics (with user filtering)
INTERNAL_TRANSFER_MATCH_WINDOW_DAYS = 3
TRANSFER_MATCH_KEYWORDS = (
    "e transfer",
    "e-transfer",
    "interac",
    "internet transfer",
    "wire transfer",
    "transfer",
)

def is_transfer_like_transaction(transaction: dict) -> bool:
    """Determine whether a transaction is likely a transfer/payment movement."""
    explicit_internal_transfer = transaction.get("is_internal_transfer")
    if explicit_internal_transfer is True:
        return True
    if explicit_internal_transfer is False:
        return False

    category = str(transaction.get("category", "") or "")
    if category == "Transfers and Payments":
        return True

    description_normalized = normalize_text(transaction.get("description", ""))
    return any(keyword in description_normalized for keyword in TRANSFER_MATCH_KEYWORDS)

def detect_internal_transfer_transaction_ids(
    transactions: List[dict],
    window_days: int = INTERNAL_TRANSFER_MATCH_WINDOW_DAYS,
) -> set[str]:
    """
    Detect likely internal transfers by pairing transfer-like outflows and inflows
    with the same absolute amount within a short date window.
    """
    inflow_by_amount: Dict[int, List[dict]] = defaultdict(list)
    outflow_candidates: List[dict] = []

    for transaction in transactions:
        transaction_id = transaction.get("id")
        if not transaction_id or not is_transfer_like_transaction(transaction):
            continue

        amount = float(transaction.get("amount", 0) or 0)
        if abs(amount) < 0.01:
            continue

        try:
            transaction_date = datetime.fromisoformat(str(transaction.get("date", ""))).date()
        except Exception:
            continue

        amount_cents = int(round(abs(amount) * 100))
        candidate = {
            "id": transaction_id,
            "date": transaction_date,
            "amount_cents": amount_cents,
        }

        if amount < 0:
            inflow_by_amount[amount_cents].append(candidate)
        else:
            outflow_candidates.append(candidate)

    for inflows in inflow_by_amount.values():
        inflows.sort(key=lambda item: item["date"])
    outflow_candidates.sort(key=lambda item: item["date"])

    matched_inflow_ids: set[str] = set()
    matched_transaction_ids: set[str] = set()

    for outflow in outflow_candidates:
        inflow_candidates = inflow_by_amount.get(outflow["amount_cents"], [])
        best_match = None
        best_delta_days = window_days + 1

        for inflow in inflow_candidates:
            inflow_id = inflow["id"]
            if inflow_id in matched_inflow_ids:
                continue

            delta_days = abs((outflow["date"] - inflow["date"]).days)
            if delta_days > window_days:
                continue

            if delta_days < best_delta_days:
                best_delta_days = delta_days
                best_match = inflow
                if delta_days == 0:
                    break

        if not best_match:
            continue

        matched_inflow_ids.add(best_match["id"])
        matched_transaction_ids.add(outflow["id"])
        matched_transaction_ids.add(best_match["id"])

    return matched_transaction_ids

def get_analytics_spending_amount(
    transaction: dict,
    include_inflows: bool = False,
    include_internal_transfers: bool = False,
    internal_transfer_ids: Optional[set[str]] = None,
) -> float:
    """Return an amount suitable for spending analytics."""
    amount_value = float(transaction.get("amount", 0) or 0)

    if not include_internal_transfers and internal_transfer_ids:
        if transaction.get("id") in internal_transfer_ids:
            return 0.0

    if include_inflows:
        return abs(amount_value)

    # Respect explicit manual inflow/outflow overrides when present.
    is_inflow = transaction.get("is_inflow")
    if is_inflow is True:
        return 0.0
    if is_inflow is False:
        return abs(amount_value)

    # Default parser convention: positive == outflow/spending, negative == inflow.
    return amount_value if amount_value > 0 else 0.0

def get_analytics_received_amount(
    transaction: dict,
    include_internal_transfers: bool = False,
    internal_transfer_ids: Optional[set[str]] = None,
) -> float:
    """Return an amount suitable for received/inflow analytics."""
    amount_value = float(transaction.get("amount", 0) or 0)

    if not include_internal_transfers and internal_transfer_ids:
        if transaction.get("id") in internal_transfer_ids:
            return 0.0

    # Respect explicit manual inflow/outflow overrides when present.
    is_inflow = transaction.get("is_inflow")
    if is_inflow is True:
        return abs(amount_value)
    if is_inflow is False:
        return 0.0

    # Default parser convention: negative == inflow/received.
    return abs(amount_value) if amount_value < 0 else 0.0

@api_router.get("/analytics/monthly-report")
async def get_monthly_report(
    year: Optional[int] = None,
    include_inflows: bool = False,
    include_internal_transfers: bool = False,
    current_user: dict = Depends(get_current_user),
    view_user_id: str = Depends(get_view_user_id),
):
    current_year = year or datetime.now().year
    
    # Get all transactions for the year
    start_date = f"{current_year}-01-01"
    end_date = f"{current_year}-12-31"
    
    view_filter = await build_view_filter(current_user, view_user_id)
    transactions_filter = {**view_filter, "date": {"$gte": start_date, "$lte": end_date}}
    transactions = await db.transactions.find(transactions_filter).to_list(1000)

    internal_transfer_ids = set()
    if not include_internal_transfers:
        internal_transfer_ids = detect_internal_transfer_transaction_ids(transactions)
    
    # Group by month
    monthly_data = defaultdict(lambda: {
        "categories": defaultdict(float),
        "total_spent": 0,
        "total_received": 0,
        "transaction_count": 0
    })

    for transaction in transactions:
        trans_date = datetime.fromisoformat(transaction["date"]).date()
        month_key = f"{trans_date.year}-{trans_date.month:02d}"

        spending_amount = get_analytics_spending_amount(
            transaction,
            include_inflows=include_inflows,
            include_internal_transfers=include_internal_transfers,
            internal_transfer_ids=internal_transfer_ids,
        )
        received_amount = get_analytics_received_amount(
            transaction,
            include_internal_transfers=include_internal_transfers,
            internal_transfer_ids=internal_transfer_ids,
        )
        if spending_amount <= 0 and received_amount <= 0:
            continue

        if spending_amount > 0:
            monthly_data[month_key]["categories"][transaction["category"]] += spending_amount
        monthly_data[month_key]["total_spent"] += spending_amount
        monthly_data[month_key]["total_received"] += received_amount
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
            "total_received": data["total_received"],
            "net": data["total_received"] - data["total_spent"],
            "transaction_count": data["transaction_count"]
        })
    
    return sorted(reports, key=lambda x: x["month"])

@api_router.get("/analytics/category-breakdown")
async def get_category_breakdown(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    include_inflows: bool = False,
    include_internal_transfers: bool = False,
    current_user: dict = Depends(get_current_user),
    view_user_id: str = Depends(get_view_user_id),
):
    filter_dict = await build_view_filter(current_user, view_user_id)
    if start_date:
        filter_dict["date"] = {"$gte": start_date}
    if end_date:
        if "date" in filter_dict:
            filter_dict["date"]["$lte"] = end_date
        else:
            filter_dict["date"] = {"$lte": end_date}
    
    transactions = await db.transactions.find(filter_dict).to_list(1000)

    internal_transfer_ids = set()
    if not include_internal_transfers:
        internal_transfer_ids = detect_internal_transfer_transaction_ids(transactions)
    
    category_data = defaultdict(lambda: {"amount": 0, "count": 0})
    total_spending = 0
    
    for transaction in transactions:
        amount = get_analytics_spending_amount(
            transaction,
            include_inflows=include_inflows,
            include_internal_transfers=include_internal_transfers,
            internal_transfer_ids=internal_transfer_ids,
        )
        if amount <= 0:
            continue
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
        
        # Category is optional. When omitted or blank, use smart categorization.
        required_columns = ['date', 'description', 'amount']
        if not all(col in df.columns for col in required_columns):
            raise HTTPException(
                status_code=400, 
                detail=f"CSV must contain columns: {', '.join(required_columns)}"
            )
        
        category_names, merchant_history = await load_user_category_context(user_id)
        transactions = []
        for _, row in df.iterrows():
            # Convert date to string if it's a datetime object
            date_value = row['date']
            if hasattr(date_value, 'isoformat'):
                date_value = date_value.isoformat()
            elif hasattr(date_value, 'strftime'):
                date_value = date_value.strftime('%Y-%m-%d')

            description = re.sub(r"\s+", " ", str(row['description']).strip())
            category_hint = row['category'] if 'category' in df.columns else None
            resolved_category = await resolve_transaction_category(
                user_id=user_id,
                description=description,
                category_hint=category_hint,
                category_names=category_names,
                merchant_history=merchant_history,
            )
            merchant_signature = build_merchant_signature(description)
            
            transaction_data = {
                "date": str(date_value),
                "description": description,
                "category": resolved_category,
                "amount": float(row['amount']),
                "account_type": str(row.get('account_type', 'credit_card')),
                "user_id": user_id,
                "merchant_signature": merchant_signature,
            }
            transaction_obj = Transaction(**transaction_data)
            transaction_dict = transaction_obj.dict()
            # Ensure dates are strings for MongoDB
            if hasattr(transaction_dict['date'], 'isoformat'):
                transaction_dict['date'] = transaction_dict['date'].isoformat()
            if hasattr(transaction_dict['created_at'], 'isoformat'):
                transaction_dict['created_at'] = transaction_dict['created_at'].isoformat()
            transactions.append(transaction_dict)

            if merchant_signature:
                merchant_history[merchant_signature][resolved_category] += 1
        
        # Insert all transactions
        if transactions:
            await db.transactions.insert_many(transactions)
        
        return {"message": f"Successfully imported {len(transactions)} transactions"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@api_router.get("/analytics/spending-trends")
async def get_spending_trends(
    months: int = 12,
    include_inflows: bool = False,
    include_internal_transfers: bool = False,
    current_user: dict = Depends(get_current_user),
    view_user_id: str = Depends(get_view_user_id),
):
    # Get transactions from the last N months
    end_date = datetime.now().date()
    start_date = end_date.replace(month=end_date.month - months + 1 if end_date.month > months else 12 - (months - end_date.month - 1), 
                                  year=end_date.year if end_date.month > months else end_date.year - 1)
    
    view_filter = await build_view_filter(current_user, view_user_id)
    transactions_filter = {
        **view_filter,
        "date": {"$gte": start_date.isoformat(), "$lte": end_date.isoformat()}
    }
    transactions = await db.transactions.find(transactions_filter).to_list(1000)

    internal_transfer_ids = set()
    if not include_internal_transfers:
        internal_transfer_ids = detect_internal_transfer_transaction_ids(transactions)
    
    # Group by month for trend analysis
    monthly_trends = defaultdict(lambda: {"total": 0, "categories": defaultdict(float)})
    
    for transaction in transactions:
        trans_date = datetime.fromisoformat(transaction["date"]).date()
        month_key = f"{trans_date.year}-{trans_date.month:02d}"
        amount = get_analytics_spending_amount(
            transaction,
            include_inflows=include_inflows,
            include_internal_transfers=include_internal_transfers,
            internal_transfer_ids=internal_transfer_ids,
        )
        if amount <= 0:
            continue

        monthly_trends[month_key]["total"] += amount
        monthly_trends[month_key]["categories"][transaction["category"]] += amount
    
    return dict(monthly_trends)

# Account Type Analytics
@api_router.get("/analytics/account-type-breakdown")
async def get_account_type_breakdown(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    include_inflows: bool = False,
    include_internal_transfers: bool = False,
    current_user: dict = Depends(get_current_user),
    view_user_id: str = Depends(get_view_user_id),
):
    """Get spending breakdown by account type (debit vs credit)"""
    filter_dict = await build_view_filter(current_user, view_user_id)
    
    if start_date:
        filter_dict["date"] = {"$gte": start_date}
    if end_date:
        if "date" in filter_dict:
            filter_dict["date"]["$lte"] = end_date
        else:
            filter_dict["date"] = {"$lte": end_date}
    
    transactions = await db.transactions.find(filter_dict).to_list(10000)

    internal_transfer_ids = set()
    if not include_internal_transfers:
        internal_transfer_ids = detect_internal_transfer_transaction_ids(transactions)
    
    if not transactions:
        return {
            "debit": {"total": 0, "count": 0, "categories": {}},
            "credit": {"total": 0, "count": 0, "categories": {}}
        }
    
    account_breakdown = {
        "debit": {"total": 0, "count": 0, "categories": defaultdict(float)},
        "credit": {"total": 0, "count": 0, "categories": defaultdict(float)}
    }
    
    for transaction in transactions:
        amount = get_analytics_spending_amount(
            transaction,
            include_inflows=include_inflows,
            include_internal_transfers=include_internal_transfers,
            internal_transfer_ids=internal_transfer_ids,
        )
        if amount <= 0:
            continue
        account_type = "debit" if transaction.get("account_type") == "debit" else "credit"
        category = transaction["category"]
        
        account_breakdown[account_type]["total"] += amount
        account_breakdown[account_type]["count"] += 1
        account_breakdown[account_type]["categories"][category] += amount
    
    # Convert defaultdict to regular dict and calculate percentages
    result = {}
    total_spending = sum(acc["total"] for acc in account_breakdown.values())
    
    for account_type, data in account_breakdown.items():
        percentage = (data["total"] / total_spending * 100) if total_spending > 0 else 0
        result[account_type] = {
            "total": data["total"],
            "count": data["count"],
            "percentage": round(percentage, 2),
            "categories": dict(data["categories"])
        }
    
    return result

@api_router.get("/analytics/monthly-by-account-type")
async def get_monthly_breakdown_by_account_type(
    year: Optional[int] = None,
    include_inflows: bool = False,
    include_internal_transfers: bool = False,
    current_user: dict = Depends(get_current_user),
    view_user_id: str = Depends(get_view_user_id),
):
    """Get monthly spending breakdown by account type"""
    if year is None:
        year = datetime.now().year
    
    filter_dict = await build_view_filter(current_user, view_user_id)
    filter_dict["date"] = {
        "$gte": f"{year}-01-01",
        "$lte": f"{year}-12-31"
    }
    
    transactions = await db.transactions.find(filter_dict).to_list(10000)

    internal_transfer_ids = set()
    if not include_internal_transfers:
        internal_transfer_ids = detect_internal_transfer_transaction_ids(transactions)
    
    # Group by month and account type
    monthly_data = defaultdict(lambda: {
        "debit": {"total": 0, "count": 0},
        "credit": {"total": 0, "count": 0}
    })
    
    for transaction in transactions:
        trans_date = datetime.fromisoformat(transaction["date"]).date()
        month_key = f"{trans_date.year}-{trans_date.month:02d}"
        amount = get_analytics_spending_amount(
            transaction,
            include_inflows=include_inflows,
            include_internal_transfers=include_internal_transfers,
            internal_transfer_ids=internal_transfer_ids,
        )
        if amount <= 0:
            continue
        account_type = "debit" if transaction.get("account_type") == "debit" else "credit"
        
        monthly_data[month_key][account_type]["total"] += amount
        monthly_data[month_key][account_type]["count"] += 1
    
    # Convert to list format
    reports = []
    for month_key, data in monthly_data.items():
        year_val, month_val = month_key.split("-")
        reports.append({
            "month": month_key,
            "year": int(year_val),
            "debit": data["debit"],
            "credit": data["credit"],
            "total": data["debit"]["total"] + data["credit"]["total"]
        })
    
    return sorted(reports, key=lambda x: x["month"])

@api_router.get("/analytics/source-breakdown")
async def get_source_breakdown(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    include_inflows: bool = False,
    include_internal_transfers: bool = False,
    current_user: dict = Depends(get_current_user),
    view_user_id: str = Depends(get_view_user_id),
):
    """Get spending breakdown by transaction source (e.g., Member A's Debit, Member B's Credit)"""
    filter_dict = await build_view_filter(current_user, view_user_id)
    
    if start_date:
        filter_dict["date"] = {"$gte": start_date}
    if end_date:
        if "date" in filter_dict:
            filter_dict["date"]["$lte"] = end_date
        else:
            filter_dict["date"] = {"$lte": end_date}
    
    transactions = await db.transactions.find(filter_dict).to_list(10000)

    internal_transfer_ids = set()
    if not include_internal_transfers:
        internal_transfer_ids = detect_internal_transfer_transaction_ids(transactions)
    
    if not transactions:
        return []
    
    source_breakdown = defaultdict(lambda: {"total": 0, "count": 0, "account_type": ""})
    
    for transaction in transactions:
        amount = get_analytics_spending_amount(
            transaction,
            include_inflows=include_inflows,
            include_internal_transfers=include_internal_transfers,
            internal_transfer_ids=internal_transfer_ids,
        )
        if amount <= 0:
            continue
        source = transaction.get("pdf_source", "Manual")
        account_type = transaction.get("account_type", "unknown")
        
        source_breakdown[source]["total"] += amount
        source_breakdown[source]["count"] += 1
        source_breakdown[source]["account_type"] = account_type
    
    # Convert to list and calculate percentages
    total_spending = sum(data["total"] for data in source_breakdown.values())
    
    result = []
    for source, data in source_breakdown.items():
        percentage = (data["total"] / total_spending * 100) if total_spending > 0 else 0
        result.append({
            "source": source,
            "total": data["total"],
            "count": data["count"],
            "percentage": round(percentage, 2),
            "account_type": data["account_type"]
        })
    
    return sorted(result, key=lambda x: x["total"], reverse=True)

# Authentication endpoints
auth_router = APIRouter(prefix="/auth", tags=["authentication"])

@auth_router.post("/register", response_model=User)
async def register_user(user_data: UserCreate):
    # Check if user already exists
    existing_user = await get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create username from email if not provided
    username = user_data.username or user_data.email.split("@")[0]
    
    # Check if username is taken
    existing_username = await db.users.find_one({"username": username})
    if existing_username:
        # Add random suffix if username exists
        username = f"{username}_{str(uuid.uuid4())[:8]}"
    
    # Hash password
    hashed_password = get_password_hash(user_data.password)
    
    # Create user document
    user_doc = {
        "id": str(uuid.uuid4()),
        "email": user_data.email,
        "username": username,
        "full_name": user_data.full_name,
        "password_hash": hashed_password,
        "role": "user",
        "household_id": None,  # Will be set when user joins/creates household
        "created_at": datetime.utcnow(),
        "last_login": None
    }
    
    await db.users.insert_one(user_doc)
    
    # Return user without password
    return User(**{k: v for k, v in user_doc.items() if k != "password_hash"})

@auth_router.post("/login", response_model=Token)
async def login_user(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await authenticate_user(form_data.username, form_data.password)  # username field contains email
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last login
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"last_login": datetime.utcnow()}}
    )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["email"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@auth_router.get("/me", response_model=User)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    return User(**{k: v for k, v in current_user.items() if k != "password_hash"})

@auth_router.post("/household", response_model=Household)
async def create_household(household_data: HouseholdCreate, current_user: dict = Depends(get_current_user)):
    household_doc = {
        "id": str(uuid.uuid4()),
        "name": household_data.name,
        "created_by": current_user["id"],
        "members": [current_user["id"]],
        "created_at": datetime.utcnow()
    }
    
    await db.households.insert_one(household_doc)
    
    # Update user's household_id
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$set": {"household_id": household_doc["id"]}}
    )
    
    return Household(**household_doc)

@auth_router.get("/household", response_model=Optional[Household])
async def get_user_household(current_user: dict = Depends(get_current_user)):
    if not current_user.get("household_id"):
        return None
    
    household = await db.households.find_one({"id": current_user["household_id"]})
    if household:
        return Household(**household)
    return None

@auth_router.get("/household/members", response_model=List[User])
async def get_household_members(current_user: dict = Depends(get_current_user)):
    if not current_user.get("household_id"):
        return []
    
    # Get all users in the same household
    users = await db.users.find({"household_id": current_user["household_id"]}).to_list(100)
    
    # Return users without password hashes
    return [User(**{k: v for k, v in user.items() if k != "password_hash"}) for user in users]

@auth_router.post("/household/invite")
async def invite_household_member(
    invitation: dict,
    current_user: dict = Depends(get_current_user)
):
    if not current_user.get("household_id"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not part of a household"
        )
    
    email = invitation.get("email")
    role = invitation.get("role", "user")
    
    # Check if user already exists
    existing_user = await get_user_by_email(email)
    if existing_user:
        if existing_user.get("household_id"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already part of a household"
            )
        
        # Add existing user to household
        await db.users.update_one(
            {"id": existing_user["id"]},
            {"$set": {"household_id": current_user["household_id"], "role": role}}
        )
        
        # Add user to household members list
        await db.households.update_one(
            {"id": current_user["household_id"]},
            {"$addToSet": {"members": existing_user["id"]}}
        )
        
        return {"message": "User added to household successfully", "user_id": existing_user["id"]}
    else:
        # Create invitation record (for future implementation)
        invitation_doc = {
            "id": str(uuid.uuid4()),
            "email": email,
            "household_id": current_user["household_id"],
            "invited_by": current_user["id"],
            "role": role,
            "status": "pending",
            "created_at": datetime.utcnow()
        }
        
        await db.invitations.insert_one(invitation_doc)
        
        return {"message": "Invitation sent", "invitation_id": invitation_doc["id"]}

# Password Reset Endpoints
@auth_router.post("/forgot-password")
async def forgot_password(request: PasswordResetRequest):
    user = await get_user_by_email(request.email)
    if not user:
        # Don't reveal if email exists for security
        return {"message": "If the email exists, a reset code has been sent"}
    
    # Generate reset code
    reset_code = generate_reset_code()
    
    # Store reset code in database with expiration
    reset_doc = {
        "email": request.email,
        "reset_code": reset_code,
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(minutes=15)  # 15 minute expiry
    }
    
    # Remove any existing reset codes for this email
    await db.password_resets.delete_many({"email": request.email})
    await db.password_resets.insert_one(reset_doc)
    
    # Send email
    subject = "LifeTracker - Password Reset Code"
    body = f"""
    <html>
    <body>
        <h2>Password Reset Request</h2>
        <p>You requested a password reset for your LifeTracker account.</p>
        <p>Your reset code is: <strong style="font-size: 18px; color: #3B82F6;">{reset_code}</strong></p>
        <p>This code will expire in 15 minutes.</p>
        <p>If you didn't request this reset, please ignore this email.</p>
        <br>
        <p>Best regards,<br>LifeTracker Team</p>
    </body>
    </html>
    """
    
    await send_email(request.email, subject, body)
    return {"message": "If the email exists, a reset code has been sent"}

@auth_router.post("/reset-password")
async def reset_password(request: PasswordResetConfirm):
    # Find valid reset code
    reset_record = await db.password_resets.find_one({
        "email": request.email,
        "reset_code": request.reset_code,
        "expires_at": {"$gt": datetime.utcnow()}
    })
    
    if not reset_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset code"
        )
    
    # Update user password
    hashed_password = get_password_hash(request.new_password)
    await db.users.update_one(
        {"email": request.email},
        {"$set": {"password_hash": hashed_password}}
    )
    
    # Remove used reset code
    await db.password_resets.delete_many({"email": request.email})
    
    return {"message": "Password successfully reset"}

# User Profile Management Endpoints
@auth_router.put("/profile", response_model=User)
async def update_user_profile(
    profile_update: UserProfileUpdate, 
    current_user: dict = Depends(get_current_user)
):
    update_data = {}
    
    if profile_update.full_name is not None:
        update_data["full_name"] = profile_update.full_name
    
    if profile_update.username is not None:
        # Check if username is taken by another user
        existing_user = await db.users.find_one({
            "username": profile_update.username,
            "id": {"$ne": current_user["id"]}
        })
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
        update_data["username"] = profile_update.username
    
    if update_data:
        await db.users.update_one(
            {"id": current_user["id"]},
            {"$set": update_data}
        )
        
        # Get updated user
        updated_user = await db.users.find_one({"id": current_user["id"]})
        return User(**{k: v for k, v in updated_user.items() if k != "password_hash"})
    
    return User(**{k: v for k, v in current_user.items() if k != "password_hash"})

@auth_router.post("/change-password")
async def change_password(
    password_request: PasswordChangeRequest,
    current_user: dict = Depends(get_current_user)
):
    # Verify current password
    if not verify_password(password_request.current_password, current_user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Update password
    hashed_password = get_password_hash(password_request.new_password)
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$set": {"password_hash": hashed_password}}
    )
    
    return {"message": "Password successfully changed"}

# Google OAuth Endpoints
@auth_router.get("/google/login")
async def google_login(request: Request):
    try:
        # Validate OAuth configuration
        if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
            logging.error("Google OAuth credentials not configured")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Google OAuth not configured. Please contact administrator."
            )
        
        logging.info(f"Google OAuth login attempt - Client ID: {GOOGLE_CLIENT_ID[:10]}...")
        
        # Create OAuth config
        oauth = OAuth()
        google = oauth.register(
            name='google',
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET,
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={
                'scope': 'openid email profile'
            }
        )
        
        # Build redirect URI - handle both local and deployed environments
        base_url = str(request.base_url).rstrip('/')
        
        # For Railway deployment, we need to use the correct redirect URI
        if 'railway.app' in base_url:
            redirect_uri = f"{base_url}/api/auth/google/callback"
        elif 'localhost' in base_url or '127.0.0.1' in base_url:
            redirect_uri = f"{base_url}/api/auth/google/callback"
        else:
            # Default to API prefix
            redirect_uri = f"{base_url}/api/auth/google/callback"
        
        logging.info(f"Google OAuth redirect URI: {redirect_uri}")
        
        # IMPORTANT: Add error handling for OAuth configuration
        try:
            return await google.authorize_redirect(request, redirect_uri)
        except Exception as oauth_error:
            logging.error(f"OAuth redirect failed: {oauth_error}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"OAuth configuration error: {str(oauth_error)}"
            )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logging.error(f"Google OAuth login error: {e}")
        import traceback
        logging.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Google OAuth initialization failed: {str(e)}"
        )

@auth_router.get("/google/callback")
async def google_callback(request: Request):
    try:
        # Validate OAuth configuration
        if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
            logging.error("Google OAuth not configured")
            # CRITICAL FIX: Don't create a user session on OAuth failure
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Google OAuth not configured"
            )
        
        logging.info("Google OAuth callback received")
        
        # Create OAuth config
        oauth = OAuth()
        google = oauth.register(
            name='google',
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET,
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={
                'scope': 'openid email profile'
            }
        )
        
        # Get token and user info
        try:
            token = await google.authorize_access_token(request)
            user_info = token.get('userinfo')
        except Exception as oauth_error:
            logging.error(f"OAuth token exchange failed: {oauth_error}")
            # CRITICAL FIX: Properly handle OAuth failures without creating session
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Google OAuth failed: {str(oauth_error)}"
            )
        
        if not user_info or not user_info.get('email'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get user information from Google"
            )
        
        email = user_info['email']
        full_name = user_info.get('name', '')
        username = email.split('@')[0]
        
        logging.info(f"Google OAuth user: {email}")
        
        # Check if user exists
        existing_user = await get_user_by_email(email)
        
        if existing_user:
            # Update last login
            await db.users.update_one(
                {"id": existing_user["id"]},
                {"$set": {"last_login": datetime.utcnow()}}
            )
            user_data = existing_user
        else:
            # Create new user
            # Check if username is taken
            existing_username = await db.users.find_one({"username": username})
            if existing_username:
                username = f"{username}_{str(uuid.uuid4())[:8]}"
            
            user_doc = {
                "id": str(uuid.uuid4()),
                "email": email,
                "username": username,
                "full_name": full_name,
                "password_hash": get_password_hash(str(uuid.uuid4())),  # Random password for OAuth users
                "role": "user",
                "household_id": None,
                "created_at": datetime.utcnow(),
                "last_login": datetime.utcnow()
            }
            
            await db.users.insert_one(user_doc)
            user_data = user_doc
            
            # Initialize default categories for new user
            await initialize_default_categories(user_data["id"])
        
        # Create JWT token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user_data["email"]}, expires_delta=access_token_expires
        )
        
        # Return token and redirect to frontend with token in query params
        frontend_url = os.environ['FRONTEND_URL']
        redirect_url   = f"{frontend_url}?token={access_token}"
        return RedirectResponse(url=redirect_url, status_code=302)
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logging.error(f"Google OAuth callback error: {e}")
        import traceback
        logging.error(traceback.format_exc())
        # CRITICAL FIX: Don't create session on unexpected errors
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth authentication failed: {str(e)}"
        )

# Legacy endpoint for backward compatibility (will be removed later)
async def get_current_user_id_legacy():
    """Legacy function for backward compatibility during migration"""
    return "default_user"

# Include both routers in the main app
app.include_router(api_router)
app.include_router(auth_router, prefix="/api")

# RAILWAY COMPATIBILITY: Also include auth router without /api prefix for direct access
app.include_router(auth_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=[
        "http://localhost:3000",  # Local development
        "https://*.vercel.app",   # Vercel deployments
        "https://*.netlify.app",  # Netlify deployments
        "*"  # Allow all for now (change in production)
    ],
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
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
