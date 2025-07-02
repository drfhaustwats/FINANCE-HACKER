# ✅ LifeTracker Deployment Checklist

## Pre-Deployment
- [ ] Code pushed to GitHub repository
- [ ] All features tested locally
- [ ] Environment files configured properly

## MongoDB Atlas (5 min)
- [ ] Account created at mongodb.com/atlas
- [ ] Free M0 cluster created
- [ ] Database user created with read/write permissions
- [ ] Network access set to 0.0.0.0/0 (allow all)
- [ ] Connection string saved

## Railway Backend (10 min)
- [ ] Account created at railway.app with GitHub
- [ ] Project deployed from GitHub repo
- [ ] Environment variables set:
  - [ ] `MONGO_URL` (from Atlas)
  - [ ] `SECRET_KEY` (secure random string)
  - [ ] `DB_NAME=lifetracker`
- [ ] Build settings configured:
  - [ ] Root Directory: `backend`
  - [ ] Start Command: `uvicorn server:app --host 0.0.0.0 --port $PORT`
- [ ] Backend URL saved (e.g., https://yourapp.railway.app)
- [ ] API docs accessible at /docs endpoint

## Vercel Frontend (5 min)
- [ ] Account created at vercel.com with GitHub
- [ ] Project deployed from GitHub repo
- [ ] Environment variables set:
  - [ ] `REACT_APP_BACKEND_URL` (Railway URL)
- [ ] Build settings configured:
  - [ ] Root Directory: `frontend`
  - [ ] Framework: Create React App
- [ ] Frontend URL received (e.g., https://yourapp.vercel.app)

## Testing & Verification
- [ ] Frontend loads without errors
- [ ] User registration works
- [ ] User login successful
- [ ] Dashboard displays correctly
- [ ] PDF upload functionality works
- [ ] Transactions display properly
- [ ] User switching features work
- [ ] Household creation/management works
- [ ] Excel export functions
- [ ] Analytics display correctly

## Optional Enhancements
- [ ] Custom domain configured
- [ ] CORS properly configured for production
- [ ] Error monitoring set up
- [ ] Regular backup schedule planned

## Post-Deployment
- [ ] Share app URL with intended users
- [ ] Monitor usage in dashboards
- [ ] Set up alerts for quota limits
- [ ] Plan upgrade path if needed

---

## 🚨 Emergency Contacts

**If something goes wrong:**

1. **Backend Issues**: Check Railway logs in project dashboard
2. **Frontend Issues**: Check Vercel deployment logs
3. **Database Issues**: Check MongoDB Atlas monitoring
4. **CORS Errors**: Verify environment variables and CORS config

## 📊 Monitoring

**Keep an eye on:**
- MongoDB Atlas storage usage (512MB limit)
- Railway monthly hours (500 hour limit)
- Vercel bandwidth usage (100GB limit)

---

**Estimated Total Time**: 20 minutes  
**Total Cost**: $0/month  
**Perfect for**: Family use (2-10 users)