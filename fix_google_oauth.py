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

def fix_google_oauth():
    """Fix the Google OAuth implementation in server.py"""
    logging.info("Fixing Google OAuth implementation...")
    
    # Create a backup of the original file
    server_path = ROOT_DIR / 'server.py'
    backup_path = ROOT_DIR / 'server.py.bak'
    
    if not server_path.exists():
        logging.error(f"Server file not found at {server_path}")
        return False
    
    # Create backup
    with open(server_path, 'r') as src, open(backup_path, 'w') as dst:
        dst.write(src.read())
    
    logging.info(f"Created backup at {backup_path}")
    
    # Read the server file
    with open(server_path, 'r') as f:
        content = f.read()
    
    # Fix 1: Move OAuth client creation to module level
    oauth_module_level = """
# Initialize OAuth client
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
"""
    
    # Insert after the imports
    import_section_end = "from authlib.integrations.starlette_client import OAuth\nimport httpx"
    if import_section_end in content:
        content = content.replace(import_section_end, import_section_end + oauth_module_level)
    
    # Fix 2: Update the Google OAuth login endpoint
    old_login_endpoint = """@auth_router.get("/google/login")
async def google_login(request: Request):
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
    
    # Build redirect URI
    redirect_uri = f"{str(request.base_url).rstrip('/')}/auth/google/callback"
    return await google.authorize_redirect(request, redirect_uri)"""
    
    new_login_endpoint = """@auth_router.get("/google/login")
async def google_login(request: Request):
    # Build redirect URI using the API URL
    api_base = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001')
    redirect_uri = f"{api_base}/api/auth/google/callback"
    logging.info(f"Google OAuth redirect URI: {redirect_uri}")
    
    # Use the module-level OAuth client
    return await google_oauth.authorize_redirect(request, redirect_uri)"""
    
    if old_login_endpoint in content:
        content = content.replace(old_login_endpoint, new_login_endpoint)
    
    # Fix 3: Update the Google OAuth callback endpoint
    old_callback_endpoint = """@auth_router.get("/google/callback")
async def google_callback(request: Request):
    try:
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
        token = await google.authorize_access_token(request)
        user_info = token.get('userinfo')"""
    
    new_callback_endpoint = """@auth_router.get("/google/callback")
async def google_callback(request: Request):
    try:
        # Use the module-level OAuth client
        # Get token and user info
        token = await google_oauth.authorize_access_token(request)
        user_info = token.get('userinfo')"""
    
    if old_callback_endpoint in content:
        content = content.replace(old_callback_endpoint, new_callback_endpoint)
    
    # Fix 4: Remove duplicate router registration
    old_router_registration = """app.include_router(api_router)
app.include_router(auth_router, prefix="/api")
app.include_router(transaction_router, prefix="/api")
app.include_router(auth_router)"""
    
    new_router_registration = """app.include_router(api_router)
app.include_router(auth_router, prefix="/api")
app.include_router(transaction_router, prefix="/api")"""
    
    if old_router_registration in content:
        content = content.replace(old_router_registration, new_router_registration)
    
    # Write the updated content back to the file
    with open(server_path, 'w') as f:
        f.write(content)
    
    logging.info("Google OAuth implementation fixed")
    return True

if __name__ == "__main__":
    logging.info("Starting Google OAuth fix...")
    
    # Fix Google OAuth implementation
    fix_ok = fix_google_oauth()
    logging.info(f"Fix result: {'SUCCESS' if fix_ok else 'FAILURE'}")
    
    sys.exit(0 if fix_ok else 1)