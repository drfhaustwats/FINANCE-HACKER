import React, { useState } from 'react';
import CallMadeIcon from '@mui/icons-material/CallMade';
import CallReceivedIcon from '@mui/icons-material/CallReceived';
import CloseIcon from '@mui/icons-material/Close';

const TransactionFlowControl = ({
  transaction,
  onUpdate,
  onCancel
}) => {
  const [isInflow, setIsInflow] = useState(
    transaction.is_inflow === true
      ? true
      : transaction.is_inflow === false
        ? false
        : transaction.amount < 0
  );
  const initialInternalTransferOverride = ['auto', 'internal', 'external'].includes(
    transaction.internal_transfer_override
  )
    ? transaction.internal_transfer_override
    : ['user', 'user_scope', 'legacy_user'].includes(transaction.is_internal_transfer_source)
      ? (transaction.is_internal_transfer === true ? 'internal' : 'external')
      : 'auto';
  const [internalTransferOverride, setInternalTransferOverride] = useState(
    initialInternalTransferOverride
  );
  const [analyticsClassOverride, setAnalyticsClassOverride] = useState(
    transaction.analytics_class_override || 'auto'
  );
  const [loading, setLoading] = useState(false);
  const isProviderTransaction = Boolean(
    transaction.plaid_transaction_id
      || transaction.source_provider === 'plaid'
      || transaction.source_type === 'plaid'
  );
  const currency = transaction.iso_currency_code
    || transaction.currency
    || transaction.unofficial_currency_code
    || 'CAD';
  const formattedAmount = (() => {
    try {
      return new Intl.NumberFormat('en-CA', {
        style: 'currency',
        currency: String(currency).toUpperCase()
      }).format(Math.abs(Number(transaction.amount || 0)));
    } catch (error) {
      return `${String(currency).toUpperCase()} ${Math.abs(Number(transaction.amount || 0)).toFixed(2)}`;
    }
  })();

  const handleSave = async () => {
    setLoading(true);
    try {
      await onUpdate(transaction.id, {
        ...(!isProviderTransaction ? { is_inflow: isInflow } : {}),
        internal_transfer_override: internalTransferOverride,
        // Internal-transfer classification takes precedence on the API. Clear
        // a stale financial-meaning override instead of saving two conflicting choices.
        analytics_class_override: internalTransferOverride === 'internal' ? 'auto' : analyticsClassOverride
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white border rounded-lg p-4 shadow-lg">
      <div className="flex items-center justify-between mb-3">
        <h4 className="font-medium text-gray-900">Adjust Transaction Flow</h4>
        <button
          type="button"
          onClick={onCancel}
          className="text-gray-400 hover:text-gray-600"
        >
          <CloseIcon sx={{ fontSize: 20 }} />
        </button>
      </div>

      <div className="space-y-3">
        <div className="text-sm text-gray-600">
          <strong>{transaction.description}</strong>
          <br />
          Amount: {formattedAmount}
        </div>

        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-700">
            Ledger direction:
          </label>

          {isProviderTransaction ? (
            <div className="rounded-md border border-gray-200 bg-gray-50 p-3 text-sm text-gray-700">
              {transaction.amount < 0
                ? <CallReceivedIcon sx={{ fontSize: 18, marginRight: 1 }} />
                : <CallMadeIcon sx={{ fontSize: 18, marginRight: 1 }} />}
              {transaction.amount < 0 ? 'Credit / money in' : 'Debit / money out'}
              <p className="mt-1 text-xs text-gray-500">Direction comes from the connected account and is not rewritten by classification.</p>
            </div>
          ) : (
          <div className="space-y-2">
            <button
              type="button"
              onClick={() => setIsInflow(false)}
              className={`w-full flex items-center justify-between p-3 border rounded-lg transition-colors ${
                !isInflow
                  ? 'border-red-500 bg-red-50 text-red-800'
                  : 'border-gray-300 hover:border-red-300'
              }`}
            >
              <div className="flex items-center space-x-2">
                <CallMadeIcon sx={{ fontSize: 20 }} />
                <div className="text-left">
                  <div className="font-medium">Debit / money out</div>
                  <div className="text-xs text-gray-500">Money going out</div>
                </div>
              </div>
              {!isInflow && (
                <span className="text-red-600 font-bold">Selected</span>
              )}
            </button>

            <button
              type="button"
              onClick={() => setIsInflow(true)}
              className={`w-full flex items-center justify-between p-3 border rounded-lg transition-colors ${
                isInflow
                  ? 'border-green-500 bg-green-50 text-green-800'
                  : 'border-gray-300 hover:border-green-300'
              }`}
            >
              <div className="flex items-center space-x-2">
                <CallReceivedIcon sx={{ fontSize: 20 }} />
                <div className="text-left">
                  <div className="font-medium">Credit / money in</div>
                  <div className="text-xs text-gray-500">Money coming in</div>
                </div>
              </div>
              {isInflow && (
                <span className="text-green-600 font-bold">Selected</span>
              )}
            </button>
          </div>
          )}
        </div>

        <label className="block text-sm font-medium text-gray-700">
          Financial meaning
          <select
            value={analyticsClassOverride}
            onChange={(event) => setAnalyticsClassOverride(event.target.value)}
            disabled={internalTransferOverride === 'internal'}
            className="mt-1 block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm"
          >
            <option value="auto">Automatic (account + provider + rules)</option>
            <option value="expense">Purchase / expense</option>
            <option value="income">Income</option>
            <option value="refund_or_credit">Refund / statement credit</option>
            <option value="transfer_out">External transfer out</option>
            <option value="transfer_in">External transfer in</option>
            <option value="credit_card_payment">Credit-card payment</option>
            <option value="investment_movement">Investment movement</option>
          </select>
          <span className="mt-1 block text-xs font-normal text-gray-500">
            {internalTransferOverride === 'internal'
              ? 'Internal transfer takes precedence, so no purchase or income meaning is applied.'
              : "A saved choice overrides provider categorization but never changes the bank's raw amount."}
          </span>
        </label>

        <fieldset className="space-y-2">
          <legend className="text-sm font-medium text-gray-700">Internal transfer handling</legend>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
            {[
              { value: 'auto', label: 'Automatic', detail: 'Use verified account pairing' },
              { value: 'internal', label: 'Internal', detail: 'Both accounts are in scope' },
              { value: 'external', label: 'External', detail: 'Do not pair as internal' }
            ].map((option) => (
              <button
                key={option.value}
                type="button"
                onClick={() => {
                  setInternalTransferOverride(option.value);
                  if (option.value === 'internal') setAnalyticsClassOverride('auto');
                }}
                className={`rounded-md border px-3 py-2 text-left text-sm transition-colors ${
                  internalTransferOverride === option.value
                    ? 'border-blue-500 bg-blue-50 text-blue-900'
                    : 'border-gray-300 text-gray-700 hover:border-blue-300'
                }`}
                aria-pressed={internalTransferOverride === option.value}
              >
                <span className="block font-medium">{option.label}</span>
                <span className="block text-xs text-gray-500">{option.detail}</span>
              </button>
            ))}
          </div>
          <p className="text-xs text-gray-500">Choose Internal only when both sides belong to identified accounts in this personal or household scope.</p>
        </fieldset>

        <div className="flex space-x-2 pt-3">
          <button
            type="button"
            onClick={handleSave}
            disabled={loading}
            className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? 'Saving...' : 'Save Changes'}
          </button>
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 bg-gray-300 text-gray-700 rounded-md hover:bg-gray-400 transition-colors"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
};

export default TransactionFlowControl;
