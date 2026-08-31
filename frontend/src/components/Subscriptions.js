import React, { useState } from 'react';
import AddIcon from '@mui/icons-material/Add';
import EditIcon from '@mui/icons-material/Edit';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutlined';
import PauseCircleOutlineIcon from '@mui/icons-material/PauseCircleOutlined';
import PlayCircleOutlineIcon from '@mui/icons-material/PlayCircleOutlined';
import AutorenewIcon from '@mui/icons-material/Autorenew';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import CheckIcon from '@mui/icons-material/Check';
import CloseIcon from '@mui/icons-material/Close';
import RadarIcon from '@mui/icons-material/Radar';

const Subscriptions = ({
  subscriptions,
  subscriptionSummary,
  categories,
  onAdd,
  onUpdate,
  onDelete,
  formatCurrency,
  onDetectSubscriptions,
  onSaveDetectedSubs,
  detectedSubs,
  detectingSubs,
  readOnly = false
}) => {
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [form, setForm] = useState({
    name: '',
    amount: '',
    billing_cycle: 'monthly',
    next_billing_date: '',
    category: 'Professional and Financial Services',
    notes: ''
  });

  const resetForm = () => {
    setForm({
      name: '',
      amount: '',
      billing_cycle: 'monthly',
      next_billing_date: '',
      category: 'Professional and Financial Services',
      notes: ''
    });
    setEditingId(null);
    setShowForm(false);
  };

  const handleSubmit = async (e) => {
    if (readOnly) return;
    e.preventDefault();
    const data = { ...form, amount: parseFloat(form.amount) };
    if (editingId) {
      await onUpdate(editingId, data);
    } else {
      await onAdd(data);
    }
    resetForm();
  };

  const handleEdit = (sub) => {
    if (readOnly) return;
    setForm({
      name: sub.name,
      amount: sub.amount.toString(),
      billing_cycle: sub.billing_cycle || 'monthly',
      next_billing_date: sub.next_billing_date || '',
      category: sub.category || 'Professional and Financial Services',
      notes: sub.notes || ''
    });
    setEditingId(sub.id);
    setShowForm(true);
  };

  const handleToggleStatus = async (sub) => {
    if (readOnly) return;
    const newStatus = sub.status === 'active' ? 'paused' : 'active';
    await onUpdate(sub.id, { status: newStatus });
  };

  const getCycleLabel = (cycle) => {
    switch (cycle) {
      case 'weekly': return '/wk';
      case 'monthly': return '/mo';
      case 'yearly': return '/yr';
      default: return '/mo';
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'active': return 'bg-green-100 text-green-800';
      case 'paused': return 'bg-yellow-100 text-yellow-800';
      case 'cancelled': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const activeSubscriptions = subscriptions.filter(s => s.status === 'active');
  const inactiveSubscriptions = subscriptions.filter(s => s.status !== 'active');

  return (
    <div className="space-y-6">
      {readOnly && (
        <div className="bg-blue-50 border border-blue-200 text-blue-800 text-sm rounded-lg px-4 py-3">
          Combined/member view is read-only for subscription edits. Switch to personal view to add or modify subscriptions.
        </div>
      )}
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center space-x-3">
            <AutorenewIcon sx={{ fontSize: 24, opacity: 0.5 }} />
            <div>
              <p className="text-sm font-medium text-gray-600">Active Subscriptions</p>
              <p className="text-2xl font-bold text-gray-900">{subscriptionSummary?.active_count || 0}</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <div>
            <p className="text-sm font-medium text-gray-600">Monthly Cost</p>
            <p className="text-2xl font-bold text-gray-900">
              {formatCurrency(subscriptionSummary?.monthly_total || 0)}
            </p>
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <div>
            <p className="text-sm font-medium text-gray-600">Yearly Cost</p>
            <p className="text-2xl font-bold text-gray-900">
              {formatCurrency(subscriptionSummary?.yearly_total || 0)}
            </p>
          </div>
        </div>
      </div>

      {/* AI Auto-Detect */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
          <div className="flex items-center space-x-2">
            <SmartToyIcon sx={{ fontSize: 20, opacity: 0.6 }} />
            <h3 className="text-lg font-medium text-gray-900">Auto-Detect Subscriptions</h3>
          </div>
          <button
            onClick={onDetectSubscriptions}
            disabled={detectingSubs}
            className="flex items-center space-x-1.5 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-blue-300 transition-colors text-sm"
          >
            <RadarIcon sx={{ fontSize: 16 }} />
            <span>{detectingSubs ? 'Scanning...' : 'Scan Transactions'}</span>
          </button>
        </div>
        {detectingSubs && (
          <div className="p-6 flex items-center justify-center space-x-2">
            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600"></div>
            <span className="text-sm text-gray-600">AI is scanning your transaction history for recurring bills...</span>
          </div>
        )}
        {detectedSubs && detectedSubs.length === 0 && !detectingSubs && (
          <div className="p-6 text-center text-sm text-gray-500">
            No new subscriptions detected. Your tracked list looks complete.
          </div>
        )}
        {detectedSubs && detectedSubs.length > 0 && (
          <div className="p-6 space-y-3">
            <p className="text-sm text-gray-600 mb-3">
              Found {detectedSubs.length} potential subscriptions. Review and add:
            </p>
            {detectedSubs.map((sub, i) => (
              <div key={i} className="flex items-center justify-between p-3 border border-gray-200 rounded-lg hover:bg-gray-50">
                <div>
                  <p className="font-medium text-gray-900">{sub.name}</p>
                  <p className="text-xs text-gray-500">{sub.category} · {sub.billing_cycle}</p>
                </div>
                <div className="flex items-center space-x-3">
                  <p className="font-semibold text-gray-900">{formatCurrency(sub.amount)}/{sub.billing_cycle === 'monthly' ? 'mo' : sub.billing_cycle === 'yearly' ? 'yr' : 'wk'}</p>
                  <button
                    onClick={() => !readOnly && onSaveDetectedSubs([sub])}
                    disabled={readOnly}
                    className="text-green-600 hover:text-green-800 p-1 disabled:opacity-40 disabled:cursor-not-allowed"
                    title={readOnly ? 'Switch to personal view to save' : 'Add this subscription'}
                  >
                    <CheckIcon sx={{ fontSize: 20 }} />
                  </button>
                </div>
              </div>
            ))}
            <button
              onClick={() => !readOnly && onSaveDetectedSubs(detectedSubs)}
              disabled={readOnly}
              className="w-full mt-2 px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:bg-green-300 disabled:cursor-not-allowed transition-colors text-sm"
            >
              Add All ({detectedSubs.length})
            </button>
          </div>
        )}
      </div>

      {/* Add/Edit Form */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
          <h3 className="text-lg font-medium text-gray-900">Subscriptions</h3>
          <button
            onClick={() => !readOnly && (resetForm(), setShowForm(!showForm))}
            disabled={readOnly}
            className="flex items-center space-x-1 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-blue-300 disabled:cursor-not-allowed transition-colors text-sm"
          >
            <AddIcon sx={{ fontSize: 18 }} />
            <span>Add Subscription</span>
          </button>
        </div>

        {!readOnly && showForm && (
          <form onSubmit={handleSubmit} className="p-6 border-b border-gray-200 bg-gray-50">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Netflix, Spotify, etc."
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Amount ($)</label>
                <input
                  type="number"
                  step="0.01"
                  value={form.amount}
                  onChange={(e) => setForm({ ...form, amount: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="0.00"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Billing Cycle</label>
                <select
                  value={form.billing_cycle}
                  onChange={(e) => setForm({ ...form, billing_cycle: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="weekly">Weekly</option>
                  <option value="monthly">Monthly</option>
                  <option value="yearly">Yearly</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Next Billing Date</label>
                <input
                  type="date"
                  value={form.next_billing_date}
                  onChange={(e) => setForm({ ...form, next_billing_date: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
                <select
                  value={form.category}
                  onChange={(e) => setForm({ ...form, category: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {categories.map(cat => (
                    <option key={cat.id} value={cat.name}>{cat.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
                <input
                  type="text"
                  value={form.notes}
                  onChange={(e) => setForm({ ...form, notes: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Optional notes"
                />
              </div>
            </div>
            <div className="mt-4 flex space-x-3">
              <button
                type="submit"
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors text-sm"
              >
                {editingId ? 'Update' : 'Add'} Subscription
              </button>
              <button
                type="button"
                onClick={resetForm}
                className="px-4 py-2 bg-gray-300 text-gray-700 rounded-md hover:bg-gray-400 transition-colors text-sm"
              >
                Cancel
              </button>
            </div>
          </form>
        )}

        {/* Active Subscriptions */}
        <div className="divide-y divide-gray-200">
          {activeSubscriptions.length === 0 && inactiveSubscriptions.length === 0 && (
            <div className="p-8 text-center text-gray-500">
              No subscriptions yet. Add one to start tracking your recurring expenses.
            </div>
          )}
          {activeSubscriptions.map(sub => (
            <div key={sub.id} className="px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors">
              <div className="flex-1">
                <div className="flex items-center space-x-3">
                  <h4 className="font-medium text-gray-900">{sub.name}</h4>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${getStatusColor(sub.status)}`}>
                    {sub.status}
                  </span>
                </div>
                <div className="flex items-center space-x-4 mt-1 text-sm text-gray-500">
                  <span>{sub.category}</span>
                  {sub.next_billing_date && (
                    <span>Next: {new Date(sub.next_billing_date + 'T00:00:00').toLocaleDateString('en-CA', { month: 'short', day: 'numeric', year: 'numeric' })}</span>
                  )}
                  {sub.notes && <span>{sub.notes}</span>}
                </div>
              </div>
                <div className="flex items-center space-x-4">
                  <div className="text-right">
                    <p className="font-semibold text-gray-900">
                      {formatCurrency(sub.amount)}
                      <span className="text-xs text-gray-500 ml-1">{getCycleLabel(sub.billing_cycle)}</span>
                    </p>
                  </div>
                  <div className="flex items-center space-x-1">
                    {!readOnly && (
                      <button
                        onClick={() => handleToggleStatus(sub)}
                        className="text-yellow-600 hover:text-yellow-800 p-1"
                        title="Pause"
                      >
                        <PauseCircleOutlineIcon sx={{ fontSize: 20 }} />
                      </button>
                    )}
                    {!readOnly && (
                      <button
                        onClick={() => handleEdit(sub)}
                        className="text-blue-600 hover:text-blue-800 p-1"
                        title="Edit"
                      >
                        <EditIcon sx={{ fontSize: 20 }} />
                      </button>
                    )}
                    {!readOnly && (
                      <button
                        onClick={() => onDelete(sub.id)}
                        className="text-red-600 hover:text-red-800 p-1"
                        title="Delete"
                      >
                        <DeleteOutlineIcon sx={{ fontSize: 20 }} />
                      </button>
                    )}
                  </div>
              </div>
            </div>
          ))}
        </div>

        {/* Inactive Subscriptions */}
        {inactiveSubscriptions.length > 0 && (
          <>
            <div className="px-6 py-3 bg-gray-50 border-t border-gray-200">
              <h4 className="text-sm font-medium text-gray-500">Paused / Cancelled</h4>
            </div>
            <div className="divide-y divide-gray-200 opacity-60">
              {inactiveSubscriptions.map(sub => (
                <div key={sub.id} className="px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3">
                      <h4 className="font-medium text-gray-900">{sub.name}</h4>
                      <span className={`text-xs px-2 py-0.5 rounded-full ${getStatusColor(sub.status)}`}>
                        {sub.status}
                      </span>
                    </div>
                    <p className="text-sm text-gray-500 mt-1">{sub.category}</p>
                  </div>
                  <div className="flex items-center space-x-4">
                    <p className="font-semibold text-gray-900">
                      {formatCurrency(sub.amount)}
                      <span className="text-xs text-gray-500 ml-1">{getCycleLabel(sub.billing_cycle)}</span>
                    </p>
                    <div className="flex items-center space-x-1">
                      {!readOnly && (
                        <button
                          onClick={() => handleToggleStatus(sub)}
                          className="text-green-600 hover:text-green-800 p-1"
                          title="Resume"
                        >
                          <PlayCircleOutlineIcon sx={{ fontSize: 20 }} />
                        </button>
                      )}
                      {!readOnly && (
                        <button
                          onClick={() => onDelete(sub.id)}
                          className="text-red-600 hover:text-red-800 p-1"
                          title="Delete"
                        >
                          <DeleteOutlineIcon sx={{ fontSize: 20 }} />
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default Subscriptions;
