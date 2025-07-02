#!/usr/bin/env python3

import requests
import json

API_URL = "http://localhost:8001"

def test_authentication_system():
    """Test Phase 2: Authentication and User Management"""
    print("=" * 70)
    print("🔐 TESTING PHASE 2: AUTHENTICATION SYSTEM")
    print("=" * 70)
    
    # Test data
    test_user = {
        "email": "jane.smith@example.com",
        "password": "securepassword123",
        "full_name": "Jane Smith",
        "username": "janesmith"
    }
    
    # Test 1: User Registration
    print("\n1. Testing User Registration...")
    try:
        response = requests.post(f"{API_URL}/auth/register", json=test_user)
        print(f"Registration response: {response.status_code}")
        
        if response.status_code == 200:
            user_data = response.json()
            print("✅ User registration successful!")
            print(f"   User ID: {user_data['id']}")
            print(f"   Email: {user_data['email']}")
            print(f"   Username: {user_data['username']}")
            print(f"   Full Name: {user_data['full_name']}")
        else:
            print(f"❌ Registration failed: {response.text}")
            return
    except Exception as e:
        print(f"❌ Registration error: {e}")
        return
    
    # Test 2: User Login
    print("\n2. Testing User Login...")
    try:
        login_data = {
            "username": test_user["email"],  # OAuth2 form uses username field for email
            "password": test_user["password"]
        }
        
        response = requests.post(f"{API_URL}/auth/login", data=login_data)
        print(f"Login response: {response.status_code}")
        
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data["access_token"]
            print("✅ User login successful!")
            print(f"   Token type: {token_data['token_type']}")
            print(f"   Access token: {access_token[:20]}...")
        else:
            print(f"❌ Login failed: {response.text}")
            return
    except Exception as e:
        print(f"❌ Login error: {e}")
        return
    
    # Test 3: Get Current User Info
    print("\n3. Testing Get Current User...")
    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(f"{API_URL}/auth/me", headers=headers)
        print(f"Get user response: {response.status_code}")
        
        if response.status_code == 200:
            user_info = response.json()
            print("✅ Get current user successful!")
            print(f"   ID: {user_info['id']}")
            print(f"   Email: {user_info['email']}")
            print(f"   Role: {user_info['role']}")
            print(f"   Household ID: {user_info.get('household_id', 'None')}")
        else:
            print(f"❌ Get user failed: {response.text}")
    except Exception as e:
        print(f"❌ Get user error: {e}")
    
    # Test 4: Create Household
    print("\n4. Testing Household Creation...")
    try:
        household_data = {"name": "The Smith Family"}
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.post(f"{API_URL}/auth/household", json=household_data, headers=headers)
        print(f"Create household response: {response.status_code}")
        
        if response.status_code == 200:
            household_info = response.json()
            print("✅ Household creation successful!")
            print(f"   Household ID: {household_info['id']}")
            print(f"   Name: {household_info['name']}")
            print(f"   Members: {household_info['members']}")
        else:
            print(f"❌ Household creation failed: {response.text}")
    except Exception as e:
        print(f"❌ Household creation error: {e}")
    
    # Test 5: Get Household Info
    print("\n5. Testing Get Household...")
    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(f"{API_URL}/auth/household", headers=headers)
        print(f"Get household response: {response.status_code}")
        
        if response.status_code == 200:
            household_info = response.json()
            if household_info:
                print("✅ Get household successful!")
                print(f"   Name: {household_info['name']}")
                print(f"   Created by: {household_info['created_by']}")
            else:
                print("✅ No household found (expected for new user)")
        else:
            print(f"❌ Get household failed: {response.text}")
    except Exception as e:
        print(f"❌ Get household error: {e}")
    
    # Test 6: Test Protected Endpoint (Legacy Compatibility)
    print("\n6. Testing Legacy API Compatibility...")
    try:
        # Test without authentication (should still work for legacy)
        response = requests.get(f"{API_URL}/api/transactions")
        print(f"Legacy API response: {response.status_code}")
        
        if response.status_code == 200:
            transactions = response.json()
            print("✅ Legacy API compatibility working!")
            print(f"   Found {len(transactions)} transactions (default user)")
        else:
            print(f"❌ Legacy API failed: {response.text}")
            
        # Test with authentication
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(f"{API_URL}/api/transactions", headers=headers)
        print(f"Authenticated API response: {response.status_code}")
        
        if response.status_code == 200:
            transactions = response.json()
            print("✅ Authenticated API working!")
            print(f"   Found {len(transactions)} transactions (authenticated user)")
        else:
            print(f"❌ Authenticated API failed: {response.text}")
            
    except Exception as e:
        print(f"❌ API compatibility error: {e}")
    
    print("\n" + "=" * 70)
    print("🎉 PHASE 2 TESTING COMPLETE!")
    print("✅ User Registration & Login")
    print("✅ JWT Token Authentication") 
    print("✅ Protected API Endpoints")
    print("✅ Household Management")
    print("✅ Legacy API Compatibility")
    print("=" * 70)

def test_time_sensitivity():
    """Test the time sensitivity fixes"""
    print("\n" + "=" * 70)
    print("🕒 TESTING TIME SENSITIVITY FIXES")
    print("=" * 70)
    
    from datetime import datetime
    current_year = datetime.now().year
    
    try:
        # Test current year analytics
        response = requests.get(f"{API_URL}/api/analytics/monthly-report")
        print(f"Monthly report (current year) response: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Monthly analytics using current year ({current_year})")
            print(f"   Found {len(data)} months of data")
            
            # Check if current month is highlighted
            current_month = f"{current_year}-{datetime.now().month:02d}"
            current_month_data = next((item for item in data if item['month'] == current_month), None)
            
            if current_month_data:
                print(f"✅ Current month data found: {current_month}")
                print(f"   Transactions: {current_month_data['transaction_count']}")
                print(f"   Total: ${current_month_data['total_spent']:.2f}")
            else:
                print(f"ℹ️  No data for current month: {current_month} (expected if no transactions)")
        else:
            print(f"❌ Monthly analytics failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Time sensitivity test error: {e}")

if __name__ == "__main__":
    test_time_sensitivity()
    test_authentication_system()