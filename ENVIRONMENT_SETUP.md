# 🔐 Environment Variables Setup

## For Local Development

1. **Copy the example file:**
   ```bash
   cp backend/.env.example backend/.env.local
   ```

2. **Edit `.env.local` with your actual secrets:**
   ```bash
   # backend/.env.local (NEVER COMMIT THIS FILE)
   MONGO_URL="mongodb://localhost:27017"
   DB_NAME="test_database"
   SECRET_KEY="your-secret-key-here"
   
   # Gmail SMTP Configuration
   GMAIL_EMAIL="your_gmail@gmail.com"
   GMAIL_APP_PASSWORD="your_gmail_app_password"
   
   # Google OAuth Configuration
   GOOGLE_CLIENT_ID="your_google_client_id"
   GOOGLE_CLIENT_SECRET="your_google_client_secret"
   ```

## For Production Deployment

**DO NOT put real secrets in git!** Instead:

### Railway Deployment:
1. Go to your Railway project dashboard
2. Navigate to Variables tab
3. Add each environment variable securely

### Vercel Deployment:
1. Go to your Vercel project settings
2. Navigate to Environment Variables
3. Add each variable for Production environment

### Other Platforms:
Use your platform's secure environment variable management system.

## ⚠️ Security Rules

- ✅ `.env.local` - Use for local development (gitignored)
- ✅ `.env.example` - Template file (safe to commit)
- ❌ `.env` - Now contains placeholders only
- ❌ NEVER commit real secrets to git!

## 🚨 If You Accidentally Commit Secrets

1. **Immediately revoke/regenerate** all exposed credentials
2. **Clean git history** using git filter-branch
3. **Update your production environment** with new secrets