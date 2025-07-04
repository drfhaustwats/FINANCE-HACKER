import React, { useState } from 'react';
import TransactionFlowControl from './TransactionFlowControl';

const OptimizedTransactionTable = ({
  transactions,
  selectedTransactions,
  onSelectTransaction,
  onSelectAll,
  selectAll,
  onSort,
  sortConfig,
  onEditCategory,
  onDeleteTransaction,
  editingTransactionId,
  tempTransactionCategory,
  onTempTransactionCategoryChange,
  onSaveCategoryEdit,
  onCancelCategoryEdit,
  categories,
  formatCurrency,
  formatDate,
  onUpdateTransaction  // NEW: Add transaction update handler
}) => {

  const [editingFlowId, setEditingFlowId] = useState(null);

  const getTransactionFlowIcon = (amount) => {
    return amount < 0 ? '💰' : '💸'; // Inflow vs Outflow
  };

  const getTransactionFlowLabel = (amount) => {
    return amount < 0 ? 'Inflow' : 'Outflow';
  };

  const getTransactionFlowColor = (amount) => {
    return amount < 0 ? 'text-green-600' : 'text-red-600';
  };

  const handleUpdateTransactionFlow = async (transactionId, updateData) => {
    try {
      await onUpdateTransaction(transactionId, updateData);
      setEditingFlowId(null);
    } catch (error) {
      console.error('Error updating transaction flow:', error);
      alert('Failed to update transaction flow. Please try again.');
    }
  };

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
        <h3 className="text-lg font-medium text-gray-900">
          💳 Transactions ({transactions.length})
        </h3>
        <div className="flex items-center space-x-4">
          <div className="text-sm text-gray-600 flex items-center space-x-4">
            <span className="flex items-center space-x-1">
              <span className="w-2 h-2 bg-green-500 rounded-full"></span>
              <span>Inflows: {transactions.filter(t => t.amount < 0).length}</span>
            </span>
            <span className="flex items-center space-x-1">
              <span className="w-2 h-2 bg-red-500 rounded-full"></span>
              <span>Outflows: {transactions.filter(t => t.amount > 0).length}</span>
            </span>
          </div>
        </div>
      </div>
      
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                <div className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    checked={selectAll}
                    onChange={onSelectAll}
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                  <button
                    onClick={onSelectAll}
                    className="text-xs text-blue-600 hover:text-blue-800"
                  >
                    {selectAll ? 'None' : 'All'}
                  </button>
                </div>
              </th>
              
              <th 
                onClick={() => onSort('date')}
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
              >
                📅 Date {sortConfig.field === 'date' && (sortConfig.direction === 'desc' ? '↓' : '↑')}
              </th>
              
              <th 
                onClick={() => onSort('description')}
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
              >
                📝 Description {sortConfig.field === 'description' && (sortConfig.direction === 'desc' ? '↓' : '↑')}
              </th>
              
              <th 
                onClick={() => onSort('category')}
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
              >
                🏷️ Category {sortConfig.field === 'category' && (sortConfig.direction === 'desc' ? '↓' : '↑')}
              </th>
              
              <th 
                onClick={() => onSort('amount')}
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
              >
                💰 Amount {sortConfig.field === 'amount' && (sortConfig.direction === 'desc' ? '↓' : '↑')}
              </th>
              
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                🔄 Flow
              </th>
              
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                📄 Source
              </th>
              
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                ⚙️ Actions
              </th>
            </tr>
          </thead>
          
          <tbody className="bg-white divide-y divide-gray-200">
            {transactions.map((transaction) => (
              <React.Fragment key={transaction.id}>
                <tr className={`hover:bg-gray-50 transition-colors ${selectedTransactions.has(transaction.id) ? 'bg-blue-50' : ''}`}>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <input
                      type="checkbox"
                      checked={selectedTransactions.has(transaction.id)}
                      onChange={() => onSelectTransaction(transaction.id)}
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                  </td>
                  
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {formatDate(transaction.date)}
                  </td>
                  
                  <td className="px-6 py-4 text-sm text-gray-900 max-w-xs">
                    <div className="truncate" title={transaction.description}>
                      {transaction.description}
                    </div>
                  </td>
                  
                  <td className="px-6 py-4 whitespace-nowrap">
                    {editingTransactionId === transaction.id ? (
                      <div className="flex items-center space-x-2">
                        <select
                          value={tempTransactionCategory}
                          onChange={(e) => onTempTransactionCategoryChange(e.target.value)}
                          className="text-xs border border-gray-300 rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                          {categories.map(category => (
                            <option key={category.id} value={category.name}>{category.name}</option>
                          ))}
                        </select>
                        <button
                          onClick={() => onSaveCategoryEdit(transaction.id)}
                          className="text-green-600 hover:text-green-800 text-xs"
                          title="Save"
                        >
                          ✓
                        </button>
                        <button
                          onClick={onCancelCategoryEdit}
                          className="text-red-600 hover:text-red-800 text-xs"
                          title="Cancel"
                        >
                          ✕
                        </button>
                      </div>
                    ) : (
                      <span 
                        className="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-blue-100 text-blue-800 cursor-pointer hover:bg-blue-200 transition-colors"
                        onClick={() => onEditCategory(transaction.id, transaction.category)}
                        title="Click to edit category"
                      >
                        {transaction.category}
                      </span>
                    )}
                  </td>
                  
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <span className={getTransactionFlowColor(transaction.amount)}>
                      {formatCurrency(transaction.amount)}
                    </span>
                  </td>
                  
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <div className="flex items-center space-x-2">
                      <span className="text-lg">
                        {getTransactionFlowIcon(transaction.amount)}
                      </span>
                      <span className={`text-xs font-medium px-2 py-1 rounded-full cursor-pointer hover:opacity-80 transition-opacity ${
                        transaction.amount < 0 
                          ? 'bg-green-100 text-green-800' 
                          : 'bg-red-100 text-red-800'
                      }`}
                      onClick={() => setEditingFlowId(transaction.id)}
                      title="Click to change inflow/outflow"
                      >
                        {getTransactionFlowLabel(transaction.amount)}
                      </span>
                    </div>
                  </td>
                  
                  <td className="px-6 py-4 whitespace-nowrap text-xs text-gray-500">
                    <div className="flex items-center space-x-1">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${
                        transaction.account_type === 'debit' 
                          ? 'bg-blue-100 text-blue-800' 
                          : 'bg-purple-100 text-purple-800'
                      }`}>
                        {transaction.account_type === 'debit' ? '💳 Debit' : '💰 Credit'}
                      </span>
                    </div>
                    {transaction.pdf_source && transaction.pdf_source !== 'Manual' && (
                      <div className="mt-1">
                        <span className="bg-green-100 text-green-800 px-2 py-1 rounded text-xs" title={transaction.pdf_source}>
                          📄 {transaction.pdf_source.length > 12 ? transaction.pdf_source.substring(0, 9) + '...' : transaction.pdf_source}
                        </span>
                      </div>
                    )}
                  </td>
                  
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <button
                      onClick={() => onDeleteTransaction(transaction.id)}
                      className="text-red-600 hover:text-red-900 transition-colors"
                      title="Delete transaction"
                    >
                      🗑️
                    </button>
                  </td>
                </tr>
                
                {/* Flow Control Row */}
                {editingFlowId === transaction.id && (
                  <tr>
                    <td colSpan="8" className="px-6 py-2 bg-gray-50 border-t border-gray-200">
                      <TransactionFlowControl
                        transaction={transaction}
                        onUpdate={handleUpdateTransactionFlow}
                        onCancel={() => setEditingFlowId(null)}
                      />
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default OptimizedTransactionTable;