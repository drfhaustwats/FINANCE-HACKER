import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import CloseIcon from '@mui/icons-material/Close';

const REVIEW_REASON_LABELS = {
  unresolved_legacy_transfer: 'Unresolved legacy transfer flag — older provider rule was not ownership-verified',
  ambiguous_transfer_candidate: 'Ambiguous transfer — multiple equal-amount cross-account matches found',
};

const INTERNAL_OPTIONS = [
  { value: 'auto', label: 'Automatic — use verified account pairing' },
  { value: 'internal', label: 'Internal — both accounts belong to this scope' },
  { value: 'external', label: 'External — not an internal movement' },
];

const CLASS_OPTIONS = [
  { value: 'auto', label: 'Automatic (account + provider + rules)' },
  { value: 'expense', label: 'Purchase / Expense' },
  { value: 'income', label: 'Income' },
  { value: 'refund_or_credit', label: 'Refund / Statement credit' },
  { value: 'transfer_in', label: 'External transfer in' },
  { value: 'transfer_out', label: 'External transfer out' },
  { value: 'credit_card_payment', label: 'Credit-card payment' },
  { value: 'investment_movement', label: 'Investment movement' },
];

function ReviewItem({ item, API, onResolved, formatCurrency, formatDate, readOnly }) {
  const [internalOverride, setInternalOverride] = useState(
    item.current_internal_transfer_override || 'auto'
  );
  const [classOverride, setClassOverride] = useState(
    item.current_analytics_class_override || 'auto'
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [resolved, setResolved] = useState(false);

  if (resolved) return null;

  const handleSave = async () => {
    setSaving(true);
    setError('');
    try {
      const updatePayload = {
        internal_transfer_override: internalOverride,
        // Internal-transfer takes precedence; clear stale financial-meaning if switching
        analytics_class_override: internalOverride === 'internal' ? 'auto' : classOverride,
      };
      if (item.expected_updated_at) {
        updatePayload.expected_updated_at = item.expected_updated_at;
      }
      await axios.put(`${API}/transactions/${item.transaction_id}`, updatePayload);
      setResolved(true);
      onResolved?.();
    } catch (err) {
      if (err.response?.status === 409) {
        setError('This transaction changed in another session. The review list was refreshed.');
        onResolved?.();
      } else {
        setError(err.response?.data?.detail || 'Failed to save. Try again.');
      }
    } finally {
      setSaving(false);
    }
  };

  const amountFormatted = formatCurrency(Math.abs(item.amount), item.currency || 'CAD');
  const dateFormatted = item.date ? formatDate(item.date) : item.date;

  return (
    <div className="border border-gray-200 rounded-lg p-4 space-y-3 bg-white">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div className="min-w-0">
          <p className="text-sm font-medium text-gray-900 truncate" title={item.description}>
            {item.description}
          </p>
          <p className="text-xs text-gray-500 mt-0.5">
            {dateFormatted} · {amountFormatted} · {item.category}
          </p>
        </div>
        <span className="shrink-0 text-xs font-medium px-2 py-1 rounded-full bg-amber-100 text-amber-900 whitespace-nowrap">
          {item.review_reason === 'unresolved_legacy_transfer'
            ? 'Unresolved legacy flag'
            : 'Ambiguous transfer'}
        </span>
      </div>

      <div className="text-xs text-gray-500 space-y-0.5">
        {(item.review_reasons || [item.review_reason]).map((r) => (
          <p key={r}>{REVIEW_REASON_LABELS[r] || r}</p>
        ))}
      </div>

      {readOnly ? (
        <p className="text-xs text-gray-400 italic">
          Read-only view — switch to personal view to make changes.
        </p>
      ) : (
        <div className="space-y-2 pt-1">
          <label className="block text-xs font-medium text-gray-700">
            Internal transfer handling
            <select
              value={internalOverride}
              onChange={(e) => {
                setInternalOverride(e.target.value);
                if (e.target.value === 'internal') setClassOverride('auto');
              }}
              className="mt-1 block w-full rounded border border-gray-300 bg-white px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              aria-label="Internal transfer handling"
            >
              {INTERNAL_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
            <span className="mt-0.5 block text-xs font-normal text-gray-500">
              Choose Internal only when both sides belong to identified accounts in this scope.
            </span>
          </label>

          <label className={`block text-xs font-medium text-gray-700 ${internalOverride === 'internal' ? 'opacity-40' : ''}`}>
            Financial meaning
            <select
              value={classOverride}
              onChange={(e) => setClassOverride(e.target.value)}
              disabled={internalOverride === 'internal'}
              className="mt-1 block w-full rounded border border-gray-300 bg-white px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50 disabled:cursor-not-allowed"
              aria-label="Financial meaning override"
            >
              {CLASS_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </label>

          {error && (
            <p className="text-xs text-red-600" role="alert">{error}</p>
          )}

          <button
            type="button"
            onClick={handleSave}
            disabled={saving}
            className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1"
          >
            {saving ? 'Saving…' : 'Save decision'}
          </button>
        </div>
      )}
    </div>
  );
}

const ClassificationReviewCenter = ({
  API,
  formatCurrency,
  formatDate,
  onClose,
  readOnly,
}) => {
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [unresolvedLegacyCount, setUnresolvedLegacyCount] = useState(0);
  const [ambiguousCount, setAmbiguousCount] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [fetchError, setFetchError] = useState('');
  const pageSize = 25;

  const fetchItems = useCallback(async (targetPage) => {
    setLoading(true);
    setFetchError('');
    try {
      const res = await axios.get(`${API}/analytics/classification-review`, {
        params: { page: targetPage, page_size: pageSize },
      });
      setItems(res.data.items || []);
      setTotal(res.data.total || 0);
      setUnresolvedLegacyCount(res.data.unresolved_legacy_count || 0);
      setAmbiguousCount(res.data.ambiguous_transfer_count || 0);
      setPage(targetPage);
    } catch (err) {
      setFetchError(err.response?.data?.detail || 'Failed to load review queue.');
    } finally {
      setLoading(false);
    }
  }, [API, pageSize]);

  useEffect(() => {
    fetchItems(1);
  }, [fetchItems]);

  const handleResolved = useCallback(() => {
    fetchItems(page);
  }, [fetchItems, page]);

  const totalPages = Math.ceil(total / pageSize);

  const summaryParts = [];
  if (unresolvedLegacyCount > 0) {
    summaryParts.push(
      `${unresolvedLegacyCount} unresolved legacy flag${unresolvedLegacyCount !== 1 ? 's' : ''}`
    );
  }
  if (ambiguousCount > 0) {
    summaryParts.push(
      `${ambiguousCount} ambiguous transfer candidate${ambiguousCount !== 1 ? 's' : ''}`
    );
  }
  const summaryText = summaryParts.join(' · ') || (loading ? '' : 'No items need review.');

  return (
    <section className="bg-gray-50 rounded-lg border border-gray-200 p-6 space-y-4" aria-labelledby="review-center-heading">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 id="review-center-heading" className="text-xl font-bold text-gray-900">
            Classification Review Center
          </h2>
          {summaryText && (
            <p className="text-sm text-gray-600 mt-1">{summaryText}</p>
          )}
          <p className="text-xs text-gray-500 mt-1">
            Decisions you make here are scoped to the active data view and do not affect other members' classifications.
            Internal transfers are only confirmed when both accounts are visible in this scope.
          </p>
        </div>
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            className="shrink-0 text-gray-400 hover:text-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-400 rounded"
            aria-label="Close review center"
          >
            <CloseIcon />
          </button>
        )}
      </div>

      {loading && (
        <p className="text-sm text-gray-500" aria-live="polite">Loading review queue…</p>
      )}

      {fetchError && (
        <p className="text-sm text-red-600" role="alert">{fetchError}</p>
      )}

      {!loading && !fetchError && items.length === 0 && (
        <p className="text-sm text-gray-500 py-6 text-center">
          All flagged items have been reviewed. No pending decisions remain.
        </p>
      )}

      <div className="space-y-3" aria-label="Review queue items">
        {items.map((item) => (
          <ReviewItem
            key={item.transaction_id}
            item={item}
            API={API}
            onResolved={handleResolved}
            formatCurrency={formatCurrency}
            formatDate={formatDate}
            readOnly={readOnly}
          />
        ))}
      </div>

      {totalPages > 1 && (
        <nav
          className="flex items-center justify-between pt-2"
          aria-label="Review queue pagination"
        >
          <p className="text-sm text-gray-500">
            {total} total · page {page} of {totalPages}
          </p>
          <div className="flex space-x-2">
            <button
              type="button"
              onClick={() => fetchItems(page - 1)}
              disabled={page <= 1}
              className="px-3 py-1 text-sm border border-gray-300 rounded disabled:opacity-40 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
              aria-label="Previous page"
            >
              Previous
            </button>
            <button
              type="button"
              onClick={() => fetchItems(page + 1)}
              disabled={page >= totalPages}
              className="px-3 py-1 text-sm border border-gray-300 rounded disabled:opacity-40 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
              aria-label="Next page"
            >
              Next
            </button>
          </div>
        </nav>
      )}
    </section>
  );
};

export default ClassificationReviewCenter;
