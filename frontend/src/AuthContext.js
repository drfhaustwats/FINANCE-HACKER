import React, { createContext, useContext, useState } from 'react';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

// Mock data for testing analytics layout
const mockUser = {
  id: 1,
  full_name: 'Test User',
  email: 'test@example.com',
  household_id: 1
};

const mockHousehold = {
  id: 1,
  name: 'Test Household'
};

const mockHouseholdMembers = [
  mockUser,
  {
    id: 2,
    full_name: 'Family Member',
    email: 'family@example.com',
    household_id: 1
  }
];

export const AuthProvider = ({ children }) => {
  const [user] = useState(mockUser);
  const [currentViewUser] = useState(mockUser);
  const [household] = useState(mockHousehold);
  const [householdMembers] = useState(mockHouseholdMembers);
  const [loading] = useState(false);
  const [viewMode, setViewMode] = useState('personal');

  // Simplified mock functions
  const login = async () => ({ success: true });
  const register = async () => ({ success: true });
  const logout = () => {};
  const createHousehold = async () => ({ success: true });
  
  const switchToUser = (targetUser) => {
    setViewMode('member');
  };

  const switchToPersonalView = () => {
    setViewMode('personal');
  };

  const switchToFamilyView = () => {
    setViewMode('family');
  };

  const inviteHouseholdMember = async () => ({ success: true });

  const getCurrentUserId = () => {
    if (viewMode === 'family') {
      return 'family_view';
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
    isAuthenticated: true, // Always authenticated for testing
    canSwitchUsers: true
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
