# LifeTracker - Multi-User Financial Dashboard

A comprehensive financial tracking application with multi-user support, PDF statement parsing, and advanced analytics.

## ✨ Features

- 🔐 **Secure Authentication** - JWT-based login with user management
- 👥 **Multi-User Support** - Family households with user switching
- 📄 **PDF Import** - Automatic CIBC credit/debit statement parsing
- 📊 **Advanced Analytics** - Time-sensitive reporting with account type breakdown
- 📈 **Excel Export** - Professional formatted reports
- 🎨 **Beautiful UI** - Responsive design with Tailwind CSS
- 🏠 **Household Management** - Family member invitations and permissions

## 🛠️ Tech Stack

- **Frontend**: React, Tailwind CSS, Axios
- **Backend**: FastAPI, Python, JWT Authentication
- **Database**: MongoDB with Motor (async)
- **Authentication**: bcrypt + JWT tokens
- **PDF Processing**: pdfplumber, PyPDF2

## 🚀 Quick Deploy (Free Hosting)

Follow our [Free Hosting Guide](./FREE_HOSTING_GUIDE.md) for step-by-step deployment to:
- **Frontend**: Vercel (Free)
- **Backend**: Railway (Free) 
- **Database**: MongoDB Atlas (Free)

**Total Cost**: $0/month

## 📋 Local Development

### Prerequisites
- Node.js 16+
- Python 3.8+
- MongoDB (local or Atlas)

### Setup

1. **Clone repository**
   ```bash
   git clone https://github.com/yourusername/lifetracker.git
   cd lifetracker
   ```

2. **Backend setup**
   ```bash
   cd backend
   pip install -r requirements.txt
   cp .env.example .env
   # Edit .env with your MongoDB URL and secret key
   uvicorn server:app --reload
   ```

3. **Frontend setup**
   ```bash
   cd frontend
   yarn install
   cp .env.example .env.local
   # Edit .env.local with your backend URL
   yarn start
   ```

4. **Access application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8001
   - API Docs: http://localhost:8001/docs

## 🌟 User Guide

### Getting Started
1. **Register** your account with email and password
2. **Create household** for family financial management
3. **Upload PDFs** of your CIBC statements (credit or debit)
4. **View analytics** with time-sensitive reporting
5. **Switch between users** to see family member data
6. **Export reports** to Excel for detailed analysis

### Supported Bank Formats
- ✅ CIBC Credit Card Statements
- ✅ CIBC Debit Account Statements
- 🔄 More formats coming soon

### Features Overview
- **Personal View**: Your individual transactions and analytics
- **Family View**: Combined household financial overview
- **Member View**: Switch to see family member's data
- **Smart Categorization**: Auto-categorize transactions
- **Time-Sensitive Analytics**: Always shows current year data
- **Account Type Filtering**: Separate debit and credit analysis

## 🔧 Configuration

### Environment Variables

**Backend (.env)**
```bash
MONGO_URL=mongodb://localhost:27017
DB_NAME=lifetracker
SECRET_KEY=your-super-secret-key-here
```

**Frontend (.env.local)**
```bash
REACT_APP_BACKEND_URL=http://localhost:8001
```

### Production Environment
See [Deployment Checklist](./DEPLOYMENT_CHECKLIST.md) for production configuration.

## 🧪 Testing

```bash
# Backend tests
cd backend
python test_phase1.py
python test_phase2.py
python test_user_switching.py

# Frontend tests
cd frontend
yarn test
```

## 📚 API Documentation

Full API documentation available at `/docs` endpoint when running the backend.

### Key Endpoints
- `POST /auth/register` - User registration
- `POST /auth/login` - User authentication
- `GET /api/transactions` - Get transactions (with filtering)
- `POST /api/transactions/pdf-import` - Upload PDF statements
- `GET /api/analytics/*` - Various analytics endpoints

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- 📖 [Deployment Guide](./FREE_HOSTING_GUIDE.md)
- ✅ [Deployment Checklist](./DEPLOYMENT_CHECKLIST.md)

---

**Built with ❤️ for families who want to manage their finances together while maintaining individual privacy.**