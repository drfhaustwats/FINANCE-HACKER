#!/usr/bin/env python3
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
