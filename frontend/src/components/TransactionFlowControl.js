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
    transaction.amount < 0 ? true : false
  );
  const [isInternalTransfer, setIsInternalTransfer] = useState(
    transaction.is_internal_transfer === true
  );
  const [loading, setLoading] = useState(false);

  const handleSave = async () => {
    setLoading(true);
    try {
      await onUpdate(transaction.id, {
        is_inflow: isInflow,
        is_internal_transfer: isInternalTransfer
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
          Amount: ${Math.abs(transaction.amount).toFixed(2)}
        </div>

        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-700">
            Transaction Type:
          </label>

          <div className="space-y-2">
            <button
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
                  <div className="font-medium">Outflow (Expense)</div>
                  <div className="text-xs text-gray-500">Money going out</div>
                </div>
              </div>
              {!isInflow && (
                <span className="text-red-600 font-bold">Selected</span>
              )}
            </button>

            <button
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
                  <div className="font-medium">Inflow (Income/Credit)</div>
                  <div className="text-xs text-gray-500">Money coming in</div>
                </div>
              </div>
              {isInflow && (
                <span className="text-green-600 font-bold">Selected</span>
              )}
            </button>
          </div>
        </div>

        <label className="flex items-start space-x-2 text-sm text-gray-700">
          <input
            type="checkbox"
            checked={isInternalTransfer}
            onChange={(e) => setIsInternalTransfer(e.target.checked)}
            className="mt-0.5 h-4 w-4 text-blue-600 border-gray-300 rounded"
          />
          <span>
            Mark as internal transfer (excluded from spending and received analytics)
          </span>
        </label>

        <div className="flex space-x-2 pt-3">
          <button
            onClick={handleSave}
            disabled={loading}
            className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? 'Saving...' : 'Save Changes'}
          </button>
          <button
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
