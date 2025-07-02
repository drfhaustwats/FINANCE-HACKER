# 🚀 LifeTracker - Free Hosting Deployment Guide

## 📋 Overview

This guide will walk you through deploying your LifeTracker application to free hosting services:

- **Frontend**: Vercel (Free tier - $0/month)
- **Backend**: Railway (Free tier - 500 hours/month)  
- **Database**: MongoDB Atlas (Free tier - 512MB)

**Total Cost**: $0/month for development and small-scale usage

---

## 🗂️ Prerequisites

Before starting, ensure you have:
- [ ] GitHub account
- [ ] Your LifeTracker code pushed to a GitHub repository
- [ ] Email address for account creation

---

# 🍃 Step 1: MongoDB Atlas Setup (5 minutes)

## 1.1 Create MongoDB Atlas Account

1. Go to [mongodb.com/atlas](https://mongodb.com/atlas)
2. Click **"Try Free"**
3. Sign up with Google/GitHub or create new account
4. Complete email verification

## 1.2 Create Free Cluster

1. Click **"Create"** when prompted for cluster creation
2. Choose **"M0 Sandbox"** (FREE tier)
3. Select **AWS** as cloud provider
4. Choose a region closest to your users (e.g., US East, EU West)
5. Name your cluster: `lifetracker-cluster`
6. Click **"Create Cluster"** (takes 3-5 minutes)

## 1.3 Configure Database Access

1. In left sidebar, click **"Database Access"**
2. Click **"Add New Database User"**
3. Create user:
   - Username: `lifetracker_user`
   - Password: Generate secure password (save this!)
   - Database User Privileges: **"Read and write to any database"**
4. Click **"Add User"**

## 1.4 Configure Network Access

1. In left sidebar, click **"Network Access"**
2. Click **"Add IP Address"**
3. Choose **"Allow Access from Anywhere"** (0.0.0.0/0)
4. Click **"Confirm"**

## 1.5 Get Connection String

1. Go back to **"Clusters"**
2. Click **"Connect"** on your cluster
3. Choose **"Connect your application"**
4. Copy the connection string (looks like):
   ```
   mongodb+srv://lifetracker_user:<password>@lifetracker-cluster.xxxxx.mongodb.net/?retryWrites=true&w=majority
   ```
5. Replace `<password>` with your actual password
6. **Save this connection string** - you'll need it for Railway!

---

# 🚂 Step 2: Railway Backend Deployment (10 minutes)

## 2.1 Create Railway Account

1. Go to [railway.app](https://railway.app)
2. Click **"Login"**
3. Sign up with **GitHub** (recommended for easy deployment)
4. Authorize Railway to access your repositories

## 2.2 Deploy Backend

1. Click **"New Project"**
2. Choose **"Deploy from GitHub repo"**
3. Select your LifeTracker repository
4. Railway will detect it's a Python app and start building

## 2.3 Configure Environment Variables

1. In your Railway project dashboard, click on the service
2. Go to **"Variables"** tab
3. Add the following environment variables:

   ```bash
   MONGO_URL=mongodb+srv://lifetracker_user:YOUR_PASSWORD@lifetracker-cluster.xxxxx.mongodb.net/lifetracker?retryWrites=true&w=majority
   SECRET_KEY=your-super-secret-key-change-this-in-production-123456789
   DB_NAME=lifetracker
   ```

   **Replace**:
   - `YOUR_PASSWORD` with your MongoDB password
   - `xxxxx` with your actual cluster URL
   - `SECRET_KEY` with a secure random string

## 2.4 Configure Build Settings

1. Go to **"Settings"** tab
2. Under **"Build"**, set:
   - **Root Directory**: `backend`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn server:app --host 0.0.0.0 --port $PORT`

## 2.5 Get Backend URL

1. Go to **"Settings"** → **"Domains"**
2. Railway will provide a URL like: `https://your-app.railway.app`
3. **Save this URL** - you'll need it for frontend!

## 2.6 Test Backend

1. Visit `https://your-app.railway.app/docs`
2. You should see the FastAPI documentation
3. Test the `/auth/register` endpoint to ensure it's working

---

# ⚡ Step 3: Vercel Frontend Deployment (5 minutes)

## 3.1 Create Vercel Account

1. Go to [vercel.com](https://vercel.com)
2. Click **"Sign up"**
3. Sign up with **GitHub** (recommended)
4. Authorize Vercel to access your repositories

## 3.2 Deploy Frontend

1. Click **"New Project"**
2. Import your LifeTracker repository
3. Configure project:
   - **Framework Preset**: Create React App
   - **Root Directory**: `frontend`
   - **Build Command**: `yarn build` (default)
   - **Output Directory**: `build` (default)

## 3.3 Configure Environment Variables

1. Before deploying, click **"Environment Variables"**
2. Add:
   ```
   REACT_APP_BACKEND_URL=https://your-app.railway.app
   ```
   (Replace with your actual Railway URL from Step 2.5)

## 3.4 Deploy

1. Click **"Deploy"**
2. Vercel will build and deploy your frontend
3. You'll get a URL like: `https://your-app.vercel.app`

---

# 🔧 Step 4: Final Configuration & Testing

## 4.1 Update CORS Settings (if needed)

If you get CORS errors, update your backend CORS settings:

```python
# In your backend/server.py
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["https://your-app.vercel.app", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 4.2 Test Complete Application

1. Visit your Vercel URL: `https://your-app.vercel.app`
2. **Register a new account**
3. **Login** to the dashboard
4. **Upload a PDF** to test the complete flow
5. **Create a household** and test user switching

## 4.3 Custom Domain (Optional)

### Vercel:
1. Go to Project Settings → Domains
2. Add your custom domain
3. Update DNS records as instructed

### Railway:
1. Go to Settings → Domains
2. Add custom domain for API
3. Update DNS records

---

# 📊 Free Tier Limitations & Monitoring

## Usage Limits:

### MongoDB Atlas (Free)
- **Storage**: 512MB
- **Connections**: 500 concurrent
- **Good for**: ~10,000 transactions

### Railway (Free)
- **Usage**: 500 hours/month
- **Memory**: 512MB RAM
- **Good for**: Small to medium usage

### Vercel (Free)
- **Bandwidth**: 100GB/month
- **Deployments**: Unlimited
- **Good for**: Most personal/family usage

## Monitoring:

1. **MongoDB**: Monitor storage in Atlas dashboard
2. **Railway**: Check usage in project dashboard
3. **Vercel**: Monitor bandwidth in analytics

---

# 🔒 Security Considerations

## Production Checklist:

- [ ] Change `SECRET_KEY` to a strong random value
- [ ] Use environment-specific MongoDB databases
- [ ] Enable MongoDB authentication
- [ ] Configure proper CORS origins
- [ ] Enable HTTPS (automatic on Vercel/Railway)
- [ ] Regular backups of MongoDB data

---

# 🚀 Your Live URLs

After deployment, you'll have:

- **Frontend**: `https://your-app.vercel.app`
- **Backend API**: `https://your-app.railway.app`  
- **API Docs**: `https://your-app.railway.app/docs`
- **Database**: MongoDB Atlas cluster

---

# 🆙 Upgrade Path

When ready to scale:

1. **MongoDB**: Upgrade to M2 ($9/month) for 2GB storage
2. **Railway**: Pro plan ($5/month) for more hours
3. **Vercel**: Pro plan ($20/month) for teams & analytics

---

# 🐛 Troubleshooting

## Common Issues:

### Backend won't start
- Check Railway logs in dashboard
- Verify environment variables are set
- Ensure MongoDB connection string is correct

### Frontend can't connect to backend
- Verify `REACT_APP_BACKEND_URL` is set correctly
- Check CORS configuration
- Test backend URL directly

### MongoDB connection failed
- Verify IP whitelist includes 0.0.0.0/0
- Check username/password in connection string
- Ensure cluster is running

### PDF uploads fail
- Check file size limits (Railway: 100MB default)
- Verify PDF parsing libraries are installed
- Check backend logs for specific errors

---

# 🎉 Success!

Your LifeTracker application is now live and accessible worldwide!

**Next Steps:**
- Share the URL with family members
- Start uploading your banking statements
- Explore the user switching features
- Monitor usage and upgrade when needed

**Support**: If you encounter issues, check the logs in Railway dashboard and Vercel analytics.

---

**Total Deployment Time**: ~20 minutes  
**Total Cost**: $0/month  
**Capacity**: Perfect for family use (up to 10 users)