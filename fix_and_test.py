#!/usr/bin/env python3
import requests
import json

# Get backend URL
def get_backend_url():
    with open('/app/frontend/.env', 'r') as f:
        for line in f:
            if line.startswith('REACT_APP_BACKEND_URL='):
                return line.strip().split('=')[1].strip('"\'')
    return None

BACKEND_URL = get_backend_url()
API_URL = f"{BACKEND_URL}/api"

# Manually add the missing Lovisa transaction
def add_lovisa_transaction():
    """Manually add the missing Lovisa transaction"""
    
    transaction_data = {
        "date": "2024-10-13",
        "description": "Lovisa Alberta AB",
        "category": "Retail and Grocery",
        "amount": 29.39,
        "account_type": "credit_card",
        "user_id": "default_user"
    }
    
    print("Adding missing Lovisa transaction...")
    print(f"Data: {json.dumps(transaction_data, indent=2)}")
    
    try:
        response = requests.post(f"{API_URL}/transactions", json=transaction_data)
        
        if response.status_code == 200:
            print("✅ SUCCESS: Lovisa transaction added!")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
            return True
        else:
            print(f"❌ FAILED: Status {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def verify_lovisa_transaction():
    """Verify the Lovisa transaction now exists"""
    print("\nVerifying Lovisa transaction exists...")
    
    try:
        response = requests.get(f"{API_URL}/transactions")
        if response.status_code == 200:
            transactions = response.json()
            
            # Search for Lovisa transaction
            lovisa_transactions = []
            for trans in transactions:
                if 'lovisa' in trans.get('description', '').lower():
                    lovisa_transactions.append(trans)
            
            if lovisa_transactions:
                print(f"✅ FOUND {len(lovisa_transactions)} Lovisa transaction(s):")
                for trans in lovisa_transactions:
                    print(f"   Date: {trans.get('date')}")
                    print(f"   Description: {trans.get('description')}")
                    print(f"   Amount: ${trans.get('amount')}")
                    print(f"   Category: {trans.get('category')}")
                    print(f"   ID: {trans.get('id')}")
                return True
            else:
                print("❌ No Lovisa transactions found")
                return False
        else:
            print(f"❌ Failed to get transactions: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def test_category_update():
    """Test the new category update functionality"""
    print("\nTesting category update functionality...")
    
    # First get a transaction to update
    try:
        response = requests.get(f"{API_URL}/transactions")
        if response.status_code != 200:
            print("❌ Failed to get transactions for testing")
            return False
        
        transactions = response.json()
        if not transactions:
            print("❌ No transactions found for testing")
            return False
        
        # Use first transaction for testing
        test_transaction = transactions[0]
        transaction_id = test_transaction.get('id')
        original_category = test_transaction.get('category')
        
        print(f"Testing with transaction: {test_transaction.get('description')}")
        print(f"Original category: {original_category}")
        
        # Update category
        new_category = "Transportation" if original_category != "Transportation" else "Restaurants"
        update_data = {"category": new_category}
        
        update_response = requests.put(f"{API_URL}/transactions/{transaction_id}", json=update_data)
        
        if update_response.status_code == 200:
            print(f"✅ Category update successful!")
            print(f"New category: {new_category}")
            
            # Verify the update
            verify_response = requests.get(f"{API_URL}/transactions")
            if verify_response.status_code == 200:
                updated_transactions = verify_response.json()
                updated_transaction = next((t for t in updated_transactions if t.get('id') == transaction_id), None)
                
                if updated_transaction and updated_transaction.get('category') == new_category:
                    print(f"✅ Category update verified!")
                    return True
                else:
                    print(f"❌ Category update not reflected in database")
                    return False
            else:
                print(f"❌ Failed to verify update")
                return False
        else:
            print(f"❌ Category update failed: {update_response.status_code}")
            print(f"Response: {update_response.text}")
            return False
            
    except Exception as e:
        print(f"❌ ERROR testing category update: {e}")
        return False

if __name__ == "__main__":
    print("FIXING MISSING TRANSACTION AND TESTING CATEGORY UPDATE")
    print("=" * 80)
    
    # Step 1: Add missing Lovisa transaction
    if add_lovisa_transaction():
        verify_lovisa_transaction()
    
    print("\n" + "=" * 80)
    
    # Step 2: Test category update functionality
    test_category_update()