from fastapi import FastAPI, APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
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
from collections import defaultdict

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

# Define Models
class Transaction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    date: date
    description: str
    category: str
    amount: float
    account_type: str = "credit_card"  # credit_card, debit, checking, etc.
    created_at: datetime = Field(default_factory=datetime.utcnow)

class TransactionCreate(BaseModel):
    date: date
    description: str
    category: str
    amount: float
    account_type: str = "credit_card"

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

# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {"message": "LifeTracker Banking Dashboard API"}

@api_router.post("/transactions", response_model=Transaction)
async def create_transaction(transaction: TransactionCreate):
    transaction_dict = transaction.dict()
    transaction_obj = Transaction(**transaction_dict)
    await db.transactions.insert_one(transaction_obj.dict())
    return transaction_obj

@api_router.get("/transactions", response_model=List[Transaction])
async def get_transactions(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category: Optional[str] = None
):
    filter_dict = {}
    
    if start_date:
        filter_dict["date"] = {"$gte": start_date}
    if end_date:
        if "date" in filter_dict:
            filter_dict["date"]["$lte"] = end_date
        else:
            filter_dict["date"] = {"$lte": end_date}
    if category:
        filter_dict["category"] = category
    
    transactions = await db.transactions.find(filter_dict).sort("date", -1).to_list(1000)
    return [Transaction(**transaction) for transaction in transactions]

@api_router.delete("/transactions/{transaction_id}")
async def delete_transaction(transaction_id: str):
    result = await db.transactions.delete_one({"id": transaction_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return {"message": "Transaction deleted successfully"}

@api_router.get("/analytics/monthly-report")
async def get_monthly_report(year: Optional[int] = None):
    current_year = year or datetime.now().year
    
    # Get all transactions for the year
    start_date = f"{current_year}-01-01"
    end_date = f"{current_year}-12-31"
    
    transactions = await db.transactions.find({
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
    end_date: Optional[str] = None
):
    filter_dict = {}
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

@api_router.post("/transactions/bulk-import")
async def bulk_import_transactions(file: UploadFile = File(...)):
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
            transaction_data = {
                "date": row['date'],
                "description": row['description'],
                "category": row['category'],
                "amount": float(row['amount']),
                "account_type": row.get('account_type', 'credit_card')
            }
            transaction_obj = Transaction(**transaction_data)
            transactions.append(transaction_obj.dict())
        
        # Insert all transactions
        if transactions:
            await db.transactions.insert_many(transactions)
        
        return {"message": f"Successfully imported {len(transactions)} transactions"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@api_router.get("/analytics/spending-trends")
async def get_spending_trends(months: int = 12):
    # Get transactions from the last N months
    end_date = datetime.now().date()
    start_date = end_date.replace(month=end_date.month - months + 1 if end_date.month > months else 12 - (months - end_date.month - 1), 
                                  year=end_date.year if end_date.month > months else end_date.year - 1)
    
    transactions = await db.transactions.find({
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