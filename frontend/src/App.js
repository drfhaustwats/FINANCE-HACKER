import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';
import { AuthProvider, useAuth } from './AuthContext';
import AuthPage from './components/AuthPage';
import UserHeader from './components/UserHeader';
import LoadingScreen from './components/LoadingScreen';
import AdvancedFilters from './components/AdvancedFilters';
import OptimizedTransactionTable from './components/OptimizedTransactionTable';
import AnalyticsDashboard from './components/AnalyticsDashboard';

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
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState({});
  const { user } = useAuth();

  // Fetch transactions when component mounts or filters change
  useEffect(() => {
    const fetchTransactions = async () => {
      try {
        setLoading(true);
        const response = await axios.get('/api/transactions', {
          params: { ...filters },
          headers: { Authorization: `Bearer ${user.token}` }
        });
        setTransactions(response.data);
        setError(null);
      } catch (err) {
        setError('Failed to fetch transactions');
        console.error('Error fetching transactions:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchTransactions();
  }, [filters, user.token]);

  // Process data for analytics
  const categoryBreakdown = transactions.reduce((acc, t) => {
    const category = t.category || 'Uncategorized';
    const amount = Math.abs(t.amount);
    const existing = acc.find(c => c.category === category);
    
    if (existing) {
      existing.amount += amount;
    } else {
      acc.push({ category, amount, percentage: 0 });
    }
    return acc;
  }, []);

  // Calculate percentages
  const totalAmount = categoryBreakdown.reduce((sum, cat) => sum + cat.amount, 0);
  categoryBreakdown.forEach(cat => {
    cat.percentage = (cat.amount / totalAmount) * 100;
  });

  // Process monthly reports
  const monthlyReports = transactions.reduce((acc, t) => {
    const date = new Date(t.date);
    const month = date.getMonth() + 1;
    const existing = acc.find(r => r.month === month);
    
    if (existing) {
      existing.total_spent += Math.abs(t.amount);
    } else {
      acc.push({ month, total_spent: Math.abs(t.amount) });
    }
    return acc;
  }, []);

  if (loading) return <div className="p-8">Loading transactions...</div>;
  if (error) return <div className="p-8 text-red-600">{error}</div>;

  return (
    <div className="p-8">
      <AdvancedFilters onFilterChange={setFilters} />
      <div className="mb-8">
        <AnalyticsDashboard 
          categoryBreakdown={categoryBreakdown}
          monthlyReports={monthlyReports}
          transactions={transactions}
          formatCurrency={formatCurrency}
          getMonthName={getMonthName}
        />
      </div>
      <OptimizedTransactionTable 
        transactions={transactions}
        formatCurrency={formatCurrency}
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
