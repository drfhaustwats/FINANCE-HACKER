#!/usr/bin/env python3
import requests
import json
import sys
import os
import logging
from pathlib import Path

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

def update_test_result_md():
    """Update the test_result.md file with the Google OAuth test results"""
    logging.info("Updating test_result.md...")
    
    try:
        # Read the test_result.md file
        test_result_path = Path('/app/test_result.md')
        if not test_result_path.exists():
            logging.error(f"Test result file not found at {test_result_path}")
            return False
        
        with open(test_result_path, 'r') as f:
            content = f.read()
        
        # Find the Google OAuth task
        google_oauth_task_start = content.find("  - task: \"Google OAuth integration\"")
        if google_oauth_task_start == -1:
            logging.error("Google OAuth task not found in test_result.md")
            return False
        
        # Find the status_history section
        status_history_start = content.find("    status_history:", google_oauth_task_start)
        if status_history_start == -1:
            logging.error("Status history section not found for Google OAuth task")
            return False
        
        # Find the end of the status_history section
        next_section_start = content.find("  - task:", status_history_start)
        if next_section_start == -1:
            next_section_start = content.find("frontend:", status_history_start)
        
        if next_section_start == -1:
            logging.error("Could not find the end of the status_history section")
            return False
        
        # Extract the status_history section
        status_history = content[status_history_start:next_section_start]
        
        # Add a new status entry
        new_status_entry = """      - working: false
        agent: "testing"
        comment: "The Google OAuth integration is not working correctly. The /api/auth/google/login endpoint returns a 500 Internal Server Error. The issue is related to the OAuth client configuration. The server.py file has a duplicate router registration for auth_router, which is causing routing conflicts. Additionally, there are issues with how the environment variables for Google OAuth credentials are being accessed. The fix would involve removing the duplicate router registration and ensuring the OAuth client is properly configured with the correct credentials."
"""
        
        # Insert the new status entry
        updated_content = content[:next_section_start] + new_status_entry + content[next_section_start:]
        
        # Update the working status
        updated_content = updated_content.replace("    working: true", "    working: false", 1)
        
        # Write the updated content back to the file
        with open(test_result_path, 'w') as f:
            f.write(updated_content)
        
        logging.info("Updated test_result.md with Google OAuth test results")
        return True
    
    except Exception as e:
        logging.error(f"Error updating test_result.md: {str(e)}")
        return False

if __name__ == "__main__":
    logging.info("Starting Google OAuth test...")
    
    # Update test_result.md
    update_ok = update_test_result_md()
    logging.info(f"Update result: {'SUCCESS' if update_ok else 'FAILURE'}")
    
    sys.exit(0 if update_ok else 1)