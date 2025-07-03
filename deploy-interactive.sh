#!/bin/bash

# LifeTracker Interactive Deployment Helper
# This script guides you through deploying to free hosting services

echo "🚀 LifeTracker Interactive Deployment Helper"
echo "============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}This script will guide you through deploying LifeTracker to free hosting.${NC}"
echo -e "${YELLOW}Total time: ~20 minutes | Total cost: \$0/month${NC}"
echo ""

# Check if we're in the right directory
if [ ! -f "backend/server.py" ]; then
    echo -e "${RED}❌ Error: Please run this script from the /app directory${NC}"
    echo "Current directory: $(pwd)"
    echo "Expected files: backend/server.py, frontend/package.json"
    exit 1
fi

echo -e "${GREEN}✅ Found LifeTracker files in current directory${NC}"
echo ""

# Step 1: GitHub Repository
echo -e "${BLUE}📂 STEP 1: GitHub Repository Setup${NC}"
echo "Your code needs to be in a GitHub repository for deployment."
echo ""
echo "What to do:"
echo "1. Go to https://github.com"
echo "2. Click 'New repository'"
echo "3. Name it 'lifetracker'"
echo "4. Make it public"
echo "5. Create repository"
echo "6. Upload your code (you can drag/drop the files from this /app folder)"
echo ""
read -p "Press ENTER when you've created the GitHub repository and uploaded your code..."
echo -e "${GREEN}✅ GitHub repository ready${NC}"
echo ""

# Get GitHub repository URL
read -p "Enter your GitHub repository URL (e.g., https://github.com/username/lifetracker): " GITHUB_URL
echo ""

# Step 2: MongoDB Atlas
echo -e "${BLUE}🍃 STEP 2: MongoDB Atlas Setup (Free Database)${NC}"
echo "Setting up your free 512MB MongoDB database..."
echo ""
echo "What to do:"
echo "1. Go to https://mongodb.com/atlas"
echo "2. Sign up for free account"
echo "3. Create M0 (FREE) cluster"
echo "4. Create database user with password"
echo "5. Set Network Access to 'Allow Access from Anywhere' (0.0.0.0/0)"
echo "6. Get connection string"
echo ""
echo "Your connection string should look like:"
echo "mongodb+srv://username:password@cluster.mongodb.net/lifetracker?retryWrites=true&w=majority"
echo ""
read -p "Press ENTER when you've completed MongoDB Atlas setup..."

read -p "Paste your MongoDB connection string here: " MONGO_URL
if [[ $MONGO_URL == mongodb+srv://* ]]; then
    echo -e "${GREEN}✅ Valid MongoDB connection string${NC}"
else
    echo -e "${YELLOW}⚠️  Warning: This doesn't look like a MongoDB Atlas connection string${NC}"
fi
echo ""

# Step 3: Railway Backend
echo -e "${BLUE}🚂 STEP 3: Railway Backend Deployment${NC}"
echo "Deploying your backend API for free..."
echo ""
echo "What to do:"
echo "1. Go to https://railway.app"
echo "2. Sign up with GitHub"
echo "3. Click 'New Project'"
echo "4. Select 'Deploy from GitHub repo'"
echo "5. Choose your 'lifetracker' repository"
echo "6. Railway will detect it's a Python app"
echo ""
echo "IMPORTANT: Configure these settings:"
echo "  → Go to your service → Settings → Root Directory: 'backend'"
echo "  → Go to Variables tab and add:"
echo "     MONGO_URL = $MONGO_URL"
echo "     SECRET_KEY = $(openssl rand -base64 32 2>/dev/null || echo 'change-this-secure-key-123')"
echo "     DB_NAME = lifetracker"
echo ""
read -p "Press ENTER when Railway deployment is complete..."

read -p "Enter your Railway app URL (e.g., https://yourapp.railway.app): " RAILWAY_URL
if [[ $RAILWAY_URL == https://* ]]; then
    echo -e "${GREEN}✅ Backend URL looks good${NC}"
else
    echo -e "${YELLOW}⚠️  Warning: URL should start with https://${NC}"
fi
echo ""

# Step 4: Vercel Frontend
echo -e "${BLUE}⚡ STEP 4: Vercel Frontend Deployment${NC}"
echo "Deploying your frontend app for free..."
echo ""
echo "What to do:"
echo "1. Go to https://vercel.com"
echo "2. Sign up with GitHub"
echo "3. Click 'New Project'"
echo "4. Import your 'lifetracker' repository"
echo "5. Configure settings:"
echo "     Framework Preset: Create React App"
echo "     Root Directory: frontend"
echo "6. Add Environment Variable:"
echo "     REACT_APP_BACKEND_URL = $RAILWAY_URL"
echo "7. Click Deploy"
echo ""
read -p "Press ENTER when Vercel deployment is complete..."

read -p "Enter your Vercel app URL (e.g., https://yourapp.vercel.app): " VERCEL_URL
if [[ $VERCEL_URL == https://* ]]; then
    echo -e "${GREEN}✅ Frontend URL looks good${NC}"
else
    echo -e "${YELLOW}⚠️  Warning: URL should start with https://${NC}"
fi
echo ""

# Step 5: Testing
echo -e "${BLUE}🧪 STEP 5: Test Your Live Application${NC}"
echo "Let's verify everything is working..."
echo ""
echo "Testing checklist:"
echo "1. Visit your app: $VERCEL_URL"
echo "2. Register a new account"
echo "3. Login successfully"
echo "4. Upload a PDF statement"
echo "5. Create a household"
echo "6. Test user switching"
echo "7. Try Excel export"
echo ""
read -p "Press ENTER when you've tested your app..."

# Final Summary
echo ""
echo -e "${GREEN}🎉 DEPLOYMENT COMPLETE!${NC}"
echo "=============================="
echo ""
echo "Your LifeTracker app is now live worldwide:"
echo -e "${GREEN}🌐 Frontend App: $VERCEL_URL${NC}"
echo -e "${GREEN}🔗 Backend API: $RAILWAY_URL${NC}"
echo -e "${GREEN}🗄️  Database: MongoDB Atlas${NC}"
echo -e "${GREEN}📁 Source Code: $GITHUB_URL${NC}"
echo ""
echo -e "${YELLOW}💰 Total monthly cost: \$0 (all free tiers)${NC}"
echo ""
echo "🎯 What you can do now:"
echo "• Share $VERCEL_URL with family members"
echo "• Start uploading your bank statements"
echo "• Create households and invite family"
echo "• Monitor usage in hosting dashboards"
echo ""
echo "🆘 Need help?"
echo "• Check FREE_HOSTING_GUIDE.md for detailed instructions"
echo "• All your URLs are saved above for reference"
echo ""
echo -e "${GREEN}Congratulations! Your financial tracking app is live! 🎊${NC}"