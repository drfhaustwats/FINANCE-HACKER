#!/usr/bin/env python3
import sys
import os
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def add_debug_logging():
    """Add debug logging to the Google OAuth implementation in server.py"""
    logging.info("Adding debug logging to Google OAuth implementation...")
    
    # Create a backup of the original file
    server_path = Path('/app/backend/server.py')
    backup_path = Path('/app/backend/server.py.bak6')
    
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
    
    # Find the Google OAuth login endpoint
    for i in range(len(lines)):
        if "@auth_router.get(\"/google/login\")" in lines[i]:
            # Found the login endpoint, add debug logging
            login_func_start = i + 1
            
            # Find the function definition line
            for j in range(login_func_start, len(lines)):
                if "async def google_login" in lines[j]:
                    # Insert debug logging after the function definition
                    debug_lines = [
                        "    # Add debug logging\n",
                        "    import logging\n",
                        "    logging.basicConfig(level=logging.DEBUG)\n",
                        "    logging.debug(\"Google OAuth login endpoint called\")\n",
                        "    logging.debug(f\"Request base_url: {request.base_url}\")\n",
                        "    logging.debug(f\"GOOGLE_CLIENT_ID: {GOOGLE_CLIENT_ID}\")\n",
                        "    logging.debug(f\"GOOGLE_CLIENT_SECRET: {GOOGLE_CLIENT_SECRET[:5]}...\")\n",
                        "\n",
                        "    try:\n"
                    ]
                    
                    # Insert the debug lines
                    lines.insert(j + 1, "".join(debug_lines))
                    
                    # Add try-except block around the OAuth code
                    for k in range(j + 1, len(lines)):
                        if "return await" in lines[k]:
                            # Add except block after the return statement
                            except_lines = [
                                "    except Exception as e:\n",
                                "        logging.error(f\"Google OAuth login error: {e}\")\n",
                                "        import traceback\n",
                                "        logging.error(traceback.format_exc())\n",
                                "        raise HTTPException(\n",
                                "            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,\n",
                                "            detail=f\"Google OAuth login error: {str(e)}\"\n",
                                "        )\n"
                            ]
                            
                            # Insert the except block
                            lines.insert(k + 1, "".join(except_lines))
                            logging.info(f"Added debug logging to Google OAuth login endpoint")
                            break
                    break
            break
    
    # Write the updated content back to the file
    with open(server_path, 'w') as f:
        f.writelines(lines)
    
    logging.info("Debug logging added to Google OAuth implementation")
    return True

if __name__ == "__main__":
    logging.info("Starting Google OAuth debug logging...")
    
    # Add debug logging
    debug_ok = add_debug_logging()
    logging.info(f"Debug logging result: {'SUCCESS' if debug_ok else 'FAILURE'}")
    
    sys.exit(0 if debug_ok else 1)