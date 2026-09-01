import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';

const AuthContext = createContext();
let googleOAuthExchangePromise = null;

// Browser authentication is cookie-backed. The API lives on a sibling origin,
// so every Axios request must opt in to sending its host-only session cookie.
axios.defaults.withCredentials = true;
delete axios.defaults.headers.common['Authorization'];

// Remove credentials left by older builds without ever reading them back into JS.
if (typeof window !== 'undefined') {
  window.localStorage.removeItem('token');
}

const consumeGoogleOAuthCode = () => {
  const fragment = window.location.hash.startsWith('#')
    ? window.location.hash.slice(1)
    : window.location.hash;
  const params = new URLSearchParams(fragment);
  const code = params.get('oauth_code');

  if (!code) {
    return null;
  }

  // Remove the handoff code before making any network request or updating UI.
  params.delete('oauth_code');
  const remainingFragment = params.toString();
  const cleanUrl = `${window.location.pathname}${window.location.search}${
    remainingFragment ? `#${remainingFragment}` : ''
  }`;
  window.history.replaceState(window.history.state, document.title, cleanUrl);
  return code;
};

const getGoogleOAuthExchangePromise = (apiBaseUrl) => {
  if (googleOAuthExchangePromise) {
    return googleOAuthExchangePromise;
  }

  const code = consumeGoogleOAuthCode();
  if (!code) {
    return null;
  }

  // React StrictMode re-runs effects in development. Keep one shared promise so
  // both effect lifecycles await the same one-time exchange after the fragment
  // has already been scrubbed from the address bar.
  const exchangeRequest = axios
    .post(`${apiBaseUrl}/auth/google/exchange`, { code })
    .then(() => undefined);
  const sharedPromise = exchangeRequest.finally(() => {
    // Keep the settled promise through StrictMode's immediate effect replay,
    // but do not retain a bearer token in module memory for the page lifetime.
    window.setTimeout(() => {
      if (googleOAuthExchangePromise === sharedPromise) {
        googleOAuthExchangePromise = null;
      }
    }, 0);
  });
  googleOAuthExchangePromise = sharedPromise;
  return googleOAuthExchangePromise;
};

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
  const [googleOAuthError, setGoogleOAuthError] = useState('');
  const [viewMode, setViewMode] = useState('personal'); // 'personal', 'family', 'member'

  const API = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

  // Complete a Google callback, then ask the API whether its HttpOnly cookie is valid.
  useEffect(() => {
    let cancelled = false;

    const checkAuth = async () => {
      const googleOAuthExchange = getGoogleOAuthExchangePromise(API);

      if (googleOAuthExchange) {
        try {
          await googleOAuthExchange;
          if (!cancelled) {
            setGoogleOAuthError('');
          }
        } catch (error) {
          if (!cancelled) {
            setGoogleOAuthError(
              error.response?.data?.detail || 'Google sign-in could not be completed. Please try again.'
            );
          }
        }
      }

      try {
        const response = await axios.get(`${API}/auth/me`);
        if (!cancelled) {
          setUser(response.data);
          setCurrentViewUser(response.data); // Default to viewing own data
        }

        // Load household data if user has one
        if (response.data.household_id) {
          await loadHouseholdData();
        }
      } catch (error) {
        if (!cancelled) {
          setUser(null);
          setCurrentViewUser(null);
        }
      }
      if (!cancelled) {
        setLoading(false);
      }
    };

    checkAuth();
    return () => {
      cancelled = true;
    };
  }, [API]);

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

      await axios.post(`${API}/auth/login`, formData, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        }
      });
      
      // Get user info
      const userResponse = await axios.get(`${API}/auth/me`);
      
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

  const logout = async () => {
    googleOAuthExchangePromise = null;
    try {
      await axios.post(`${API}/auth/logout`);
    } catch (error) {
      console.error('Logout request failed:', error);
    } finally {
      setUser(null);
      setCurrentViewUser(null);
      setHousehold(null);
      setHouseholdMembers([]);
      setViewMode('personal');
      window.localStorage.removeItem('token');
      window.sessionStorage.removeItem('lifetracker_plaid_oauth_context');
      delete axios.defaults.headers.common['Authorization'];
    }
  };

  const clearGoogleOAuthError = () => setGoogleOAuthError('');

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
    googleOAuthError,
    viewMode,
    login,
    register,
    logout,
    clearGoogleOAuthError,
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
