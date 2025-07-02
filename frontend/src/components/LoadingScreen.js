import React from 'react';

const LoadingScreen = () => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
      <div className="text-center">
        <div className="mx-auto h-16 w-16 bg-blue-600 rounded-full flex items-center justify-center mb-4">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white"></div>
        </div>
        <h2 className="text-xl font-semibold text-gray-900 mb-2">Loading LifeTracker</h2>
        <p className="text-gray-600">Setting up your financial dashboard...</p>
      </div>
    </div>
  );
};

export default LoadingScreen;