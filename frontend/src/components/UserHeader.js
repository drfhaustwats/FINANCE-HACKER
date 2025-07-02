import React, { useState } from 'react';
import { useAuth } from '../AuthContext';

const UserHeader = () => {
  const { user, logout } = useAuth();
  const [showDropdown, setShowDropdown] = useState(false);

  const handleLogout = () => {
    logout();
    setShowDropdown(false);
  };

  return (
    <div className="bg-white shadow-sm border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo/Title */}
          <div className="flex items-center space-x-4">
            <div className="h-8 w-8 bg-blue-600 rounded-lg flex items-center justify-center">
              <span className="text-white text-lg font-bold">💰</span>
            </div>
            <h1 className="text-xl font-semibold text-gray-900">LifeTracker</h1>
          </div>

          {/* User Menu */}
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
              <svg
                className="w-4 h-4 text-gray-500"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            {/* Dropdown Menu */}
            {showDropdown && (
              <div className="absolute right-0 mt-2 w-56 bg-white rounded-md shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none z-50">
                <div className="py-1">
                  {/* User Info */}
                  <div className="px-4 py-2 border-b border-gray-100">
                    <p className="text-sm font-medium text-gray-900">{user?.full_name}</p>
                    <p className="text-sm text-gray-500">{user?.email}</p>
                    {user?.household_id && (
                      <p className="text-xs text-blue-600 mt-1">
                        👥 Household Member
                      </p>
                    )}
                  </div>

                  {/* Menu Items */}
                  <button
                    onClick={() => setShowDropdown(false)}
                    className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                  >
                    👤 Profile Settings
                  </button>
                  
                  {user?.household_id ? (
                    <button
                      onClick={() => setShowDropdown(false)}
                      className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                    >
                      🏠 Manage Household
                    </button>
                  ) : (
                    <button
                      onClick={() => setShowDropdown(false)}
                      className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                    >
                      ➕ Create Household
                    </button>
                  )}
                  
                  <div className="border-t border-gray-100">
                    <button
                      onClick={handleLogout}
                      className="block w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50"
                    >
                      🚪 Sign Out
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default UserHeader;