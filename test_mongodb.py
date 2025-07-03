#!/usr/bin/env python3

import os
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio

async def test_mongodb_connection():
    """Test MongoDB Atlas connection"""
    
    # Test connection string (replace with your actual one)
    mongo_url = input("Enter your MongoDB connection string: ").strip()
    
    if not mongo_url.startswith("mongodb+srv://"):
        print("❌ Invalid MongoDB connection string format")
        return
    
    try:
        print("🔍 Testing MongoDB connection...")
        client = AsyncIOMotorClient(mongo_url)
        
        # Test connection
        await client.admin.command('ping')
        print("✅ MongoDB connection successful!")
        
        # Test database access
        db = client.lifetracker
        collections = await db.list_collection_names()
        print(f"✅ Database access successful! Collections: {collections}")
        
        # Test write permission
        test_doc = {"test": "connection", "timestamp": "2025-07-03"}
        result = await db.test_collection.insert_one(test_doc)
        print(f"✅ Write permission successful! Inserted ID: {result.inserted_id}")
        
        # Clean up test document
        await db.test_collection.delete_one({"_id": result.inserted_id})
        print("✅ Test cleanup complete")
        
        client.close()
        
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        print("\nCommon issues:")
        print("• Check your username/password in the connection string")
        print("• Verify network access allows 0.0.0.0/0")
        print("• Make sure your cluster is running")

if __name__ == "__main__":
    asyncio.run(test_mongodb_connection())