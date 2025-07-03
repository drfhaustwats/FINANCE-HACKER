# 🚀 RAILWAY ENVIRONMENT VARIABLES SETUP

Copy and paste these into Railway's Variables section:

## **Required Variables:**

**MONGO_URL**
```
mongodb+srv://username:password@cluster.mongodb.net/lifetracker?retryWrites=true&w=majority
```
*Replace with your MongoDB Atlas connection string*

**DB_NAME**
```
lifetracker
```

**SECRET_KEY**
```
your-super-secure-random-string-here
```
*Generate a new secure random string for production*

## **Gmail SMTP Variables:**

**GMAIL_EMAIL**
```
your_gmail_email_here
```

**GMAIL_APP_PASSWORD**
```
ujyy fomb wecw lgfw
```

## **Google OAuth Variables:**

**GOOGLE_CLIENT_ID**
```
your_google_client_id_here
```

**GOOGLE_CLIENT_SECRET**
```
your_google_client_secret_here
```

## **How to Add in Railway:**

1. Go to your Railway project → Variables tab
2. Click "New Variable" 
3. Enter the name (e.g., MONGO_URL)
4. Enter the value 
5. Click "Add"
6. Repeat for all variables above

## **⚠️ IMPORTANT SECURITY NOTES:**

1. **Regenerate OAuth Credentials** (since they were in git):
   - Go to Google Cloud Console
   - Delete the current OAuth client
   - Create new credentials
   - Update Railway with new values

2. **Set up MongoDB Atlas** (if you haven't):
   - Create account at mongodb.com
   - Create cluster
   - Get connection string
   - Replace MONGO_URL above

3. **Generate Secure SECRET_KEY**:
   - Use: https://generate-secret.now.sh/32
   - Or run: `openssl rand -hex 32`