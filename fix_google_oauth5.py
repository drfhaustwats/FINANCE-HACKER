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
    backup_path = Path('/app/backend/server.py.bak5')
    
    if not server_path.exists():
        logging.error(f"Server file not found at {server_path}")
        return False
    
    # Create backup
    with open(server_path, 'r') as src, open(backup_path, 'w') as dst:
        dst.write(src.read())
    
    logging.info(f"Created backup at {backup_path}")
    
    # Read the server file
    with open(server_path, 'r') as f:
        lines = f.readlines()
    
    # Find and fix the duplicate router registration
    for i in range(len(lines)):
        if "app.include_router(auth_router)" in lines[i] and i > 0 and "app.include_router(auth_router, prefix=\"/api\")" in lines[i-2]:
            lines[i] = "# app.include_router(auth_router)  # Removed duplicate registration\n"
            logging.info(f"Removed duplicate router registration at line {i+1}")
    
    # Write the updated content back to the file
    with open(server_path, 'w') as f:
        f.writelines(lines)
    
    logging.info("Google OAuth implementation fixed")
    return True

if __name__ == "__main__":
    logging.info("Starting Google OAuth fix...")
    
    # Fix Google OAuth implementation
    fix_ok = fix_google_oauth()
    logging.info(f"Fix result: {'SUCCESS' if fix_ok else 'FAILURE'}")
    
    sys.exit(0 if fix_ok else 1)