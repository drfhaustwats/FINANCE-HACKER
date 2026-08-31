import React, { useState } from 'react';
import { useAuth } from '../AuthContext';
import UserProfile from './UserProfile';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import SwapHorizIcon from '@mui/icons-material/SwapHoriz';
import PersonIcon from '@mui/icons-material/Person';
import GroupIcon from '@mui/icons-material/Group';
import SettingsIcon from '@mui/icons-material/Settings';
import HomeIcon from '@mui/icons-material/Home';
import LogoutIcon from '@mui/icons-material/Logout';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';

const UserHeader = () => {
  const {
    user,
    currentViewUser,
    household,
    householdMembers,
    viewMode,
    logout,
    switchToUser,
    switchToPersonalView,
    switchToFamilyView,
    getViewModeLabel,
    canSwitchUsers
  } = useAuth();

  const [showDropdown, setShowDropdown] = useState(false);
  const [showUserSwitcher, setShowUserSwitcher] = useState(false);
  const [showProfile, setShowProfile] = useState(false);

  const handleLogout = () => {
    logout();
    setShowDropdown(false);
  };

  const handleUserSwitch = (targetUser) => {
    switchToUser(targetUser);
    setShowUserSwitcher(false);
    setShowDropdown(false);
  };

  const handleViewSwitch = (mode) => {
    if (mode === 'personal') {
      switchToPersonalView();
    } else if (mode === 'family') {
      switchToFamilyView();
    }
    setShowUserSwitcher(false);
    setShowDropdown(false);
  };

  return (
    <div className="bg-white shadow-sm border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo/Title */}
          <div className="flex items-center space-x-4">
            <div className="h-8 w-8 bg-blue-600 rounded-lg flex items-center justify-center">
              <span className="text-white text-sm font-bold tracking-wide">LT</span>
            </div>
            <h1 className="text-xl font-semibold text-gray-900">LifeTracker</h1>

            {/* View Mode Indicator */}
            <div className="hidden md:flex items-center space-x-2">
              <span className="text-sm text-gray-500">Viewing:</span>
              <span className={`text-sm font-medium px-2 py-1 rounded-full ${
                viewMode === 'family'
                  ? 'bg-purple-100 text-purple-800'
                  : viewMode === 'member'
                  ? 'bg-blue-100 text-blue-800'
                  : 'bg-green-100 text-green-800'
              }`}>
                {getViewModeLabel()}
              </span>
            </div>
          </div>

          {/* User Menu */}
          <div className="flex items-center space-x-4">
            {/* User Switcher (if available) */}
            {canSwitchUsers && (
              <div className="relative">
                <button
                  onClick={() => setShowUserSwitcher(!showUserSwitcher)}
                  className="flex items-center space-x-2 text-sm bg-blue-50 rounded-md px-3 py-2 hover:bg-blue-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <SwapHorizIcon sx={{ fontSize: 18, color: '#3b82f6' }} />
                  <span className="text-blue-700 font-medium">Switch View</span>
                  <KeyboardArrowDownIcon sx={{ fontSize: 18, color: '#3b82f6' }} />
                </button>

                {/* User Switcher Dropdown */}
                {showUserSwitcher && (
                  <div className="absolute right-0 mt-2 w-64 bg-white rounded-md shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none z-50">
                    <div className="py-1">
                      {/* Personal View */}
                      <button
                        onClick={() => handleViewSwitch('personal')}
                        className={`block w-full text-left px-4 py-2 text-sm hover:bg-gray-50 ${
                          viewMode === 'personal' ? 'bg-green-50 text-green-800' : 'text-gray-700'
                        }`}
                      >
                        <div className="flex items-center space-x-2">
                          <PersonIcon sx={{ fontSize: 18 }} />
                          <span>{user?.full_name} (Your Data)</span>
                          {viewMode === 'personal' && <CheckCircleIcon sx={{ fontSize: 14, color: '#16a34a' }} />}
                        </div>
                      </button>

                      {/* Family View */}
                      <button
                        onClick={() => handleViewSwitch('family')}
                        className={`block w-full text-left px-4 py-2 text-sm hover:bg-gray-50 ${
                          viewMode === 'family' ? 'bg-purple-50 text-purple-800' : 'text-gray-700'
                        }`}
                      >
                        <div className="flex items-center space-x-2">
                          <GroupIcon sx={{ fontSize: 18 }} />
                          <span>Family Combined View</span>
                          {viewMode === 'family' && <CheckCircleIcon sx={{ fontSize: 14, color: '#9333ea' }} />}
                        </div>
                      </button>

                      <div className="border-t border-gray-100">
                        <div className="px-4 py-2 text-xs text-gray-500 font-medium">
                          FAMILY MEMBERS
                        </div>
                        {householdMembers
                          .filter(member => member.id !== user.id)
                          .map(member => (
                            <button
                              key={member.id}
                              onClick={() => handleUserSwitch(member)}
                              className={`block w-full text-left px-4 py-2 text-sm hover:bg-gray-50 ${
                                viewMode === 'member' && currentViewUser?.id === member.id
                                  ? 'bg-blue-50 text-blue-800'
                                  : 'text-gray-700'
                              }`}
                            >
                              <div className="flex items-center space-x-2">
                                <div className="w-5 h-5 bg-gray-400 rounded-full flex items-center justify-center">
                                  <span className="text-white text-xs">
                                    {member.full_name.charAt(0).toUpperCase()}
                                  </span>
                                </div>
                                <span>{member.full_name}</span>
                                {viewMode === 'member' && currentViewUser?.id === member.id && (
                                  <CheckCircleIcon sx={{ fontSize: 14, color: '#2563eb' }} />
                                )}
                              </div>
                            </button>
                          ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Main User Menu */}
            <div className="relative">
              <button
                onClick={() => setShowDropdown(!showDropdown)}
                className="flex items-center space-x-2 text-sm bg-gray-50 rounded-md px-3 py-2 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <div className="w-6 h-6 bg-blue-600 rounded-full flex items-center justify-center">
                  <span className="text-white text-xs font-medium">
                    {user?.full_name?.charAt(0).toUpperCase()}
                  </span>
                </div>
                <span className="text-gray-700 font-medium">{user?.full_name}</span>
                <KeyboardArrowDownIcon sx={{ fontSize: 18, color: '#6b7280' }} />
              </button>

              {/* Main Dropdown Menu */}
              {showDropdown && (
                <div className="absolute right-0 mt-2 w-56 bg-white rounded-md shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none z-50">
                  <div className="py-1">
                    {/* User Info */}
                    <div className="px-4 py-2 border-b border-gray-100">
                      <p className="text-sm font-medium text-gray-900">{user?.full_name}</p>
                      <p className="text-sm text-gray-500">{user?.email}</p>
                      {household && (
                        <p className="text-xs text-blue-600 mt-1">{household.name}</p>
                      )}
                    </div>

                    {/* Menu Items */}
                    <button
                      onClick={() => {
                        setShowProfile(true);
                        setShowDropdown(false);
                      }}
                      className="w-full flex items-center space-x-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                    >
                      <SettingsIcon sx={{ fontSize: 16 }} />
                      <span>Profile Settings</span>
                    </button>

                    {household ? (
                      <button
                        onClick={() => setShowDropdown(false)}
                        className="w-full flex items-center space-x-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                      >
                        <HomeIcon sx={{ fontSize: 16 }} />
                        <span>Manage Household</span>
                      </button>
                    ) : (
                      <button
                        onClick={() => setShowDropdown(false)}
                        className="w-full flex items-center space-x-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                      >
                        <HomeIcon sx={{ fontSize: 16 }} />
                        <span>Create Household</span>
                      </button>
                    )}

                    <div className="border-t border-gray-100">
                      <button
                        onClick={handleLogout}
                        className="w-full flex items-center space-x-2 px-4 py-2 text-sm text-red-600 hover:bg-red-50"
                      >
                        <LogoutIcon sx={{ fontSize: 16 }} />
                        <span>Sign Out</span>
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Profile Modal */}
      {showProfile && (
        <UserProfile onClose={() => setShowProfile(false)} />
      )}
    </div>
  );
};

export default UserHeader;
