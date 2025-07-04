#!/usr/bin/env python3
import os
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path('/app/backend')
print(f"ROOT_DIR: {ROOT_DIR}")

# Check if .env.local exists
env_local_path = ROOT_DIR / '.env.local'
print(f".env.local exists: {env_local_path.exists()}")
if env_local_path.exists():
    print(f".env.local content:")
    with open(env_local_path, 'r') as f:
        print(f.read())

# Check if .env exists
env_path = ROOT_DIR / '.env'
print(f".env exists: {env_path.exists()}")
if env_path.exists():
    print(f".env content:")
    with open(env_path, 'r') as f:
        print(f.read())

# Load environment variables
print("Loading environment variables...")
load_dotenv(env_local_path)  # Load local secrets first
load_dotenv(env_path)        # Load template as fallback

# Check if environment variables are loaded
print(f"GOOGLE_CLIENT_ID: {os.environ.get('GOOGLE_CLIENT_ID')}")
print(f"GOOGLE_CLIENT_SECRET: {os.environ.get('GOOGLE_CLIENT_SECRET')}")