#!/usr/bin/env python3
import requests
import json
import sys
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Get the backend URL from the frontend .env file
def get_backend_url():
    with open('/app/frontend/.env', 'r') as f:
        for line in f:
            if line.startswith('REACT_APP_BACKEND_URL='):
                return line.strip().split('=')[1].strip('"\'')
    return None

BACKEND_URL = get_backend_url()
if not BACKEND_URL:
    logging.error("Error: Could not find REACT_APP_BACKEND_URL in frontend/.env")
    sys.exit(1)

API_URL = f"{BACKEND_URL}/api"
logging.info(f"Using API URL: {API_URL}")

def test_google_oauth_login():
    """Test the Google OAuth login endpoint"""
    logging.info("Testing Google OAuth login endpoint...")
    
    try:
        # Test with allow_redirects=False to see the redirect response
        response = requests.get(f"{API_URL}/auth/google/login", allow_redirects=False)
        
        logging.info(f"Status code: {response.status_code}")
        logging.info(f"Headers: {json.dumps(dict(response.headers), indent=2)}")
        
        if response.status_code >= 300 and response.status_code < 400:
            logging.info(f"Redirect URL: {response.headers.get('Location')}")
        
        try:
            logging.info(f"Response body: {json.dumps(response.json(), indent=2)}")
        except:
            logging.info(f"Response text: {response.text[:500]}")
        
        return response.status_code < 400 or (response.status_code >= 300 and response.status_code < 400)
    
    except Exception as e:
        logging.error(f"Error testing Google OAuth login: {str(e)}")
        return False

def test_google_oauth_callback():
    """Test the Google OAuth callback endpoint with dummy parameters"""
    logging.info("Testing Google OAuth callback endpoint...")
    
    try:
        # Test with dummy code and state parameters
        response = requests.get(f"{API_URL}/auth/google/callback?code=dummy_code&state=dummy_state")
        
        logging.info(f"Status code: {response.status_code}")
        
        try:
            logging.info(f"Response body: {json.dumps(response.json(), indent=2)}")
        except:
            logging.info(f"Response text: {response.text[:500]}")
        
        # We expect this to fail with a 400 error since we're using dummy parameters
        # But it shouldn't return a 500 error
        return response.status_code != 500
    
    except Exception as e:
        logging.error(f"Error testing Google OAuth callback: {str(e)}")
        return False

def check_google_oauth_configuration():
    """Check if Google OAuth is properly configured in the environment"""
    logging.info("Checking Google OAuth configuration...")
    
    # Check if the required environment variables are set
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    
    if not client_id:
        logging.error("GOOGLE_CLIENT_ID is not set in the environment")
        return False
    
    if not client_secret:
        logging.error("GOOGLE_CLIENT_SECRET is not set in the environment")
        return False
    
    logging.info(f"GOOGLE_CLIENT_ID: {client_id[:10]}...{client_id[-5:]}")
    logging.info(f"GOOGLE_CLIENT_SECRET: {client_secret[:5]}...{client_secret[-5:]}")
    
    return True

if __name__ == "__main__":
    logging.info("Starting Google OAuth tests...")
    
    # Check configuration
    config_ok = check_google_oauth_configuration()
    logging.info(f"Configuration check: {'PASSED' if config_ok else 'FAILED'}")
    
    # Test login endpoint
    login_ok = test_google_oauth_login()
    logging.info(f"Login endpoint test: {'PASSED' if login_ok else 'FAILED'}")
    
    # Test callback endpoint
    callback_ok = test_google_oauth_callback()
    logging.info(f"Callback endpoint test: {'PASSED' if callback_ok else 'FAILED'}")
    
    # Overall result
    overall_ok = config_ok and login_ok and callback_ok
    logging.info(f"Overall test result: {'PASSED' if overall_ok else 'FAILED'}")
    
    sys.exit(0 if overall_ok else 1)