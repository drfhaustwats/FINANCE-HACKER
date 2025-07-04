# Replace the entire transaction creation and update logic

@api_router.post("/transactions")
async def create_transaction(
    transaction: dict, 
    current_user_id: str = Depends(get_current_user_id)
):
    try:
        # Create transaction document with manual inflow/outflow override
        transaction_doc = {
            "id": str(uuid.uuid4()),
            "user_id": current_user_id,
            "date": transaction["date"],
            "description": transaction["description"],
            "category": transaction["category"],
            "amount": float(transaction["amount"]),
            "account_type": transaction.get("account_type", "credit_card"),
            "pdf_source": transaction.get("pdf_source", "Manual"),
            "created_at": datetime.utcnow(),
            # NEW: Allow manual override of inflow/outflow
            "is_inflow": transaction.get("is_inflow", None),  # None means auto-detect
            "original_amount": float(transaction["amount"])  # Store original for reference
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

@api_router.put("/transactions/{transaction_id}")
async def update_transaction(
    transaction_id: str, 
    transaction_data: dict,
    current_user_id: str = Depends(get_current_user_id)
):
    try:
        # Build update document
        update_data = {
            "updated_at": datetime.utcnow()
        }
        
        # Update allowed fields
        allowed_fields = ["description", "category", "amount", "date", "account_type", "is_inflow"]
        for field in allowed_fields:
            if field in transaction_data:
                update_data[field] = transaction_data[field]
        
        # Handle manual inflow/outflow override
        if "is_inflow" in transaction_data:
            is_inflow = transaction_data["is_inflow"]
            current_amount = transaction_data.get("amount")
            
            if current_amount is not None:
                if is_inflow and current_amount > 0:
                    update_data["amount"] = -abs(current_amount)
                elif not is_inflow and current_amount < 0:
                    update_data["amount"] = abs(current_amount)
                else:
                    update_data["amount"] = current_amount
        
        result = await db.transactions.update_one(
            {"id": transaction_id, "user_id": current_user_id},
            {"$set": update_data}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        return {"message": "Transaction updated successfully"}
    except Exception as e:
        logging.error(f"Error updating transaction: {e}")
        raise HTTPException(status_code=500, detail=str(e))