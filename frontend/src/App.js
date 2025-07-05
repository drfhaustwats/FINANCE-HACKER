import React from 'react';
import './App.css';
import { AuthProvider, useAuth } from './AuthContext';
import AuthPage from './components/AuthPage';
import UserHeader from './components/UserHeader';
import LoadingScreen from './components/LoadingScreen';
import AnalyticsDashboard from './components/AnalyticsDashboard';
import { categoryBreakdown, monthlyReports, transactions } from './mockAnalyticsData';

// Helper functions
const formatCurrency = (amount) => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD'
  }).format(amount);
};

const getMonthName = (month) => {
  return new Date(2024, month - 1).toLocaleString('default', { month: 'long' });
};

// Main Dashboard Component
function Dashboard() {
  return (
    <div className="p-8">
      <AnalyticsDashboard 
        categoryBreakdown={categoryBreakdown}
        monthlyReports={monthlyReports}
        transactions={transactions}
        formatCurrency={formatCurrency}
        getMonthName={getMonthName}
      />
    </div>
  );
}

// Main App Component with Authentication
function AppContent() {
  const { user, loading } = useAuth();

  if (loading) {
    return <LoadingScreen />;
  }

  if (!user) {
    return <AuthPage />;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <UserHeader />
      <Dashboard />
    </div>
  );
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;
