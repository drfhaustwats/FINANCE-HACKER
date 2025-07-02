import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState(localStorage.getItem('token'));

  const API = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

  // Set up axios interceptor for token
  useEffect(() => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    } else {
      delete axios.defaults.headers.common['Authorization'];
    }
  }, [token]);

  // Check if user is logged in on app start
  useEffect(() => {
    const checkAuth = async () => {
      if (token) {
        try {
          const response = await axios.get(`${API}/auth/me`);
          setUser(response.data);
        } catch (error) {
          console.error('Auth check failed:', error);
          logout(); // Clear invalid token
        }
      }
      setLoading(false);
    };

    checkAuth();
  }, [token, API]);

  const login = async (email, password) => {
    try {
      const formData = new URLSearchParams();
      formData.append('username', email); // OAuth2 form uses username field for email
      formData.append('password', password);

      const response = await axios.post(`${API}/auth/login`, formData, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        }
      });

      const { access_token } = response.data;
      
      setToken(access_token);
      localStorage.setItem('token', access_token);
      
      // Get user info
      const userResponse = await axios.get(`${API}/auth/me`, {
        headers: { Authorization: `Bearer ${access_token}` }
      });
      
      setUser(userResponse.data);
      return { success: true };
    } catch (error) {
      console.error('Login failed:', error);
      return { 
        success: false, 
        error: error.response?.data?.detail || 'Login failed' 
      };
    }
  };

  const register = async (userData) => {
    try {
      const response = await axios.post(`${API}/auth/register`, userData);
      
      // Auto-login after successful registration
      const loginResult = await login(userData.email, userData.password);
      
      if (loginResult.success) {
        return { success: true, user: response.data };
      } else {
        return { success: false, error: 'Registration successful but login failed' };
      }
    } catch (error) {
      console.error('Registration failed:', error);
      return { 
        success: false, 
        error: error.response?.data?.detail || 'Registration failed' 
      };
    }
  };

  const logout = () => {
    setUser(null);
    setToken(null);
    localStorage.removeItem('token');
    delete axios.defaults.headers.common['Authorization'];
  };

  const createHousehold = async (householdData) => {
    try {
      const response = await axios.post(`${API}/auth/household`, householdData);
      
      // Update user data to reflect new household
      const userResponse = await axios.get(`${API}/auth/me`);
      setUser(userResponse.data);
      
      return { success: true, household: response.data };
    } catch (error) {
      console.error('Create household failed:', error);
      return { 
        success: false, 
        error: error.response?.data?.detail || 'Failed to create household' 
      };
    }
  };

  const value = {
    user,
    loading,
    login,
    register,
    logout,
    createHousehold,
    isAuthenticated: !!user
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};