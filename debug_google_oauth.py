#!/usr/bin/env python3
import requests
import json
import sys
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
ROOT_DIR = Path('/app/backend')
load_dotenv(ROOT_DIR / '.env.local')
load_dotenv(ROOT_DIR / '.env')

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
    """Test the Google OAuth login endpoint with debug information"""
    logging.info("Testing Google OAuth login endpoint...")
    
    try:
        # Enable debug logging for requests
        import http.client as http_client
        http_client.HTTPConnection.debuglevel = 1
        
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

def check_backend_logs():
    """Check the backend logs for errors"""
    logging.info("Checking backend logs...")
    
    try:
        # Get the last 100 lines of the backend error log
        log_path = Path('/var/log/supervisor/backend.err.log')
        if log_path.exists():
            with open(log_path, 'r') as f:
                lines = f.readlines()
                last_lines = lines[-100:]
                logging.info(f"Last 100 lines of backend error log:")
                for line in last_lines:
                    logging.info(line.strip())
        else:
            logging.error(f"Backend error log not found at {log_path}")
        
        return True
    
    except Exception as e:
        logging.error(f"Error checking backend logs: {str(e)}")
        return False

def create_minimal_oauth_test():
    """Create a minimal test file for Google OAuth"""
    logging.info("Creating minimal OAuth test file...")
    
    try:
        test_file_path = Path('/app/minimal_oauth_test.py')
        
        test_file_content = """#!/usr/bin/env python3
from fastapi import FastAPI, Request
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth
import uvicorn
import os

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="your-secret-key")

# Google OAuth Configuration
GOOGLE_CLIENT_ID = "350583948653-23ulg9ifs0dop7ic3pq33neb92lv1ci2.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET = "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"

# Initialize OAuth
oauth = OAuth()
oauth.register(
    name='google',
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

@app.get("/")
async def root():
    return {"message": "Minimal OAuth Test"}

@app.get("/login")
async def login(request: Request):
    redirect_uri = request.url_for('auth')
    return await oauth.google.authorize_redirect(request, redirect_uri)

@app.get("/auth")
async def auth(request: Request):
    try:
        token = await oauth.google.authorize_access_token(request)
        user = await oauth.google.parse_id_token(request, token)
        return {"user": user}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
"""
        
        with open(test_file_path, 'w') as f:
            f.write(test_file_content)
        
        logging.info(f"Created minimal OAuth test file at {test_file_path}")
        return True
    
    except Exception as e:
        logging.error(f"Error creating minimal OAuth test file: {str(e)}")
        return False

if __name__ == "__main__":
    logging.info("Starting Google OAuth debug...")
    
    # Check backend logs
    check_backend_logs()
    
    # Test Google OAuth login
    login_ok = test_google_oauth_login()
    logging.info(f"Login endpoint test: {'PASSED' if login_ok else 'FAILED'}")
    
    # Create minimal OAuth test
    create_minimal_oauth_test()
    
    logging.info("Google OAuth debug complete")
    
    sys.exit(0 if login_ok else 1)