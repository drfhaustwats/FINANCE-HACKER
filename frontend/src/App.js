import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';
import { AuthProvider, useAuth } from './AuthContext';
import AuthPage from './components/AuthPage';
import UserHeader from './components/UserHeader';
import LoadingScreen from './components/LoadingScreen';
import AdvancedFilters from './components/AdvancedFilters';
import OptimizedTransactionTable from './components/OptimizedTransactionTable';
import AnalyticsDashboard from './components/AnalyticsDashboard';
import Subscriptions from './components/Subscriptions';
import ImportProgress from './components/ImportProgress';
import RecategorizeProgress from './components/RecategorizeProgress';
import PlaidConnectPanel from './components/PlaidConnectPanel';
import ClassificationReviewCenter from './components/ClassificationReviewCenter';
import DashboardIcon from '@mui/icons-material/Dashboard';
import ReceiptLongIcon from '@mui/icons-material/ReceiptLong';
import BarChartIcon from '@mui/icons-material/BarChart';
import CategoryIcon from '@mui/icons-material/Category';
import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutlined';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import AutorenewIcon from '@mui/icons-material/Autorenew';
import AccountBalanceWalletIcon from '@mui/icons-material/AccountBalanceWallet';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import CalendarMonthIcon from '@mui/icons-material/CalendarMonth';
import PictureAsPdfIcon from '@mui/icons-material/PictureAsPdf';
import FileDownloadIcon from '@mui/icons-material/FileDownload';
import SyncIcon from '@mui/icons-material/Sync';
import DeleteSweepIcon from '@mui/icons-material/DeleteSweep';
import SearchIcon from '@mui/icons-material/Search';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import TipsAndUpdatesIcon from '@mui/icons-material/TipsAndUpdates';
import RadarIcon from '@mui/icons-material/Radar';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import BuildIcon from '@mui/icons-material/Build';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutlined';
import VisibilityOffIcon from '@mui/icons-material/VisibilityOff';
import RadioButtonUncheckedIcon from '@mui/icons-material/RadioButtonUnchecked';

// Main Dashboard Component (wrapped with authentication)
function Dashboard() {
  const backendBaseUrl = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';
  const API = `${backendBaseUrl}/api`;
  const { user, viewMode, getCurrentUserId, getViewModeLabel } = useAuth();
  
  const [transactions, setTransactions] = useState([]);
  const [categories, setCategories] = useState([]);
  const [monthlyReports, setMonthlyReports] = useState([]);
  const [categoryBreakdown, setCategoryBreakdown] = useState([]);
  const [dashboardSummary, setDashboardSummary] = useState(null);
  const [activeTab, setActiveTab] = useState(() => (
    typeof window !== 'undefined' && new URL(window.location.href).searchParams.has('oauth_state_id')
      ? 'import'
      : 'overview'
  ));
  const [loading, setLoading] = useState(true);
  const [uploadingPDF, setUploadingPDF] = useState(false);
  const [recategorizingTransactions, setRecategorizingTransactions] = useState(false);

  // Transaction form state
  const [newTransaction, setNewTransaction] = useState({
    date: new Date().toISOString().split('T')[0],
    description: '',
    category: '',
    amount: '',
    account_type: 'credit_card'
  });

  // Category management state
  const [newCategory, setNewCategory] = useState({
    name: '',
    color: '#3B82F6'
  });
  const [editingCategory, setEditingCategory] = useState(null);

  // Filter and sorting state
  const [filters, setFilters] = useState({
    startDate: '',
    endDate: '',
    category: '',
    pdfSource: '',
    accountType: ''
  });
  const [sortConfig, setSortConfig] = useState({
    field: 'date',
    direction: 'desc'
  });
  const [pdfSources, setPdfSources] = useState([]);

  // Bulk selection state
  const [selectedTransactions, setSelectedTransactions] = useState(new Set());
  const [selectAll, setSelectAll] = useState(false);

  // Subscription state
  const [subscriptions, setSubscriptions] = useState([]);
  const [subscriptionSummary, setSubscriptionSummary] = useState(null);

  // AI state
  const [aiInsights, setAiInsights] = useState(null);  // { items: [...] }
  const [aiInsightsLoading, setAiInsightsLoading] = useState(false);
  const [aiGenerating, setAiGenerating] = useState(false);
  const [aiSearchQuery, setAiSearchQuery] = useState('');
  const [aiSearchResults, setAiSearchResults] = useState(null);
  const [aiSearching, setAiSearching] = useState(false);
  const [detectedSubs, setDetectedSubs] = useState(null);
  const [detectingSubs, setDetectingSubs] = useState(false);
  const [subscriptionScanMeta, setSubscriptionScanMeta] = useState(null);
  const [subscriptionScanError, setSubscriptionScanError] = useState('');
  const [expandedInsight, setExpandedInsight] = useState(null);
  const [insightDetail, setInsightDetail] = useState(null);
  const [insightDetailLoading, setInsightDetailLoading] = useState(false);
  const [insightFollowUp, setInsightFollowUp] = useState('');

  // Transaction category editing state
  const [editingTransactionId, setEditingTransactionId] = useState(null);
  const [tempTransactionCategory, setTempTransactionCategory] = useState('');

  // Category editing state
  const [tempCategory, setTempCategory] = useState('');

  const defaultCategories = [
    'Retail and Grocery',
    'Restaurants',
    'Transportation',
    'Home and Office Improvement',
    'Hotel, Entertainment and Recreation',
    'Transfers and Payments',
    'Income and Payroll',
    'Banking Fees and ATM',
    'Insurance and Financial Products',
    'Investments and Brokerage',
    'Professional and Financial Services',
    'Health and Education',
    'Foreign Currency Transactions',
    'Personal and Household Expenses'
  ];

  const fetchData = async () => {
    setLoading(true);
    try {
      // Build query parameters for transactions
      const transactionParams = new URLSearchParams();
      if (filters.startDate) transactionParams.append('start_date', filters.startDate);
      if (filters.endDate) transactionParams.append('end_date', filters.endDate);
      if (filters.category) transactionParams.append('category', filters.category);
      if (filters.pdfSource) transactionParams.append('pdf_source', filters.pdfSource);
      if (filters.accountType) transactionParams.append('account_type', filters.accountType);
      transactionParams.append('sort_by', sortConfig.field);
      transactionParams.append('sort_order', sortConfig.direction);

      const currentYear = new Date().getFullYear();
      const previousYear = currentYear - 1;
      // Dashboard spending always excludes transfers and debt movements. Gross
      // account movement remains available in the reconciliation view.
      const internalTransferParam = 'false';
      const today = new Date();
      const todayKey = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
      const yearStart = `${currentYear}-01-01`;
      
      const [transactionsRes, monthlyCurrentRes, monthlyPreviousRes, summaryRes, categoryRes, categoriesRes, sourcesRes, subsRes, subSummaryRes] = await Promise.all([
        axios.get(`${API}/transactions?${transactionParams.toString()}`),
        axios.get(`${API}/analytics/monthly-report?year=${currentYear}&include_internal_transfers=${internalTransferParam}&include_pending=false`),
        axios.get(`${API}/analytics/monthly-report?year=${previousYear}&include_internal_transfers=${internalTransferParam}&include_pending=false`),
        axios.get(`${API}/analytics/dashboard-summary?year=${currentYear}&include_internal_transfers=${internalTransferParam}&include_pending=false`),
        axios.get(`${API}/analytics/category-breakdown?start_date=${yearStart}&end_date=${todayKey}&include_internal_transfers=${internalTransferParam}&include_pending=false`),
        axios.get(`${API}/categories`),
        axios.get(`${API}/transactions/sources`),
        axios.get(`${API}/subscriptions`).catch(() => ({ data: [] })),
        axios.get(`${API}/subscriptions/summary`).catch(() => ({ data: null }))
      ]);

      const mergedMonthlyReports = [
        ...(monthlyPreviousRes.data || []),
        ...(monthlyCurrentRes.data || [])
      ]
        .reduce((acc, report) => {
          acc[report.month] = report;
          return acc;
        }, {});
      const sortedMonthlyReports = Object.values(mergedMonthlyReports).sort((a, b) => a.month.localeCompare(b.month));
      
      setTransactions(transactionsRes.data);
      setMonthlyReports(sortedMonthlyReports);
      setDashboardSummary(summaryRes.data || null);
      setCategoryBreakdown(categoryRes.data);
      setCategories(categoriesRes.data);
      setPdfSources(sourcesRes.data.sources || []);
      setSubscriptions(subsRes.data || []);
      setSubscriptionSummary(subSummaryRes.data || null);

      // Load insight log (non-blocking)
      axios.get(`${API}/ai/insights`).then(res => {
        if (res.data) setAiInsights(res.data);
      }).catch(() => {});
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
        category: '',
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

  const handleBulkDelete = async () => {
    if (selectedTransactions.size === 0) {
      alert('Please select transactions to delete');
      return;
    }

    const confirmed = window.confirm(`Are you sure you want to delete ${selectedTransactions.size} selected transactions?`);
    if (!confirmed) return;

    try {
      await axios.post(`${API}/transactions/bulk-delete`, {
        transaction_ids: Array.from(selectedTransactions)
      });
      
      setSelectedTransactions(new Set());
      setSelectAll(false);
      fetchData(); // Refresh data
      alert(`Successfully deleted ${selectedTransactions.size} transactions`);
    } catch (error) {
      console.error('Error bulk deleting transactions:', error);
      alert('Error deleting transactions: ' + (error.response?.data?.detail || error.message));
    }
  };

  const handleRecategorizeTransactions = async () => {
    const confirmed = window.confirm('Re-run smart categorization for all of your existing transactions? Custom categories will be preserved.');
    if (!confirmed) return;

    setRecategorizingTransactions(true);
    try {
      const response = await axios.post(`${API}/transactions/recategorize`);
      fetchData();
      alert(`${response.data.message}\nUpdated: ${response.data.updated_count} of ${response.data.total_transactions} transactions`);
    } catch (error) {
      console.error('Error re-running categorization:', error);
      alert('Failed to re-run categorization: ' + (error.response?.data?.detail || error.message));
    } finally {
      setRecategorizingTransactions(false);
    }
  };

  const handleEditCategory = (transactionId, currentCategory) => {
    setEditingTransactionId(transactionId);
    setTempTransactionCategory(currentCategory);
  };

  const handleCancelCategoryEdit = () => {
    setEditingTransactionId(null);
    setTempTransactionCategory('');
  };

  const handleSaveCategoryEdit = async (transactionId) => {
    try {
      await axios.put(`${API}/transactions/${transactionId}`, {
        category: tempTransactionCategory
      });
      
      setEditingTransactionId(null);
      setTempTransactionCategory('');
      fetchData(); // Refresh data to show the updated category
    } catch (error) {
      console.error('Error updating category:', error);
      alert('Failed to update category. Please try again.');
    }
  };

  const handleUpdateTransaction = async (transactionId, updateData) => {
    try {
      await axios.put(`${API}/transactions/${transactionId}`, updateData);
      fetchData(); // Refresh data to show the updated transaction
    } catch (error) {
      console.error('Error updating transaction:', error);
      throw error; // Re-throw so component can handle it
    }
  };

  const handleSelectTransaction = (transactionId) => {
    const newSelected = new Set(selectedTransactions);
    if (newSelected.has(transactionId)) {
      newSelected.delete(transactionId);
    } else {
      newSelected.add(transactionId);
    }
    setSelectedTransactions(newSelected);
    setSelectAll(newSelected.size === transactions.length && transactions.length > 0);
  };

  const handleSelectAll = () => {
    if (selectAll) {
      setSelectedTransactions(new Set());
      setSelectAll(false);
    } else {
      setSelectedTransactions(new Set(transactions.map(t => t.id)));
      setSelectAll(true);
    }
  };

  // Subscription handlers
  const handleAddSubscription = async (data) => {
    try {
      await axios.post(`${API}/subscriptions`, data);
      fetchData();
    } catch (error) {
      console.error('Error adding subscription:', error);
      alert('Failed to add subscription');
    }
  };

  const handleUpdateSubscription = async (id, data) => {
    try {
      await axios.put(`${API}/subscriptions/${id}`, data);
      fetchData();
    } catch (error) {
      console.error('Error updating subscription:', error);
      alert('Failed to update subscription');
    }
  };

  const handleDeleteSubscription = async (id) => {
    if (!window.confirm('Delete this subscription?')) return;
    try {
      await axios.delete(`${API}/subscriptions/${id}`);
      fetchData();
    } catch (error) {
      console.error('Error deleting subscription:', error);
    }
  };

  // AI handlers
  const generateNewInsights = async () => {
    setAiGenerating(true);
    try {
      await axios.post(`${API}/ai/insights/generate`);
      // Reload the full list
      const response = await axios.get(`${API}/ai/insights`);
      setAiInsights(response.data);
    } catch (error) {
      console.error('Error generating insights:', error);
    }
    setAiGenerating(false);
  };

  const handleAiSearch = async (e) => {
    e.preventDefault();
    if (!aiSearchQuery.trim()) return;
    setAiSearching(true);
    try {
      const response = await axios.post(`${API}/ai/search`, { query: aiSearchQuery });
      setAiSearchResults(response.data);
    } catch (error) {
      console.error('Error with AI search:', error);
    }
    setAiSearching(false);
  };

  const handleInsightStatusChange = async (insightId, newStatus) => {
    try {
      await axios.post(`${API}/ai/insights/update-status`, { insight_id: insightId, status: newStatus });
      // Update local state
      setAiInsights(prev => {
        if (!prev) return prev;
        return {
          ...prev,
          items: prev.items?.map(item => item.id === insightId ? { ...item, status: newStatus } : item) || [],
        };
      });
      setMonthInsights(prev => prev ? {
        ...prev,
        items: prev.items?.map(item => item.id === insightId ? { ...item, status: newStatus } : item) || [],
      } : prev);
    } catch (error) {
      console.error('Error updating insight status:', error);
    }
  };

  const handleInsightDrillDown = (insight) => {
    // Switch to transactions tab and run AI search with the insight's query
    setAiSearchQuery(insight.search_query || insight.text);
    setActiveTab('transactions');
    // Trigger search
    setTimeout(async () => {
      try {
        setAiSearching(true);
        const response = await axios.post(`${API}/ai/search`, { query: insight.search_query || insight.text });
        setAiSearchResults(response.data);
      } catch (error) {
        console.error('Error with drill-down search:', error);
      }
      setAiSearching(false);
    }, 100);
  };

  const handleInsightTellMore = async (insight, insightId) => {
    if (expandedInsight === insightId) {
      setExpandedInsight(null);
      setInsightDetail(null);
      return;
    }
    setExpandedInsight(insightId);
    setInsightDetailLoading(true);
    setInsightDetail(null);

    // Check if there's already a thread saved
    const existingItem = aiInsights?.items?.find(i => i.id === insightId);
    if (existingItem?.thread?.length > 0) {
      // Show the last assistant response from the thread
      const lastAssistant = [...existingItem.thread].reverse().find(e => e.role === 'assistant');
      if (lastAssistant) {
        setInsightDetail({ ...lastAssistant.content, _thread: existingItem.thread });
        setInsightDetailLoading(false);
        return;
      }
    }

    try {
      const response = await axios.post(`${API}/ai/insight-detail`, {
        insight: insight.text || insight,
        insight_id: insightId
      });
      setInsightDetail(response.data);
    } catch (error) {
      console.error('Error getting insight detail:', error);
    }
    setInsightDetailLoading(false);
  };

  const handleInsightFollowUp = async (insight, insightId) => {
    if (!insightFollowUp.trim()) return;
    setInsightDetailLoading(true);
    try {
      const response = await axios.post(`${API}/ai/insight-detail`, {
        insight: insight.text || insight,
        insight_id: insightId,
        follow_up: insightFollowUp,
      });
      setInsightDetail(response.data);
      setInsightFollowUp('');

      // Auto-close: if resolved, update local state
      if (response.data.resolved) {
        setAiInsights(prev => ({
          ...prev,
          items: prev.items?.map(i => i.id === insightId ? { ...i, status: 'addressed' } : i)
        }));
      }

      // Reload insights to get updated thread
      const listRes = await axios.get(`${API}/ai/insights`);
      if (listRes.data) setAiInsights(listRes.data);
    } catch (error) {
      console.error('Error with follow-up:', error);
    }
    setInsightDetailLoading(false);
  };

  const handleDetectSubscriptions = async () => {
    setDetectingSubs(true);
    setDetectedSubs(null);
    setSubscriptionScanMeta(null);
    setSubscriptionScanError('');
    try {
      const response = await axios.post(`${API}/ai/detect-subscriptions`);
      setDetectedSubs(response.data.detected || []);
      setSubscriptionScanMeta({
        method: response.data.method,
        plaidStatus: response.data.plaid_recurring_status,
        transactionsAnalyzed: response.data.transactions_analyzed || 0,
        aiStatus: response.data.ai_review_status || 'not_configured',
        aiCounts: response.data.ai_review_counts || {}
      });
    } catch (error) {
      console.error('Error detecting subscriptions:', error);
      setSubscriptionScanError(error.response?.data?.detail || 'Recurring-payment scan failed. Please try again.');
    }
    setDetectingSubs(false);
  };

  const handleSaveDetectedSubs = async (subsToSave) => {
    try {
      const response = await axios.post(`${API}/ai/detect-subscriptions/save`, subsToSave);
      const savedNames = new Set((response.data.saved || []).map(name => name.trim().toLowerCase()));
      setDetectedSubs(previous => (
        previous
          ? previous.filter(candidate => !savedNames.has((candidate.name || '').trim().toLowerCase()))
          : previous
      ));
      fetchData();
    } catch (error) {
      console.error('Error saving detected subscriptions:', error);
      alert(error.response?.data?.detail || 'Failed to save detected subscriptions');
    }
  };

  const [showRecategorize, setShowRecategorize] = useState(false);
  const [showReviewCenter, setShowReviewCenter] = useState(false);
  const [selectedMonth, setSelectedMonth] = useState(null); // e.g. "2026-03"
  const [monthInsights, setMonthInsights] = useState(null);
  const [monthInsightsLoading, setMonthInsightsLoading] = useState(false);
  const viewUserId = getCurrentUserId();
  const isSharedView = viewMode !== 'personal';

  useEffect(() => {
    axios.defaults.headers.common['X-View-User-ID'] = viewUserId;
  }, [viewUserId]);

  useEffect(() => {
    if (!selectedMonth) {
      setMonthInsights(null);
      return undefined;
    }
    let cancelled = false;
    setMonthInsightsLoading(true);
    axios.get(`${API}/ai/insights/month/${selectedMonth}`)
      .then((response) => {
        if (!cancelled) setMonthInsights(response.data || { items: [] });
      })
      .catch(() => {
        if (!cancelled) setMonthInsights({ items: [] });
      })
      .finally(() => {
        if (!cancelled) setMonthInsightsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [API, selectedMonth, viewUserId]);

  useEffect(() => {
    setSelectedTransactions(new Set());
    setSelectAll(false);
    setSelectedMonth(null);
    setAiSearchResults(null);
  }, [viewUserId]);

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

  const handleSort = (field) => {
    setSortConfig(prev => ({
      field,
      direction: prev.field === field && prev.direction === 'desc' ? 'asc' : 'desc'
    }));
  };

  const handleExportToExcel = async () => {
    try {
      // Build the same query parameters as fetchData
      const params = new URLSearchParams();
      if (filters.startDate) params.append('start_date', filters.startDate);
      if (filters.endDate) params.append('end_date', filters.endDate);
      if (filters.category) params.append('category', filters.category);
      if (filters.pdfSource) params.append('pdf_source', filters.pdfSource);
      if (filters.accountType) params.append('account_type', filters.accountType);

      const response = await axios.get(`${API}/transactions/export/excel?${params.toString()}`, {
        responseType: 'blob'
      });

      // Create blob and download
      const blob = new Blob([response.data], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      });
      
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      
      // Extract filename from response headers or generate one
      const contentDisposition = response.headers['content-disposition'];
      let filename = 'lifetracker_transactions.xlsx';
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
        if (filenameMatch && filenameMatch[1]) {
          filename = filenameMatch[1].replace(/['"]/g, '');
        }
      }
      
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      alert('Excel file downloaded successfully!');
    } catch (error) {
      console.error('Error exporting to Excel:', error);
      alert('Error exporting to Excel: ' + (error.response?.data?.detail || error.message));
    }
  };

  const handleFilterChange = (filterName, value) => {
    setFilters(prev => ({
      ...prev,
      [filterName]: value
    }));
  };

  const clearFilters = () => {
    setFilters({
      startDate: '',
      endDate: '',
      category: '',
      pdfSource: '',
      accountType: ''
    });
  };

  const openTransactionsForCategory = (category, dateRange = {}) => {
    const today = new Date();
    const todayKey = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
    setFilters({
      startDate: dateRange.startDate || `${today.getFullYear()}-01-01`,
      endDate: dateRange.endDate || todayKey,
      category,
      pdfSource: '',
      accountType: ''
    });
    setAiSearchResults(null);
    setSelectedTransactions(new Set());
    setSelectAll(false);
    setSelectedMonth(null);
    setActiveTab('transactions');
  };

  const getMonthDateRange = (monthKey) => {
    const [year, month] = monthKey.split('-').map(Number);
    const today = new Date();
    const lastDay = new Date(year, month, 0);
    const effectiveEnd = lastDay > today ? today : lastDay;
    return {
      startDate: `${monthKey}-01`,
      endDate: `${effectiveEnd.getFullYear()}-${String(effectiveEnd.getMonth() + 1).padStart(2, '0')}-${String(effectiveEnd.getDate()).padStart(2, '0')}`
    };
  };

  // Auto-fetch data when filters or sorting changes
  useEffect(() => {
    fetchData();
  }, [filters, sortConfig, viewUserId]);

  const formatCurrency = (amount, currency = 'CAD') => {
    const currencyCode = String(currency || 'CAD').toUpperCase();
    try {
      return new Intl.NumberFormat('en-CA', {
        style: 'currency',
        currency: currencyCode
      }).format(Math.abs(amount));
    } catch (error) {
      return `${currencyCode} ${Math.abs(Number(amount || 0)).toFixed(2)}`;
    }
  };

  const formatDate = (dateString) => {
    // Parse date as local date to avoid timezone conversion issues
    const [year, month, day] = dateString.split('-');
    const date = new Date(parseInt(year), parseInt(month) - 1, parseInt(day));
    return date.toLocaleDateString('en-CA', {
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

  const getMonthKey = (dateObj) => {
    const year = dateObj.getFullYear();
    const month = String(dateObj.getMonth() + 1).padStart(2, '0');
    return `${year}-${month}`;
  };

  const buildRecentMonthlyReports = (reports, monthsToShow = 6) => {
    const reportByMonth = reports.reduce((acc, report) => {
      acc[report.month] = report;
      return acc;
    }, {});

    const now = new Date();
    const filled = [];
    for (let offset = monthsToShow - 1; offset >= 0; offset--) {
      const monthDate = new Date(now.getFullYear(), now.getMonth() - offset, 1);
      const monthKey = getMonthKey(monthDate);
      filled.push(
        reportByMonth[monthKey] || {
          month: monthKey,
          year: monthDate.getFullYear(),
          categories: {},
          total_spent: 0,
          total_received: 0,
          net: 0,
          transaction_count: 0
        }
      );
    }

    return filled;
  };

  const now = new Date();
  const currentMonthKey = getMonthKey(now);
  const currentMonthLabel = now.toLocaleDateString('en-CA', {
    year: 'numeric',
    month: 'long'
  });
  const monthlyReportByMonth = monthlyReports.reduce((acc, report) => {
    acc[report.month] = report;
    return acc;
  }, {});
  const currentMonthReport = monthlyReportByMonth[currentMonthKey] || {
    month: currentMonthKey,
    year: now.getFullYear(),
    categories: {},
    total_spent: 0,
    total_received: 0,
    net: 0,
    transaction_count: 0
  };
  const latestActivityReport = monthlyReports.length > 0 ? monthlyReports[monthlyReports.length - 1] : null;
  const timeAwareMonthlyReports = buildRecentMonthlyReports(monthlyReports, 6);
  const maxTimeAwareMonthlyTotal = Math.max(
    ...timeAwareMonthlyReports.map((report) => report.total_spent),
    0
  );
  const activeCategoryCount = dashboardSummary?.active_category_count
    ?? new Set((transactions || []).map((transaction) => transaction.category).filter(Boolean)).size;
  const allTransactionCount = dashboardSummary?.all_transaction_count ?? transactions.length;
  const periodTransactionCount = dashboardSummary?.transaction_count ?? transactions.length;
  const ytdSpending = dashboardSummary?.total_spent
    ?? categoryBreakdown.reduce((sum, category) => sum + Number(category.amount || 0), 0);
  const ytdIncome = dashboardSummary?.total_income ?? 0;
  const ytdRefunds = dashboardSummary?.total_refunds ?? 0;
  const ytdNet = dashboardSummary?.net ?? 0;
  const excludedMovementTotal = dashboardSummary
    ? Number(dashboardSummary.total_transfer_in || 0)
      + Number(dashboardSummary.total_transfer_out || 0)
      + Number(dashboardSummary.total_credit_card_payments || 0)
      + Number(dashboardSummary.total_investment_in || 0)
      + Number(dashboardSummary.total_investment_out || 0)
    : 0;
  const foreignCurrencyCount = Number(dashboardSummary?.foreign_currency_count || 0);
  const filterCategoryOptions = isSharedView
    ? Array.from(new Set((transactions || []).map((transaction) => transaction.category).filter(Boolean)))
        .sort((a, b) => a.localeCompare(b))
        .map((name) => ({ id: `derived-${name}`, name }))
    : categories;

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="finance-dashboard min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">LifeTracker v2.0</h1>
              <p className="text-gray-600 mt-1">Advanced Banking & Expense Analytics</p>
            </div>
            <div className="text-right">
              <p className="text-sm text-gray-600">Records in Scope</p>
              <p className="text-2xl font-bold text-blue-600">{allTransactionCount.toLocaleString()}</p>
              <p className="text-xs text-gray-500">Welcome, {user?.full_name || 'You'}</p>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Navigation Tabs */}
        <div className="border-b border-gray-200 mb-8">
          <nav className="-mb-px flex space-x-8">
            {[
              { id: 'overview', name: 'Overview', icon: <DashboardIcon sx={{ fontSize: 16 }} /> },
              { id: 'transactions', name: 'Transactions', icon: <ReceiptLongIcon sx={{ fontSize: 16 }} /> },
              { id: 'subscriptions', name: 'Subscriptions', icon: <AutorenewIcon sx={{ fontSize: 16 }} /> },
              { id: 'analytics', name: 'Analytics', icon: <BarChartIcon sx={{ fontSize: 16 }} /> },
              { id: 'categories', name: 'Categories', icon: <CategoryIcon sx={{ fontSize: 16 }} /> },
              { id: 'add', name: 'Add Transaction', icon: <AddCircleOutlineIcon sx={{ fontSize: 16 }} /> },
              { id: 'import', name: 'Import PDF', icon: <UploadFileIcon sx={{ fontSize: 16 }} /> }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                } whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm flex items-center space-x-1.5`}
              >
                {tab.icon}
                <span>{tab.name}</span>
              </button>
            ))}
          </nav>
        </div>

        {/* Overview Tab */}
        {activeTab === 'overview' && !selectedMonth && (
          <div className="space-y-6">
            {/* Summary row */}
            <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
              <div className="bg-white rounded-lg shadow p-5">
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">YTD Spending</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">
                  {formatCurrency(ytdSpending)}
                </p>
                <p className="text-xs text-gray-500">Purchases only</p>
              </div>
              <div className="bg-white rounded-lg shadow p-5">
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">YTD Income</p>
                <p className="text-2xl font-bold text-green-600 mt-1">{formatCurrency(ytdIncome)}</p>
                <p className="text-xs text-gray-500">Payroll and income</p>
              </div>
              <div className="bg-white rounded-lg shadow p-5">
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">YTD Classified Surplus</p>
                <p className={`text-2xl font-bold mt-1 ${ytdNet >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {ytdNet >= 0 ? '+' : '-'}{formatCurrency(Math.abs(ytdNet))}
                </p>
                <p className="text-xs text-gray-500">Income + {formatCurrency(ytdRefunds)} credits minus purchases</p>
              </div>
              <div className="bg-white rounded-lg shadow p-5">
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">This Month</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">{formatCurrency(currentMonthReport.total_spent)}</p>
                <p className="text-xs text-gray-500">{currentMonthLabel} spending</p>
              </div>
              <div className="bg-white rounded-lg shadow p-5">
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">Transactions</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">{allTransactionCount.toLocaleString()}</p>
                <p className="text-xs text-gray-500">{periodTransactionCount.toLocaleString()} posted {dashboardSummary?.currency || 'CAD'} YTD · {activeCategoryCount} purchase categories</p>
              </div>
            </div>
            <div className="text-sm text-gray-500">
              Data scope: <span className="font-medium text-gray-700">{getViewModeLabel()}</span>
              <span className="ml-2">· {dashboardSummary?.currency || 'CAD'} · through {dashboardSummary?.period_end || 'today'}</span>
            </div>
            {excludedMovementTotal > 0 && (
              <div className="rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-800">
                {formatCurrency(excludedMovementTotal)} of transfers, investment movements, and credit-card payments is shown separately and excluded from spending/income totals.
              </div>
            )}
            {Number(dashboardSummary?.pending_count || 0) > 0 && (
              <div className="rounded-lg border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-900">
                {Number(dashboardSummary.pending_count).toLocaleString()} pending transactions are excluded until the institution posts or removes them. Pending {dashboardSummary?.currency || 'CAD'} movement is {formatCurrency(Number(dashboardSummary.pending_money_out || 0))} out / {formatCurrency(Number(dashboardSummary.pending_money_in || 0))} in.
              </div>
            )}
            {foreignCurrencyCount > 0 && (
              <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                {foreignCurrencyCount} non-{dashboardSummary?.currency || 'CAD'} transactions are excluded from dashboard monetary totals and remain visible in the transaction table in their original currency.
              </div>
            )}
            {(Number(dashboardSummary?.classification_review_count || 0) > 0 || Number(dashboardSummary?.ambiguous_transfer_review_count || 0) > 0) && (
              <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                <div className="flex items-start justify-between gap-3 flex-wrap">
                  <div className="space-y-1">
                    {Number(dashboardSummary?.classification_review_count || 0) > 0 && (
                      <p>{Number(dashboardSummary.classification_review_count).toLocaleString()} older transfer flags remain unresolved after verified account pairing and are not treated as internal automatically.</p>
                    )}
                    {Number(dashboardSummary?.ambiguous_transfer_review_count || 0) > 0 && (
                      <p>{Number(dashboardSummary.ambiguous_transfer_review_count).toLocaleString()} entries have multiple eligible equal-amount cross-account matches. No internal pair was assumed.</p>
                    )}
                  </div>
                  <button
                    type="button"
                    onClick={() => setShowReviewCenter(true)}
                    className="shrink-0 px-3 py-1.5 text-xs font-medium bg-amber-700 text-white rounded hover:bg-amber-800 focus:outline-none focus:ring-2 focus:ring-amber-600 whitespace-nowrap"
                  >
                    Open Review Center
                  </button>
                </div>
              </div>
            )}
            {showReviewCenter && (
              <ClassificationReviewCenter
                API={API}
                formatCurrency={formatCurrency}
                formatDate={formatDate}
                onClose={() => setShowReviewCenter(false)}
                readOnly={isSharedView}
              />
            )}

            {/* Monthly Timeline */}
            <div className="bg-white rounded-lg shadow">
              <div className="px-6 py-4 border-b border-gray-200">
                <h3 className="text-lg font-medium text-gray-900">Monthly Reports</h3>
                <p className="text-xs text-gray-500 mt-1">Click a month to view details, insights, and transactions</p>
              </div>
              <div className="divide-y divide-gray-200">
                {timeAwareMonthlyReports.slice().reverse().map((report) => {
                  const transactionCount = Number(report.transaction_count || 0);
                  const inflows = Number(report.total_income ?? report.total_received ?? 0);
                  const outflows = Number(report.total_spent || 0);
                  const refunds = Number(report.total_refunds || 0);
                  const net = Number(report.net ?? (inflows + refunds - outflows));
                  const hasData = transactionCount > 0;
                  return (
                    <div
                      key={report.month}
                      onClick={() => hasData && setSelectedMonth(report.month)}
                      className={`px-6 py-5 flex items-center justify-between transition-colors ${
                        hasData ? 'cursor-pointer hover:bg-gray-50' : 'opacity-40'
                      }`}
                    >
                      <div className="flex items-center space-x-4">
                        <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center flex-shrink-0">
                          <CalendarMonthIcon sx={{ fontSize: 20, opacity: 0.6 }} />
                        </div>
                        <div>
                          <h4 className="font-medium text-gray-900">{getMonthName(report.month)}</h4>
                          <p className="text-xs text-gray-500">{transactionCount} transactions</p>
                        </div>
                      </div>
                      <div className="flex items-center space-x-6">
                        {hasData && (
                          <>
                            <div className="text-right">
                              <p className="text-xs text-gray-500">Spent</p>
                              <p className="text-sm font-semibold text-gray-900">{formatCurrency(outflows)}</p>
                            </div>
                            <div className="text-right">
                              <p className="text-xs text-gray-500">Income</p>
                              <p className="text-sm font-semibold text-green-600">{formatCurrency(inflows)}</p>
                            </div>
                            <div className="text-right">
                              <p className="text-xs text-gray-500">Net</p>
                              <p className={`text-sm font-semibold ${net >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                {net >= 0 ? '+' : '-'}{formatCurrency(Math.abs(net))}
                              </p>
                            </div>
                          </>
                        )}
                        {!hasData && <p className="text-sm text-gray-400">No data</p>}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* Month Detail View */}
        {activeTab === 'overview' && selectedMonth && (() => {
          const monthLabel = getMonthName(selectedMonth);
          const monthReport = monthlyReportByMonth[selectedMonth] || {
            total_spent: 0,
            total_received: 0,
            net: 0,
            categories: {},
            transaction_count: 0
          };
          const monthTx = transactions.filter(t => t.date?.startsWith(selectedMonth));
          const monthInflows = Number(monthReport.total_income ?? monthReport.total_received ?? 0);
          const monthRefunds = Number(monthReport.total_refunds || 0);
          const monthOutflows = Number(monthReport.total_spent || 0);
          const monthNet = Number(monthReport.net ?? (monthInflows + monthRefunds - monthOutflows));
          const monthTransactionCount = Number(monthReport.transaction_count || monthTx.length);
          const monthCatBreakdown = monthReport.categories || {};
          const sortedCats = Object.entries(monthCatBreakdown).sort((a, b) => b[1] - a[1]);
          const catTotal = sortedCats.reduce((s, [, v]) => s + v, 0);

          return (
          <div className="space-y-6">
            {/* Back button + header */}
            <div className="flex items-center space-x-4">
              <button
                onClick={() => { setSelectedMonth(null); setMonthInsights(null); }}
                className="text-sm text-blue-600 hover:text-blue-800"
              >
                &larr; All Months
              </button>
              <h2 className="text-xl font-bold text-gray-900">{monthLabel}</h2>
            </div>

            {/* Month summary cards */}
            <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
              <div className="bg-white rounded-lg shadow p-5">
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">Spent</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">{formatCurrency(monthOutflows)}</p>
              </div>
              <div className="bg-white rounded-lg shadow p-5">
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">Income</p>
                <p className="text-2xl font-bold text-green-600 mt-1">{formatCurrency(monthInflows)}</p>
              </div>
              <div className="bg-white rounded-lg shadow p-5">
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">Refunds & Credits</p>
                <p className="text-2xl font-bold text-blue-600 mt-1">{formatCurrency(monthRefunds)}</p>
              </div>
              <div className="bg-white rounded-lg shadow p-5">
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">Net</p>
                <p className={`text-2xl font-bold mt-1 ${monthNet >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {monthNet >= 0 ? '+' : '-'}{formatCurrency(Math.abs(monthNet))}
                </p>
              </div>
              <div className="bg-white rounded-lg shadow p-5">
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">Transactions</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">{monthTransactionCount.toLocaleString()}</p>
              </div>
            </div>

            {/* AI Insights for this month */}
            <div className="bg-white rounded-lg shadow">
              <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
                <div className="flex items-center space-x-2">
                  <SmartToyIcon sx={{ fontSize: 20, opacity: 0.5 }} />
                  <h3 className="text-lg font-medium text-gray-900">Insights</h3>
                  {monthInsights?.items?.length > 0 && (
                    <span className="text-xs text-gray-500">{monthInsights.items.filter(i => i.status === 'open' || !i.status).length} open</span>
                  )}
                </div>
                <button
                  onClick={async () => {
                    setMonthInsightsLoading(true);
                    try {
                      await axios.post(`${API}/ai/insights/month/${selectedMonth}/generate`);
                      const res = await axios.get(`${API}/ai/insights/month/${selectedMonth}`);
                      setMonthInsights(res.data);
                    } catch (e) { console.error(e); }
                    setMonthInsightsLoading(false);
                  }}
                  disabled={monthInsightsLoading}
                  className="flex items-center space-x-1.5 px-3 py-1.5 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-blue-300 transition-colors text-sm"
                >
                  <TipsAndUpdatesIcon sx={{ fontSize: 16 }} />
                  <span>{monthInsightsLoading ? 'Analyzing...' : monthInsights?.items?.length ? 'New Analysis' : 'Generate'}</span>
                </button>
              </div>
              <div className="p-6">
                {!monthInsights?.items?.length && !monthInsightsLoading && (
                  <p className="text-sm text-gray-500 text-center py-2">Click Generate to analyze this month</p>
                )}
                {monthInsightsLoading && (
                  <div className="flex items-center justify-center py-4 space-x-2">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                    <span className="text-xs text-gray-500">Analyzing {monthLabel}...</span>
                  </div>
                )}
                {monthInsights?.items?.length > 0 && (
                  <div className="space-y-2">
                    {monthInsights.items.map((item, idx) => {
                      const isAddr = item.status === 'addressed';
                      return (
                        <div key={item.id} className={`flex items-start space-x-3 px-3 py-2.5 rounded-lg border transition-opacity ${
                          isAddr ? 'border-green-300 opacity-50' : item.type === 'anomaly' ? 'border-gray-200' : 'border-gray-200'
                        }`} style={item.type === 'anomaly' && !isAddr ? { borderLeftWidth: '3px', borderLeftColor: '#f59e0b' } : {}}>
                          <button
                            onClick={() => handleInsightStatusChange(item.id, isAddr ? 'open' : 'addressed')}
                            className="mt-0.5 flex-shrink-0"
                          >
                            {isAddr ? <CheckCircleOutlineIcon sx={{ fontSize: 16, color: '#16a34a' }} /> : <RadioButtonUncheckedIcon sx={{ fontSize: 16, color: '#9ca3af' }} />}
                          </button>
                          <div className="flex-1">
                            <p className={`text-sm ${isAddr ? 'line-through text-gray-400' : 'text-gray-700'}`}>{item.text}</p>
                            {item.reason && <p className="text-xs text-gray-500">{item.reason}</p>}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>

            {/* Category breakdown for this month */}
            <div className="bg-white rounded-lg shadow">
              <div className="px-6 py-4 border-b border-gray-200">
                <h3 className="text-lg font-medium text-gray-900">Spending by Category</h3>
                <p className="text-xs text-gray-500 mt-1">Select a category to open this month's matching transactions.</p>
              </div>
              <div className="p-6 space-y-3">
                {sortedCats.map(([cat, amount]) => (
                  <button
                    key={cat}
                    type="button"
                    onClick={() => openTransactionsForCategory(cat, getMonthDateRange(selectedMonth))}
                    className="flex w-full items-center justify-between rounded-md px-2 py-1 text-left hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <div className="flex items-center space-x-3">
                      <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
                      <span className="text-sm font-medium text-gray-900">{cat}</span>
                    </div>
                    <div className="text-right">
                      <span className="text-sm font-semibold text-gray-900">{formatCurrency(amount)}</span>
                      <span className="text-xs text-gray-500 ml-2">({catTotal > 0 ? ((amount / catTotal) * 100).toFixed(1) : 0}%)</span>
                    </div>
                  </button>
                ))}
                {sortedCats.length === 0 && <p className="text-sm text-gray-500 text-center">No spending this month</p>}
              </div>
            </div>

            {/* Transactions for this month */}
            <OptimizedTransactionTable
              transactions={monthTx}
              selectedTransactions={selectedTransactions}
              onSelectTransaction={handleSelectTransaction}
              onSelectAll={handleSelectAll}
              selectAll={selectAll}
              onSort={handleSort}
              sortConfig={sortConfig}
              onEditCategory={handleEditCategory}
              onDeleteTransaction={handleDeleteTransaction}
              editingTransactionId={editingTransactionId}
              tempTransactionCategory={tempTransactionCategory}
              onTempTransactionCategoryChange={setTempTransactionCategory}
              onSaveCategoryEdit={handleSaveCategoryEdit}
              onCancelCategoryEdit={handleCancelCategoryEdit}
              categories={categories}
              formatCurrency={formatCurrency}
              formatDate={formatDate}
              onUpdateTransaction={handleUpdateTransaction}
              readOnly={isSharedView}
            />
          </div>
          );
        })()}

        {/* Import PDF Tab */}
        {activeTab === 'import' && (
          <div className="space-y-6">
            {isSharedView ? (
              <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                Bank connections and statement imports are available only in personal view. Switch to your own profile before changing financial data.
              </div>
            ) : (
              <>
                <PlaidConnectPanel onImported={fetchData} />
                <ImportProgress onComplete={fetchData} />
              </>
            )}
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
                              Save
                            </button>
                            <button
                              onClick={() => setEditingCategory(null)}
                              className="text-gray-600 hover:text-gray-800"
                            >
                              Cancel
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
          <div className="space-y-6">
            {/* AI Search */}
            <div className="bg-white rounded-lg shadow p-4">
              <div className="flex items-center space-x-3">
                <form onSubmit={handleAiSearch} className="flex items-center space-x-3 flex-1">
                  <SmartToyIcon sx={{ fontSize: 20, opacity: 0.5 }} />
                  <input
                    type="text"
                    value={aiSearchQuery}
                    onChange={(e) => setAiSearchQuery(e.target.value)}
                    placeholder='Ask anything... "food spending in March", "big purchases over $500", "money sent to family"'
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                  />
                  <button
                    type="submit"
                    disabled={aiSearching}
                    className="flex items-center space-x-1.5 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-blue-300 transition-colors text-sm"
                  >
                    <SearchIcon sx={{ fontSize: 16 }} />
                    <span>{aiSearching ? 'Searching...' : 'Search'}</span>
                  </button>
                  {aiSearchResults && (
                    <button
                      type="button"
                      onClick={() => { setAiSearchResults(null); setAiSearchQuery(''); }}
                      className="text-sm text-gray-500 hover:text-gray-700"
                    >
                      Clear
                    </button>
                  )}
                </form>
                <button
                  onClick={() => setShowRecategorize(true)}
                  disabled={isSharedView}
                  className="flex items-center space-x-1.5 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-blue-300 disabled:cursor-not-allowed transition-colors text-sm whitespace-nowrap"
                  title={isSharedView ? 'Switch to personal view to run recategorization.' : 'Re-categorize transactions with AI'}
                >
                  <SmartToyIcon sx={{ fontSize: 16 }} />
                  <span>AI Re-categorize</span>
                </button>
              </div>
              {aiSearchResults && (
                <div className="mt-3 pt-3 border-t border-gray-200">
                  <p className="text-sm text-gray-600 mb-2">
                    Found {aiSearchResults.count} results for "{aiSearchResults.query}"
                  </p>
                </div>
              )}
            </div>

            {/* Advanced Filters (Initially Hidden) */}
            <AdvancedFilters
              filters={filters}
              onFilterChange={handleFilterChange}
              onClearFilters={clearFilters}
              categories={filterCategoryOptions}
              pdfSources={pdfSources}
            />

            {/* Enhanced Transactions Table */}
            <OptimizedTransactionTable
              transactions={aiSearchResults ? aiSearchResults.results : transactions}
              selectedTransactions={selectedTransactions}
              onSelectTransaction={handleSelectTransaction}
              onSelectAll={handleSelectAll}
              selectAll={selectAll}
              onSort={handleSort}
              sortConfig={sortConfig}
              onEditCategory={handleEditCategory}
              onDeleteTransaction={handleDeleteTransaction}
              editingTransactionId={editingTransactionId}
              tempTransactionCategory={tempTransactionCategory}
              onTempTransactionCategoryChange={setTempTransactionCategory}
              onSaveCategoryEdit={handleSaveCategoryEdit}
              onCancelCategoryEdit={handleCancelCategoryEdit}
              categories={categories}
              formatCurrency={formatCurrency}
              formatDate={formatDate}
              onUpdateTransaction={handleUpdateTransaction}
              readOnly={isSharedView}
            />

            {/* Action Bar */}
            <div className="bg-white rounded-lg shadow p-4">
              <div className="flex justify-between items-center">
                <div className="flex items-center space-x-4">
                  <div className="text-sm text-gray-600">
                    Showing {transactions.length} transactions
                    {filters.startDate || filters.endDate || filters.category || filters.pdfSource ? ' (filtered)' : ''}
                  </div>
                </div>
                <div className="flex items-center space-x-3">
                  <button
                    onClick={handleExportToExcel}
                    className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 flex items-center space-x-1.5 transition-colors"
                  >
                    <FileDownloadIcon sx={{ fontSize: 16 }} />
                    <span>Export Excel</span>
                  </button>
                  {!isSharedView && selectedTransactions.size > 0 && (
                    <button
                      onClick={handleBulkDelete}
                      className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 transition-colors flex items-center space-x-1.5"
                    >
                      <DeleteSweepIcon sx={{ fontSize: 16 }} />
                      <span>Delete Selected ({selectedTransactions.size})</span>
                    </button>
                  )}
                </div>
              </div>
              {isSharedView && (
                <p className="text-xs text-gray-500 mt-2">Read-only in combined/member view. Switch to personal view for edits.</p>
              )}
            </div>
          </div>
        )}

        {/* Subscriptions Tab */}
        {activeTab === 'subscriptions' && (
          <Subscriptions
            subscriptions={subscriptions}
            subscriptionSummary={subscriptionSummary}
            categories={categories}
            onAdd={handleAddSubscription}
            onUpdate={handleUpdateSubscription}
            onDelete={handleDeleteSubscription}
            formatCurrency={formatCurrency}
            onDetectSubscriptions={handleDetectSubscriptions}
            onSaveDetectedSubs={handleSaveDetectedSubs}
            detectedSubs={detectedSubs}
            detectingSubs={detectingSubs}
            scanMeta={subscriptionScanMeta}
            scanError={subscriptionScanError}
            readOnly={isSharedView}
          />
        )}

        {/* Analytics Tab - Enhanced */}
        {activeTab === 'analytics' && (
          <AnalyticsDashboard
            categoryBreakdown={categoryBreakdown}
            monthlyReports={timeAwareMonthlyReports}
            dashboardSummary={dashboardSummary}
            formatCurrency={formatCurrency}
            getMonthName={getMonthName}
            onOpenCategory={(category) => openTransactionsForCategory(category)}
            onOpenReviewCenter={() => { setActiveTab('overview'); setShowReviewCenter(true); }}
          />
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
                    <option value="">Auto-detect from description</option>
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
                <p className="text-sm text-gray-600 mt-1">Upload a CSV file with columns: date, description, amount. Category is optional and will auto-detect when blank.</p>
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

      {/* AI Recategorize Modal */}
      {showRecategorize && (
        <RecategorizeProgress
          onComplete={fetchData}
          onClose={() => setShowRecategorize(false)}
          categories={categories}
        />
      )}
    </div>
  );
};

// Main App Component with Authentication
function AppContent() {
  const { user, loading } = useAuth();

  if (loading) {
    return <LoadingScreen />;
  }

  if (!user) {
    return <AuthPage />;
  }

  return (
    <div className="finance-theme min-h-screen bg-gray-50">
      <UserHeader />
      <Dashboard />
    </div>
  );
}

function App() {
  return (
    <div className="finance-theme">
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </div>
  );
}

export default App;
