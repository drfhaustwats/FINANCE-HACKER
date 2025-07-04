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
    backup_path = Path('/app/backend/server.py.bak3')
    
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
    
    # Find the duplicate router registration and remove it
    new_lines = []
    skip_next_line = False
    
    for i, line in enumerate(lines):
        if "app.include_router(auth_router, prefix=\"/api\")" in line:
            # Found the first registration, keep it
            new_lines.append(line)
            # Check if the next line is also registering auth_router
            if i + 2 < len(lines) and "app.include_router(auth_router)" in lines[i + 2]:
                skip_next_line = True
                logging.info(f"Found duplicate router registration at line {i+3}, will remove it")
        elif skip_next_line and "app.include_router(auth_router)" in line:
            # Skip this line (duplicate registration)
            skip_next_line = False
            logging.info(f"Skipping duplicate router registration at line {i+1}")
        else:
            new_lines.append(line)
    
    # Fix the Google OAuth login endpoint
    for i, line in enumerate(new_lines):
        if "@auth_router.get(\"/google/login\")" in line:
            # Found the login endpoint, replace the implementation
            start_index = i
            end_index = i
            
            # Find the end of the function
            for j in range(i + 1, len(new_lines)):
                if "@auth_router.get" in new_lines[j]:
                    end_index = j - 1
                    break
            
            # Replace the implementation
            new_implementation = [
                "@auth_router.get(\"/google/login\")\n",
                "async def google_login(request: Request):\n",
                "    # Create OAuth config with explicit credentials\n",
                "    oauth = OAuth()\n",
                "    client_id = \"350583948653-23ulg9ifs0dop7ic3pq33neb92lv1ci2.apps.googleusercontent.com\"\n",
                "    client_secret = \"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\"\n",
                "    \n",
                "    google = oauth.register(\n",
                "        name='google',\n",
                "        client_id=client_id,\n",
                "        client_secret=client_secret,\n",
                "        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',\n",
                "        client_kwargs={\n",
                "            'scope': 'openid email profile'\n",
                "        }\n",
                "    )\n",
                "    \n",
                "    # Build redirect URI using the API URL\n",
                "    api_base = os.environ.get('REACT_APP_BACKEND_URL', request.base_url)\n",
                "    redirect_uri = f\"{api_base}/api/auth/google/callback\"\n",
                "    logging.info(f\"Google OAuth redirect URI: {redirect_uri}\")\n",
                "    \n",
                "    return await google.authorize_redirect(request, redirect_uri)\n",
                "\n"
            ]
            
            # Replace the lines
            new_lines[start_index:end_index] = new_implementation
            logging.info(f"Replaced Google OAuth login implementation at lines {start_index+1}-{end_index+1}")
            break
    
    # Fix the Google OAuth callback endpoint
    for i, line in enumerate(new_lines):
        if "@auth_router.get(\"/google/callback\")" in line:
            # Found the callback endpoint, replace the OAuth client creation
            for j in range(i + 1, min(i + 20, len(new_lines))):
                if "oauth = OAuth()" in new_lines[j]:
                    # Found the OAuth client creation, replace it
                    start_index = j
                    end_index = j + 9  # Assuming 9 lines for the OAuth client creation
                    
                    # Replace the implementation
                    new_implementation = [
                        "        # Create OAuth config with explicit credentials\n",
                        "        oauth = OAuth()\n",
                        "        client_id = \"350583948653-23ulg9ifs0dop7ic3pq33neb92lv1ci2.apps.googleusercontent.com\"\n",
                        "        client_secret = \"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\"\n",
                        "        \n",
                        "        google = oauth.register(\n",
                        "            name='google',\n",
                        "            client_id=client_id,\n",
                        "            client_secret=client_secret,\n",
                        "            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',\n",
                        "            client_kwargs={\n",
                        "                'scope': 'openid email profile'\n",
                        "            }\n",
                        "        )\n"
                    ]
                    
                    # Replace the lines
                    new_lines[start_index:end_index] = new_implementation
                    logging.info(f"Replaced Google OAuth callback implementation at lines {start_index+1}-{end_index+1}")
                    break
            break
    
    # Write the updated content back to the file
    with open(server_path, 'w') as f:
        f.writelines(new_lines)
    
    logging.info("Google OAuth implementation fixed")
    return True

if __name__ == "__main__":
    logging.info("Starting Google OAuth fix...")
    
    # Fix Google OAuth implementation
    fix_ok = fix_google_oauth()
    logging.info(f"Fix result: {'SUCCESS' if fix_ok else 'FAILURE'}")
    
    sys.exit(0 if fix_ok else 1)