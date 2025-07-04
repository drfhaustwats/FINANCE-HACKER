import React, { useState } from 'react';

const AdvancedFilters = ({ 
  filters, 
  onFilterChange, 
  onClearFilters, 
  categories, 
  pdfSources 
}) => {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="bg-white rounded-lg shadow">
      {/* Collapsed Header */}
      <div 
        className="px-6 py-4 border-b border-gray-200 flex justify-between items-center cursor-pointer hover:bg-gray-50 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center space-x-3">
          <h3 className="text-lg font-medium text-gray-900">🔍 Filters & Search</h3>
          {Object.values(filters).some(v => v) && (
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
              {Object.values(filters).filter(v => v).length} active
            </span>
          )}
        </div>
        <div className="flex items-center space-x-2">
          {Object.values(filters).some(v => v) && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onClearFilters();
              }}
              className="text-sm text-red-600 hover:text-red-800 px-2 py-1 rounded"
            >
              Clear All
            </button>
          )}
          <span className={`transform transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`}>
            ▼
          </span>
        </div>
      </div>

      {/* Expanded Filters */}
      {isExpanded && (
        <div className="p-6 bg-gray-50">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Start Date</label>
              <input
                type="date"
                value={filters.startDate}
                onChange={(e) => onFilterChange('startDate', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">End Date</label>
              <input
                type="date"
                value={filters.endDate}
                onChange={(e) => onFilterChange('endDate', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
              <select
                value={filters.category}
                onChange={(e) => onFilterChange('category', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">All Categories</option>
                {categories.map(cat => (
                  <option key={cat.id} value={cat.name}>{cat.name}</option>
                ))}
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Account Type</label>
              <select
                value={filters.accountType}
                onChange={(e) => onFilterChange('accountType', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">All Types</option>
                <option value="credit_card">Credit Card</option>
                <option value="debit">Debit Account</option>
              </select>
            </div>
          </div>

          {/* Quick Filter Buttons */}
          <div className="mt-4 flex flex-wrap gap-2">
            <button
              onClick={() => {
                const now = new Date();
                const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1);
                onFilterChange('startDate', startOfMonth.toISOString().split('T')[0]);
                onFilterChange('endDate', now.toISOString().split('T')[0]);
              }}
              className="px-3 py-1 text-xs bg-blue-100 text-blue-800 rounded-full hover:bg-blue-200 transition-colors"
            >
              This Month
            </button>
            <button
              onClick={() => {
                const now = new Date();
                const lastMonth = new Date(now.getFullYear(), now.getMonth() - 1, 1);
                const endOfLastMonth = new Date(now.getFullYear(), now.getMonth(), 0);
                onFilterChange('startDate', lastMonth.toISOString().split('T')[0]);
                onFilterChange('endDate', endOfLastMonth.toISOString().split('T')[0]);
              }}
              className="px-3 py-1 text-xs bg-green-100 text-green-800 rounded-full hover:bg-green-200 transition-colors"
            >
              Last Month
            </button>
            <button
              onClick={() => {
                const now = new Date();
                const threeMonthsAgo = new Date(now.getFullYear(), now.getMonth() - 3, 1);
                onFilterChange('startDate', threeMonthsAgo.toISOString().split('T')[0]);
                onFilterChange('endDate', now.toISOString().split('T')[0]);
              }}
              className="px-3 py-1 text-xs bg-purple-100 text-purple-800 rounded-full hover:bg-purple-200 transition-colors"
            >
              Last 3 Months
            </button>
            <button
              onClick={() => {
                const now = new Date();
                const startOfYear = new Date(now.getFullYear(), 0, 1);
                onFilterChange('startDate', startOfYear.toISOString().split('T')[0]);
                onFilterChange('endDate', now.toISOString().split('T')[0]);
              }}
              className="px-3 py-1 text-xs bg-yellow-100 text-yellow-800 rounded-full hover:bg-yellow-200 transition-colors"
            >
              This Year
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdvancedFilters;