#!/usr/bin/env python3
import sys
import os
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def fix_google_oauth():
    """Fix the Google OAuth implementation in server.py"""
    logging.info("Fixing Google OAuth implementation...")
    
    # Create a backup of the original file
    server_path = Path('/app/backend/server.py')
    backup_path = Path('/app/backend/server.py.bak4')
    
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
    
    # Fix 1: Remove duplicate router registration
    if "app.include_router(auth_router)" in content and "app.include_router(auth_router, prefix=\"/api\")" in content:
        content = content.replace("app.include_router(auth_router)", "# Removed duplicate router registration")
        logging.info("Removed duplicate router registration")
    
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
    try:
        # Create OAuth config with hardcoded credentials
        oauth = OAuth()
        client_id = "350583948653-23ulg9ifs0dop7ic3pq33neb92lv1ci2.apps.googleusercontent.com"
        client_secret = "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"
        
        google = oauth.register(
            name='google',
            client_id=client_id,
            client_secret=client_secret,
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={
                'scope': 'openid email profile'
            }
        )
        
        # Build redirect URI using the API URL
        api_base = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001')
        redirect_uri = f"{api_base}/api/auth/google/callback"
        logging.info(f"Google OAuth redirect URI: {redirect_uri}")
        
        return await google.authorize_redirect(request, redirect_uri)
    except Exception as e:
        logging.error(f"Google OAuth login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Google OAuth login error: {str(e)}"
        )"""
    
    if old_login_endpoint in content:
        content = content.replace(old_login_endpoint, new_login_endpoint)
        logging.info("Updated Google OAuth login endpoint")
    
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
        )"""
    
    new_callback_endpoint = """@auth_router.get("/google/callback")
async def google_callback(request: Request):
    try:
        # Create OAuth config with hardcoded credentials
        oauth = OAuth()
        client_id = "350583948653-23ulg9ifs0dop7ic3pq33neb92lv1ci2.apps.googleusercontent.com"
        client_secret = "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"
        
        google = oauth.register(
            name='google',
            client_id=client_id,
            client_secret=client_secret,
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={
                'scope': 'openid email profile'
            }
        )"""
    
    if old_callback_endpoint in content:
        content = content.replace(old_callback_endpoint, new_callback_endpoint)
        logging.info("Updated Google OAuth callback endpoint")
    
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