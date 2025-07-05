import React from 'react';
import './App.css';
import AnalyticsDashboard from './components/AnalyticsDashboard';
import { AuthProvider } from './AuthContext';

function App() {
  return (
    <AuthProvider>
      <div className="min-h-screen bg-gray-50 p-8">
        <AnalyticsDashboard />
      </div>
    </AuthProvider>
  );
}

export default App;
