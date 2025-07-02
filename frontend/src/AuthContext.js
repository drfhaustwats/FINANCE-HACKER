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
  const [currentViewUser, setCurrentViewUser] = useState(null); // User we're currently viewing data for
  const [household, setHousehold] = useState(null);
  const [householdMembers, setHouseholdMembers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [viewMode, setViewMode] = useState('personal'); // 'personal', 'family', 'member'

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
          setCurrentViewUser(response.data); // Default to viewing own data
          
          // Load household data if user has one
          if (response.data.household_id) {
            await loadHouseholdData();
          }
        } catch (error) {
          console.error('Auth check failed:', error);
          logout(); // Clear invalid token
        }
      }
      setLoading(false);
    };

    checkAuth();
  }, [token, API]);

  const loadHouseholdData = async () => {
    try {
      const [householdResponse, membersResponse] = await Promise.all([
        axios.get(`${API}/auth/household`),
        axios.get(`${API}/auth/household/members`)
      ]);
      
      if (householdResponse.data) {
        setHousehold(householdResponse.data);
      }
      
      if (membersResponse.data) {
        setHouseholdMembers(membersResponse.data);
      }
    } catch (error) {
      console.error('Failed to load household data:', error);
    }
  };

  const login = async (email, password) => {
    try {
      const formData = new URLSearchParams();
      formData.append('username', email);
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
      
      const userData = userResponse.data;
      setUser(userData);
      setCurrentViewUser(userData);
      
      // Load household data if available
      if (userData.household_id) {
        await loadHouseholdData();
      }
      
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
    setCurrentViewUser(null);
    setHousehold(null);
    setHouseholdMembers([]);
    setViewMode('personal');
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
      
      // Load household data
      await loadHouseholdData();
      
      return { success: true, household: response.data };
    } catch (error) {
      console.error('Create household failed:', error);
      return { 
        success: false, 
        error: error.response?.data?.detail || 'Failed to create household' 
      };
    }
  };

  const switchToUser = (targetUser) => {
    setCurrentViewUser(targetUser);
    setViewMode('member');
  };

  const switchToPersonalView = () => {
    setCurrentViewUser(user);
    setViewMode('personal');
  };

  const switchToFamilyView = () => {
    setViewMode('family');
    setCurrentViewUser(null); // Family view doesn't have a specific user
  };

  const inviteHouseholdMember = async (email, role = 'user') => {
    try {
      const response = await axios.post(`${API}/auth/household/invite`, {
        email,
        role
      });
      
      // Refresh household members
      await loadHouseholdData();
      
      return { success: true, invitation: response.data };
    } catch (error) {
      console.error('Invite member failed:', error);
      return { 
        success: false, 
        error: error.response?.data?.detail || 'Failed to invite member' 
      };
    }
  };

  const getCurrentUserId = () => {
    if (viewMode === 'family') {
      return 'family_view'; // Special identifier for family view
    }
    return currentViewUser?.id || user?.id || 'default_user';
  };

  const getViewModeLabel = () => {
    switch (viewMode) {
      case 'personal':
        return `${user?.full_name}'s Data`;
      case 'member':
        return `${currentViewUser?.full_name}'s Data`;
      case 'family':
        return 'Family View';
      default:
        return 'Personal View';
    }
  };

  const value = {
    user,
    currentViewUser,
    household,
    householdMembers,
    loading,
    viewMode,
    login,
    register,
    logout,
    createHousehold,
    switchToUser,
    switchToPersonalView,
    switchToFamilyView,
    inviteHouseholdMember,
    getCurrentUserId,
    getViewModeLabel,
    isAuthenticated: !!user,
    canSwitchUsers: !!household && householdMembers.length > 1
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};