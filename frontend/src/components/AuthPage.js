import React, { useState } from 'react';
import Login from './Login';
import Register from './Register';
import ForgotPassword from './ForgotPassword';

const AuthPage = () => {
  const [currentView, setCurrentView] = useState('login'); // 'login', 'register', 'forgot-password'

  return (
    <>
      {currentView === 'login' && (
        <Login 
          onSwitchToRegister={() => setCurrentView('register')}
          onSwitchToForgotPassword={() => setCurrentView('forgot-password')}
        />
      )}
      {currentView === 'register' && (
        <Register onSwitchToLogin={() => setCurrentView('login')} />
      )}
      {currentView === 'forgot-password' && (
        <ForgotPassword onBackToLogin={() => setCurrentView('login')} />
      )}
    </>
  );
};

export default AuthPage;