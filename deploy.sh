#!/bin/bash

# LifeTracker Deployment Helper Script
# This script helps you deploy to free hosting services

echo "🚀 LifeTracker Deployment Helper"
echo "================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}This script will help you deploy LifeTracker to free hosting.${NC}"
echo -e "${YELLOW}You'll need to create accounts and follow the interactive steps.${NC}"
echo ""

# Step 1: GitHub Repository
echo -e "${BLUE}📂 Step 1: GitHub Repository${NC}"
echo "Your code needs to be in a GitHub repository for deployment."
echo ""
echo "Actions needed:"
echo "1. Create a GitHub repository (if you haven't already)"
echo "2. Push your LifeTracker code to GitHub"
echo ""
read -p "Press Enter when your code is on GitHub..."

# Step 2: MongoDB Atlas
echo ""
echo -e "${BLUE}🍃 Step 2: MongoDB Atlas Setup${NC}"
echo "Setting up your free MongoDB database..."
echo ""
echo "Go to: https://mongodb.com/atlas"
echo "Actions needed:"
echo "1. Sign up for free account"
echo "2. Create M0 (free) cluster"
echo "3. Create database user"
echo "4. Set network access to 0.0.0.0/0"
echo "5. Get connection string"
echo ""
echo "Your connection string should look like:"
echo "mongodb+srv://username:password@cluster.mongodb.net/lifetracker?retryWrites=true&w=majority"
echo ""
read -p "Enter your MongoDB connection string: " MONGO_URL
echo -e "${GREEN}✅ MongoDB setup ready${NC}"

# Step 3: Railway Backend
echo ""
echo -e "${BLUE}🚂 Step 3: Railway Backend Deployment${NC}"
echo "Deploying your backend API..."
echo ""
echo "Go to: https://railway.app"
echo "Actions needed:"
echo "1. Sign up with GitHub"
echo "2. Create new project from GitHub repo"
echo "3. Set root directory to 'backend'"
echo "4. Add environment variables:"
echo "   - MONGO_URL: ${MONGO_URL}"
echo "   - SECRET_KEY: $(openssl rand -base64 32)"
echo "   - DB_NAME: lifetracker"
echo ""
read -p "Enter your Railway app URL (e.g., https://yourapp.railway.app): " RAILWAY_URL
echo -e "${GREEN}✅ Backend deployment ready${NC}"

# Step 4: Vercel Frontend
echo ""
echo -e "${BLUE}⚡ Step 4: Vercel Frontend Deployment${NC}"
echo "Deploying your frontend app..."
echo ""
echo "Go to: https://vercel.com"
echo "Actions needed:"
echo "1. Sign up with GitHub"
echo "2. Import your GitHub repo"
echo "3. Set root directory to 'frontend'"
echo "4. Add environment variable:"
echo "   - REACT_APP_BACKEND_URL: ${RAILWAY_URL}"
echo ""
read -p "Enter your Vercel app URL (e.g., https://yourapp.vercel.app): " VERCEL_URL
echo -e "${GREEN}✅ Frontend deployment ready${NC}"

# Step 5: Final Testing
echo ""
echo -e "${BLUE}🧪 Step 5: Test Your Deployment${NC}"
echo "Testing your live application..."
echo ""
echo "1. Visit your app: ${VERCEL_URL}"
echo "2. Register a new account"
echo "3. Try uploading a PDF"
echo "4. Test user switching features"
echo ""

# Summary
echo ""
echo -e "${GREEN}🎉 Deployment Complete!${NC}"
echo "=============================="
echo ""
echo "Your LifeTracker app is now live:"
echo -e "${GREEN}🌐 Frontend: ${VERCEL_URL}${NC}"
echo -e "${GREEN}🔗 Backend: ${RAILWAY_URL}${NC}"
echo -e "${GREEN}🗄️  Database: MongoDB Atlas${NC}"
echo ""
echo -e "${YELLOW}💰 Total cost: $0/month${NC}"
echo ""
echo "Next steps:"
echo "• Share the app URL with family members"
echo "• Start uploading your bank statements"
echo "• Monitor usage in your hosting dashboards"
echo ""
echo -e "${BLUE}Support: Check FREE_HOSTING_GUIDE.md for detailed instructions${NC}"