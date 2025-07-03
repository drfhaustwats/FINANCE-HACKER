#!/usr/bin/env python3
"""
Railway-specific startup script for LifeTracker backend.
This ensures proper port configuration and environment setup.
"""

import os
import uvicorn

if __name__ == "__main__":
    # Railway sets the PORT environment variable
    port = int(os.environ.get("PORT", 8000))
    
    # Run the FastAPI application
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=port,
        log_level="info"
    )