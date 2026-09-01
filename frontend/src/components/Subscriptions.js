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
  scanMeta,
  scanError,
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
      case 'biweekly': return '/2wk';
      case 'semi_monthly': return '2×/mo';
      case 'monthly': return '/mo';
      case 'yearly': return '/yr';
      default: return '/mo';
    }
  };

  const getCandidateCurrency = (sub) => String(sub.currency || 'CAD').toUpperCase();

  const showHistoricalAverage = (sub) => {
    if (sub.average_amount === null || sub.average_amount === undefined) return false;
    return sub.amount_is_variable === true
      || Math.abs(Number(sub.average_amount) - Number(sub.amount)) >= 0.01;
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
  const aiReviewComplete = ['reviewed', 'reviewed_truncated'].includes(scanMeta?.aiStatus);
  const aiCounts = scanMeta?.aiCounts || {};
  const aiRejectedCount = Math.max(
    0,
    Number(aiCounts.reviewed || 0) - Number(aiCounts.kept || 0)
  );
  const formatAiLabel = (label) => {
    if (label === 'recurring_bill') return 'Recurring bill';
    if (label === 'subscription') return 'Subscription';
    return 'Manual review';
  };

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

      {/* Recurring-payment detection and conservative AI review */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
          <div className="flex items-center space-x-2">
            <SmartToyIcon sx={{ fontSize: 20, opacity: 0.6 }} />
            <div>
              <h3 className="text-lg font-medium text-gray-900">Recurring Payment Scan</h3>
              <p className="text-xs text-gray-500">Plaid and local patterns find candidates; Claude reviews them before you approve.</p>
            </div>
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
            <span className="text-sm text-gray-600">Analyzing transaction cadence for recurring bills...</span>
          </div>
        )}
        {scanError && !detectingSubs && (
          <div className="mx-6 mt-5 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {scanError}
          </div>
        )}
        {scanMeta && !detectingSubs && (
          <div className="mx-6 mt-5 rounded-md border border-blue-100 bg-blue-50 px-4 py-3 text-xs text-blue-800">
            <p>
              Analyzed {scanMeta.transactionsAnalyzed.toLocaleString()} transactions.{' '}
              {scanMeta.plaidStatus === 'available' && 'Plaid recurring data was checked.'}
              {scanMeta.plaidStatus === 'disabled' && 'Plaid recurring is disabled; results use local patterns.'}
              {scanMeta.plaidStatus === 'access_required' && 'Plaid recurring access was unavailable; local patterns were used.'}
              {scanMeta.plaidStatus === 'partial_timeout' && 'Plaid returned a partial result; local patterns are included.'}
              {scanMeta.plaidStatus === 'temporarily_unavailable' && 'Plaid was temporarily unavailable; local patterns are included.'}
              {scanMeta.plaidStatus === 'policy_changed' && 'Account permissions changed during the scan; rescan to refresh Plaid results.'}
            </p>
            {aiReviewComplete && (
              <p className="mt-1 font-medium">
                Claude reviewed {Number(aiCounts.reviewed || 0).toLocaleString()} candidates: kept {Number(aiCounts.kept || 0).toLocaleString()} and rejected {aiRejectedCount.toLocaleString()} (including {Number(aiCounts.uncertain || 0).toLocaleString()} uncertain).
                {Number(aiCounts.truncated || 0) > 0 && ` ${Number(aiCounts.truncated).toLocaleString()} additional candidates were withheld by the safety limit.`}
              </p>
            )}
            {scanMeta.aiStatus === 'not_configured' && (
              <p className="mt-1 font-medium">Claude review is not configured. Results below are deterministic candidates for individual manual review.</p>
            )}
            {scanMeta.aiStatus === 'provider_unavailable' && (
              <p className="mt-1 font-medium">Claude was unavailable. No AI-review claim was applied; review each deterministic candidate individually.</p>
            )}
            {scanMeta.aiStatus === 'invalid_response' && (
              <p className="mt-1 font-medium">Claude returned an invalid review, so it was discarded. Review each deterministic candidate individually.</p>
            )}
            {Number(aiCounts.deterministic_vetoed || 0) > 0 && (
              <p className="mt-1 font-medium">Structural rules rejected {Number(aiCounts.deterministic_vetoed).toLocaleString()} transfer or income candidates before AI review.</p>
            )}
          </div>
        )}
        {detectedSubs && detectedSubs.length === 0 && !detectingSubs && (
          <div className="p-6 text-center text-sm text-gray-500">
            No recurring payment candidates met the current confidence threshold.
          </div>
        )}
        {detectedSubs && detectedSubs.length > 0 && (
          <div className="p-6 space-y-3">
            <p className="text-sm text-gray-600 mb-3">
              {aiReviewComplete
                ? `Claude kept ${detectedSubs.length} likely subscriptions or recurring bills. Review before adding:`
                : `Found ${detectedSubs.length} deterministic candidates. Review each one before adding:`}
            </p>
            {detectedSubs.map((sub, i) => (
              <div key={i} className="flex items-center justify-between p-3 border border-gray-200 rounded-lg hover:bg-gray-50">
                <div>
                  <p className="font-medium text-gray-900">{sub.name}</p>
                  <p className="text-xs text-gray-500">
                    {sub.category} · {sub.billing_cycle}
                    {sub.occurrences ? ` · ${sub.occurrences} occurrences` : ''}
                    {sub.confidence ? ` · ${Math.round(sub.confidence * 100)}% confidence` : ''}
                  </p>
                  <span className={`inline-flex mt-1 rounded-full px-2 py-0.5 text-[11px] font-medium ${sub.detection_source === 'plaid_recurring' ? 'bg-indigo-100 text-indigo-700' : 'bg-gray-100 text-gray-700'}`}>
                    {sub.detection_source === 'plaid_recurring' ? 'Plaid recurring' : 'Local pattern'}
                  </span>
                  <span className={`inline-flex mt-1 ml-1 rounded-full px-2 py-0.5 text-[11px] font-medium ${sub.ai_label ? 'bg-violet-100 text-violet-700' : 'bg-amber-100 text-amber-800'}`}>
                    {sub.ai_label
                      ? `Claude: ${formatAiLabel(sub.ai_label)}${sub.ai_confidence !== undefined ? ` (${Math.round(Number(sub.ai_confidence) * 100)}%)` : ''}`
                      : 'Manual review'}
                  </span>
                  {sub.ai_reason && (
                    <p className="mt-1 text-xs text-violet-700">{sub.ai_reason}</p>
                  )}
                </div>
                <div className="flex items-center space-x-3">
                  <div className="text-right">
                    <p className="text-[11px] text-gray-500">Current estimate</p>
                    <p className="font-semibold text-gray-900">
                      {getCandidateCurrency(sub)} {formatCurrency(sub.amount, getCandidateCurrency(sub))}{getCycleLabel(sub.billing_cycle)}
                    </p>
                    {showHistoricalAverage(sub) && (
                      <p className="text-[11px] text-gray-500">
                        Historical avg: {getCandidateCurrency(sub)} {formatCurrency(sub.average_amount, getCandidateCurrency(sub))}
                        {sub.amount_is_variable === true ? ' · variable' : ''}
                      </p>
                    )}
                  </div>
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
            {aiReviewComplete && (
              <button
                onClick={() => !readOnly && onSaveDetectedSubs(detectedSubs)}
                disabled={readOnly}
                className="w-full mt-2 px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:bg-green-300 disabled:cursor-not-allowed transition-colors text-sm"
              >
                Add All Claude-Kept ({detectedSubs.length})
              </button>
            )}
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
                  <option value="biweekly">Every two weeks</option>
                  <option value="semi_monthly">Twice monthly</option>
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
