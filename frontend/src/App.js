import React, { useState, useEffect } from "react";
import "./App.css";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Dashboard Components
const Dashboard = () => {
  const [transactions, setTransactions] = useState([]);
  const [categories, setCategories] = useState([]);
  const [monthlyReports, setMonthlyReports] = useState([]);
  const [categoryBreakdown, setCategoryBreakdown] = useState([]);
  const [activeTab, setActiveTab] = useState('overview');
  const [loading, setLoading] = useState(true);
  const [uploadingPDF, setUploadingPDF] = useState(false);

  // Transaction form state
  const [newTransaction, setNewTransaction] = useState({
    date: new Date().toISOString().split('T')[0],
    description: '',
    category: 'Retail and Grocery',
    amount: '',
    account_type: 'credit_card'
  });

  // Category management state
  const [newCategory, setNewCategory] = useState({
    name: '',
    color: '#3B82F6'
  });
  const [editingCategory, setEditingCategory] = useState(null);

  // User management state (simple for now)
  const [currentUser, setCurrentUser] = useState({
    id: 'default_user',
    name: 'You',
    email: 'user@example.com'
  });

  // Filter and sorting state
  const [filters, setFilters] = useState({
    startDate: '',
    endDate: '',
    category: '',
    pdfSource: ''
  });
  const [sortConfig, setSortConfig] = useState({
    field: 'date',
    direction: 'desc'
  });
  const [pdfSources, setPdfSources] = useState([]);

  const defaultCategories = [
    'Retail and Grocery',
    'Restaurants',
    'Transportation',
    'Home and Office Improvement',
    'Hotel, Entertainment and Recreation',
    'Professional and Financial Services',
    'Health and Education',
    'Foreign Currency Transactions',
    'Personal and Household Expenses'
  ];

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [transactionsRes, monthlyRes, categoryRes, categoriesRes] = await Promise.all([
        axios.get(`${API}/transactions`),
        axios.get(`${API}/analytics/monthly-report`),
        axios.get(`${API}/analytics/category-breakdown`),
        axios.get(`${API}/categories`)
      ]);
      
      setTransactions(transactionsRes.data);
      setMonthlyReports(monthlyRes.data);
      setCategoryBreakdown(categoryRes.data);
      setCategories(categoriesRes.data);
    } catch (error) {
      console.error('Error fetching data:', error);
    }
    setLoading(false);
  };

  const handleAddTransaction = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/transactions`, {
        ...newTransaction,
        amount: parseFloat(newTransaction.amount)
      });
      
      setNewTransaction({
        date: new Date().toISOString().split('T')[0],
        description: '',
        category: categories.length > 0 ? categories[0].name : 'Retail and Grocery',
        amount: '',
        account_type: 'credit_card'
      });
      
      fetchData(); // Refresh data
    } catch (error) {
      console.error('Error adding transaction:', error);
    }
  };

  const handleDeleteTransaction = async (transactionId) => {
    try {
      await axios.delete(`${API}/transactions/${transactionId}`);
      fetchData(); // Refresh data
    } catch (error) {
      console.error('Error deleting transaction:', error);
    }
  };

  const handlePDFUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setUploadingPDF(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(`${API}/transactions/pdf-import`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      alert(`PDF processed successfully!\n${response.data.message}\nImported: ${response.data.imported_count} transactions\nDuplicates skipped: ${response.data.duplicate_count || 0}`);
      fetchData(); // Refresh data
      event.target.value = ''; // Reset file input
    } catch (error) {
      console.error('Error uploading PDF:', error);
      alert('Error processing PDF: ' + (error.response?.data?.detail || error.message));
    } finally {
      setUploadingPDF(false);
    }
  };

  const handleAddCategory = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/categories`, newCategory);
      setNewCategory({ name: '', color: '#3B82F6' });
      fetchData(); // Refresh data
    } catch (error) {
      console.error('Error adding category:', error);
    }
  };

  const handleUpdateCategory = async (categoryId, updates) => {
    try {
      await axios.put(`${API}/categories/${categoryId}`, updates);
      setEditingCategory(null);
      fetchData(); // Refresh data
    } catch (error) {
      console.error('Error updating category:', error);
    }
  };

  const handleDeleteCategory = async (categoryId) => {
    if (!window.confirm('Are you sure you want to delete this category?')) return;
    
    try {
      await axios.delete(`${API}/categories/${categoryId}`);
      fetchData(); // Refresh data
    } catch (error) {
      console.error('Error deleting category:', error);
      alert('Error: ' + (error.response?.data?.detail || error.message));
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-CA', {
      style: 'currency',
      currency: 'CAD'
    }).format(Math.abs(amount));
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-CA', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  const getMonthName = (monthStr) => {
    const [year, month] = monthStr.split('-');
    return new Date(year, month - 1).toLocaleDateString('en-CA', {
      year: 'numeric',
      month: 'long'
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">LifeTracker v2.0</h1>
              <p className="text-gray-600 mt-1">Advanced Banking & Expense Analytics</p>
            </div>
            <div className="text-right">
              <p className="text-sm text-gray-600">Total Transactions</p>
              <p className="text-2xl font-bold text-blue-600">{transactions.length}</p>
              <p className="text-xs text-gray-500">Welcome, {currentUser.name}</p>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Navigation Tabs */}
        <div className="border-b border-gray-200 mb-8">
          <nav className="-mb-px flex space-x-8">
            {[
              { id: 'overview', name: 'Overview', icon: '📊' },
              { id: 'transactions', name: 'Transactions', icon: '💳' },
              { id: 'analytics', name: 'Analytics', icon: '📈' },
              { id: 'categories', name: 'Categories', icon: '🏷️' },
              { id: 'add', name: 'Add Transaction', icon: '➕' },
              { id: 'import', name: 'Import PDF', icon: '📄' }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                } whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm flex items-center space-x-2`}
              >
                <span>{tab.icon}</span>
                <span>{tab.name}</span>
              </button>
            ))}
          </nav>
        </div>

        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <div className="space-y-8">
            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center">
                  <div className="p-2 bg-blue-100 rounded-md">
                    <span className="text-2xl">💰</span>
                  </div>
                  <div className="ml-4">
                    <p className="text-sm font-medium text-gray-600">Total Spending</p>
                    <p className="text-2xl font-bold text-gray-900">
                      {formatCurrency(categoryBreakdown.reduce((sum, cat) => sum + cat.amount, 0))}
                    </p>
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center">
                  <div className="p-2 bg-green-100 rounded-md">
                    <span className="text-2xl">📋</span>
                  </div>
                  <div className="ml-4">
                    <p className="text-sm font-medium text-gray-600">Categories</p>
                    <p className="text-2xl font-bold text-gray-900">{categories.length}</p>
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center">
                  <div className="p-2 bg-purple-100 rounded-md">
                    <span className="text-2xl">📅</span>
                  </div>
                  <div className="ml-4">
                    <p className="text-sm font-medium text-gray-600">This Month</p>
                    <p className="text-2xl font-bold text-gray-900">
                      {monthlyReports.length > 0 ? formatCurrency(monthlyReports[monthlyReports.length - 1].total_spent) : '$0.00'}
                    </p>
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center">
                  <div className="p-2 bg-yellow-100 rounded-md">
                    <span className="text-2xl">📄</span>
                  </div>
                  <div className="ml-4">
                    <p className="text-sm font-medium text-gray-600">PDF Imports</p>
                    <p className="text-2xl font-bold text-gray-900">
                      {transactions.filter(t => t.pdf_source).length}
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Monthly Spending Trend */}
            <div className="bg-white rounded-lg shadow">
              <div className="px-6 py-4 border-b border-gray-200">
                <h3 className="text-lg font-medium text-gray-900">Monthly Spending Overview</h3>
              </div>
              <div className="p-6">
                <div className="space-y-4">
                  {monthlyReports.slice(-6).map((report) => (
                    <div key={report.month} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                      <div>
                        <h4 className="font-medium text-gray-900">{getMonthName(report.month)}</h4>
                        <p className="text-sm text-gray-600">{report.transaction_count} transactions</p>
                      </div>
                      <div className="text-right">
                        <p className="text-lg font-semibold text-gray-900">{formatCurrency(report.total_spent)}</p>
                        <div className="w-32 bg-gray-200 rounded-full h-2 mt-1">
                          <div 
                            className="bg-blue-600 h-2 rounded-full" 
                            style={{
                              width: `${Math.min(100, (report.total_spent / Math.max(...monthlyReports.map(r => r.total_spent))) * 100)}%`
                            }}
                          ></div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Top Categories */}
            <div className="bg-white rounded-lg shadow">
              <div className="px-6 py-4 border-b border-gray-200">
                <h3 className="text-lg font-medium text-gray-900">Spending by Category</h3>
              </div>
              <div className="p-6">
                <div className="space-y-4">
                  {categoryBreakdown.slice(0, 5).map((category) => (
                    <div key={category.category} className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        <div className="w-4 h-4 bg-blue-500 rounded-full"></div>
                        <span className="font-medium text-gray-900">{category.category}</span>
                        <span className="text-sm text-gray-500">({category.count} transactions)</span>
                      </div>
                      <div className="text-right">
                        <span className="font-semibold text-gray-900">{formatCurrency(category.amount)}</span>
                        <span className="text-sm text-gray-500 ml-2">({category.percentage}%)</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Import PDF Tab */}
        {activeTab === 'import' && (
          <div className="max-w-2xl mx-auto">
            <div className="bg-white rounded-lg shadow">
              <div className="px-6 py-4 border-b border-gray-200">
                <h3 className="text-lg font-medium text-gray-900">📄 Import Bank Statement PDF</h3>
                <p className="text-sm text-gray-600 mt-1">Upload your bank statement PDF to automatically extract and categorize transactions</p>
              </div>
              <div className="p-6">
                <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center">
                  <div className="space-y-4">
                    <div className="text-6xl">📄</div>
                    <div>
                      <h4 className="text-lg font-medium text-gray-900">Upload PDF Statement</h4>
                      <p className="text-gray-600">Supports CIBC, TD, RBC, and most major banks</p>
                    </div>
                    <input
                      type="file"
                      accept=".pdf"
                      onChange={handlePDFUpload}
                      disabled={uploadingPDF}
                      className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 disabled:opacity-50"
                    />
                    {uploadingPDF && (
                      <div className="flex items-center justify-center space-x-2">
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                        <span className="text-blue-600">Processing PDF...</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Features List */}
                <div className="mt-6 bg-blue-50 rounded-lg p-4">
                  <h5 className="font-medium text-blue-900 mb-2">✨ Smart PDF Processing Features:</h5>
                  <ul className="text-sm text-blue-800 space-y-1">
                    <li>• Automatic transaction detection and parsing</li>
                    <li>• Smart category assignment based on merchant names</li>
                    <li>• Duplicate detection (won't import the same transaction twice)</li>
                    <li>• Support for multiple bank statement formats</li>
                    <li>• Date range detection and validation</li>
                  </ul>
                </div>

                {/* Instructions */}
                <div className="mt-6 bg-gray-50 rounded-lg p-4">
                  <h5 className="font-medium text-gray-900 mb-2">📋 Instructions:</h5>
                  <ol className="text-sm text-gray-700 space-y-1 list-decimal list-inside">
                    <li>Download your bank statement PDF from your online banking</li>
                    <li>Make sure it's a clear, text-based PDF (not a scanned image)</li>
                    <li>Upload the file using the button above</li>
                    <li>Review the imported transactions in the Transactions tab</li>
                    <li>Adjust categories if needed</li>
                  </ol>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Categories Tab */}
        {activeTab === 'categories' && (
          <div className="space-y-8">
            <div className="bg-white rounded-lg shadow">
              <div className="px-6 py-4 border-b border-gray-200">
                <h3 className="text-lg font-medium text-gray-900">Manage Categories</h3>
                <p className="text-sm text-gray-600 mt-1">Customize your expense categories</p>
              </div>
              <div className="p-6">
                {/* Add New Category Form */}
                <form onSubmit={handleAddCategory} className="mb-6 p-4 bg-gray-50 rounded-lg">
                  <div className="flex items-end space-x-4">
                    <div className="flex-1">
                      <label className="block text-sm font-medium text-gray-700 mb-1">Category Name</label>
                      <input
                        type="text"
                        value={newCategory.name}
                        onChange={(e) => setNewCategory({...newCategory, name: e.target.value})}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="Enter category name"
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Color</label>
                      <input
                        type="color"
                        value={newCategory.color}
                        onChange={(e) => setNewCategory({...newCategory, color: e.target.value})}
                        className="w-12 h-10 border border-gray-300 rounded-md"
                      />
                    </div>
                    <button
                      type="submit"
                      className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      Add Category
                    </button>
                  </div>
                </form>

                {/* Categories List */}
                <div className="space-y-3">
                  {categories.map((category) => (
                    <div key={category.id} className="flex items-center justify-between p-3 border rounded-lg hover:bg-gray-50">
                      {editingCategory === category.id ? (
                        <div className="flex items-center space-x-3 flex-1">
                          <div 
                            className="w-4 h-4 rounded-full" 
                            style={{ backgroundColor: category.color }}
                          ></div>
                          <input
                            type="text"
                            defaultValue={category.name}
                            onKeyPress={(e) => {
                              if (e.key === 'Enter') {
                                handleUpdateCategory(category.id, { name: e.target.value });
                              }
                            }}
                            className="flex-1 px-2 py-1 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                            autoFocus
                          />
                          <div className="flex space-x-2">
                            <button
                              onClick={() => handleUpdateCategory(category.id, { name: document.activeElement.value })}
                              className="text-green-600 hover:text-green-800"
                            >
                              ✓
                            </button>
                            <button
                              onClick={() => setEditingCategory(null)}
                              className="text-gray-600 hover:text-gray-800"
                            >
                              ✕
                            </button>
                          </div>
                        </div>
                      ) : (
                        <>
                          <div className="flex items-center space-x-3">
                            <div 
                              className="w-4 h-4 rounded-full" 
                              style={{ backgroundColor: category.color }}
                            ></div>
                            <span className="font-medium text-gray-900">{category.name}</span>
                            {category.is_default && (
                              <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">Default</span>
                            )}
                          </div>
                          <div className="flex space-x-2">
                            <button
                              onClick={() => setEditingCategory(category.id)}
                              className="text-blue-600 hover:text-blue-800 text-sm"
                            >
                              Edit
                            </button>
                            {!category.is_default && (
                              <button
                                onClick={() => handleDeleteCategory(category.id)}
                                className="text-red-600 hover:text-red-800 text-sm"
                              >
                                Delete
                              </button>
                            )}
                          </div>
                        </>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Transactions Tab */}
        {activeTab === 'transactions' && (
          <div className="bg-white rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
              <h3 className="text-lg font-medium text-gray-900">Recent Transactions</h3>
              <div className="text-sm text-gray-600">
                PDF Imports: {transactions.filter(t => t.pdf_source).length} | Manual: {transactions.filter(t => !t.pdf_source).length}
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Description</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Category</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Amount</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Source</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {transactions.map((transaction) => (
                    <tr key={transaction.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {formatDate(transaction.date)}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-900 max-w-xs truncate">{transaction.description}</td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-blue-100 text-blue-800">
                          {transaction.category}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {formatCurrency(transaction.amount)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-xs text-gray-500">
                        {transaction.pdf_source ? (
                          <span className="bg-green-100 text-green-800 px-2 py-1 rounded">PDF</span>
                        ) : (
                          <span className="bg-gray-100 text-gray-800 px-2 py-1 rounded">Manual</span>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                        <button
                          onClick={() => handleDeleteTransaction(transaction.id)}
                          className="text-red-600 hover:text-red-900"
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Analytics Tab - Enhanced */}
        {activeTab === 'analytics' && (
          <div className="space-y-8">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              {/* Category Breakdown */}
              <div className="bg-white rounded-lg shadow">
                <div className="px-6 py-4 border-b border-gray-200">
                  <h3 className="text-lg font-medium text-gray-900">Category Analysis</h3>
                </div>
                <div className="p-6">
                  <div className="space-y-4">
                    {categoryBreakdown.map((category, index) => (
                      <div key={category.category} className="space-y-2">
                        <div className="flex justify-between items-center">
                          <span className="text-sm font-medium text-gray-700">{category.category}</span>
                          <span className="text-sm text-gray-500">{formatCurrency(category.amount)}</span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div 
                            className={`h-2 rounded-full ${
                              index === 0 ? 'bg-blue-600' :
                              index === 1 ? 'bg-green-600' :
                              index === 2 ? 'bg-yellow-600' :
                              index === 3 ? 'bg-purple-600' : 'bg-gray-600'
                            }`}
                            style={{ width: `${category.percentage}%` }}
                          ></div>
                        </div>
                        <div className="text-xs text-gray-500">
                          {category.percentage}% • {category.count} transactions
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Monthly Comparison */}
              <div className="bg-white rounded-lg shadow">
                <div className="px-6 py-4 border-b border-gray-200">
                  <h3 className="text-lg font-medium text-gray-900">Monthly Comparison</h3>
                </div>
                <div className="p-6">
                  <div className="space-y-4">
                    {monthlyReports.slice(-6).map((report, index, arr) => {
                      const prevReport = index > 0 ? arr[index - 1] : null;
                      const change = prevReport ? 
                        ((report.total_spent - prevReport.total_spent) / prevReport.total_spent * 100) : 0;
                      
                      return (
                        <div key={report.month} className="flex items-center justify-between p-3 border rounded-lg">
                          <div>
                            <h4 className="font-medium text-gray-900">{getMonthName(report.month)}</h4>
                            <p className="text-sm text-gray-600">{report.transaction_count} transactions</p>
                          </div>
                          <div className="text-right">
                            <p className="font-semibold text-gray-900">{formatCurrency(report.total_spent)}</p>
                            {prevReport && (
                              <p className={`text-xs ${change > 0 ? 'text-red-600' : 'text-green-600'}`}>
                                {change > 0 ? '↑' : '↓'} {Math.abs(change).toFixed(1)}%
                              </p>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Add Transaction Tab */}
        {activeTab === 'add' && (
          <div className="max-w-2xl mx-auto">
            <div className="bg-white rounded-lg shadow">
              <div className="px-6 py-4 border-b border-gray-200">
                <h3 className="text-lg font-medium text-gray-900">Add New Transaction</h3>
              </div>
              <form onSubmit={handleAddTransaction} className="p-6 space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Date</label>
                    <input
                      type="date"
                      value={newTransaction.date}
                      onChange={(e) => setNewTransaction({...newTransaction, date: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Amount ($)</label>
                    <input
                      type="number"
                      step="0.01"
                      value={newTransaction.amount}
                      onChange={(e) => setNewTransaction({...newTransaction, amount: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="0.00"
                      required
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Description</label>
                  <input
                    type="text"
                    value={newTransaction.description}
                    onChange={(e) => setNewTransaction({...newTransaction, description: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Transaction description"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Category</label>
                  <select
                    value={newTransaction.category}
                    onChange={(e) => setNewTransaction({...newTransaction, category: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    {categories.map(category => (
                      <option key={category.id} value={category.name}>{category.name}</option>
                    ))}
                    {categories.length === 0 && defaultCategories.map(category => (
                      <option key={category} value={category}>{category}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Account Type</label>
                  <select
                    value={newTransaction.account_type}
                    onChange={(e) => setNewTransaction({...newTransaction, account_type: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="credit_card">Credit Card</option>
                    <option value="debit">Debit Card</option>
                    <option value="checking">Checking Account</option>
                    <option value="savings">Savings Account</option>
                  </select>
                </div>

                <div className="flex justify-end">
                  <button
                    type="submit"
                    className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    Add Transaction
                  </button>
                </div>
              </form>
            </div>

            {/* Quick Import Section */}
            <div className="mt-8 bg-white rounded-lg shadow">
              <div className="px-6 py-4 border-b border-gray-200">
                <h3 className="text-lg font-medium text-gray-900">Bulk Import CSV</h3>
                <p className="text-sm text-gray-600 mt-1">Upload a CSV file with columns: date, description, category, amount</p>
              </div>
              <div className="p-6">
                <input
                  type="file"
                  accept=".csv"
                  onChange={async (e) => {
                    const file = e.target.files[0];
                    if (file) {
                      const formData = new FormData();
                      formData.append('file', file);
                      try {
                        await axios.post(`${API}/transactions/bulk-import`, formData);
                        fetchData();
                        e.target.value = '';
                      } catch (error) {
                        console.error('Error importing CSV:', error);
                        alert('Error importing CSV file');
                      }
                    }
                  }}
                  className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                />
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

function App() {
  return (
    <div className="App">
      <Dashboard />
    </div>
  );
}

export default App;