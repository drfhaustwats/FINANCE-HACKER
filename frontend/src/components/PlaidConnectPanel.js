import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { usePlaidLink } from 'react-plaid-link';
import AccountBalanceIcon from '@mui/icons-material/AccountBalance';
import LinkIcon from '@mui/icons-material/Link';
import SyncIcon from '@mui/icons-material/Sync';
import DeleteOutlineOutlinedIcon from '@mui/icons-material/DeleteOutlineOutlined';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import CheckCircleOutlinedIcon from '@mui/icons-material/CheckCircleOutlined';

const backendBaseUrl = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';
const API = `${backendBaseUrl}/api`;

const PlaidConnectPanel = ({ onImported }) => {
  const [status, setStatus] = useState(null); // { type: 'success'|'error'|'info', text: string }
  const [plaidStatus, setPlaidStatus] = useState(null);
  const [connections, setConnections] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadingLinkToken, setLoadingLinkToken] = useState(false);
  const [linkToken, setLinkToken] = useState(null);
  const [syncingKey, setSyncingKey] = useState(null); // item_id | 'all'
  const [disconnectingItemId, setDisconnectingItemId] = useState(null);

  const refreshConnections = async () => {
    try {
      const response = await axios.get(`${API}/plaid/connections`);
      setConnections(response.data?.items || []);
    } catch (error) {
      console.error('Failed to load Plaid connections:', error);
    }
  };

  const loadPlaidStatus = async () => {
    try {
      const response = await axios.get(`${API}/plaid/status`);
      setPlaidStatus(response.data || null);
    } catch (error) {
      console.error('Failed to load Plaid status:', error);
      setPlaidStatus(null);
    }
  };

  const createLinkToken = async () => {
    setLoadingLinkToken(true);
    try {
      const response = await axios.post(`${API}/plaid/link-token/create`);
      setLinkToken(response.data?.link_token || null);
    } catch (error) {
      console.error('Failed to create Plaid link token:', error);
      setStatus({
        type: 'error',
        text: error.response?.data?.detail || 'Unable to initialize Plaid Link.',
      });
      setLinkToken(null);
    } finally {
      setLoadingLinkToken(false);
    }
  };

  useEffect(() => {
    const bootstrap = async () => {
      setLoading(true);
      await Promise.all([loadPlaidStatus(), refreshConnections()]);
      setLoading(false);
    };
    bootstrap();
  }, []);

  useEffect(() => {
    if (plaidStatus?.enabled) {
      createLinkToken();
    } else {
      setLinkToken(null);
    }
  }, [plaidStatus?.enabled]);

  const { open, ready, error: plaidLinkError } = usePlaidLink({
    token: linkToken || null,
    onSuccess: async (publicToken) => {
      setStatus({ type: 'info', text: 'Connecting account and importing transactions...' });
      try {
        const response = await axios.post(`${API}/plaid/exchange-public-token`, {
          public_token: publicToken,
        });
        const sync = response.data?.sync || {};
        setStatus({
          type: 'success',
          text: `Connected. Added ${sync.added_count || 0}, merged ${sync.merged_count || 0}, updated ${sync.modified_count || 0}.`,
        });
        await refreshConnections();
        if (onImported) {
          onImported();
        }
      } catch (exchangeError) {
        console.error('Plaid exchange failed:', exchangeError);
        setStatus({
          type: 'error',
          text: exchangeError.response?.data?.detail || 'Failed to connect account.',
        });
      } finally {
        createLinkToken();
      }
    },
    onExit: (exitError) => {
      if (exitError) {
        setStatus({
          type: 'error',
          text: exitError.display_message || exitError.error_message || 'Plaid Link exited with an error.',
        });
      }
    },
  });

  useEffect(() => {
    if (!plaidLinkError) return;
    setStatus({
      type: 'error',
      text: plaidLinkError.display_message || plaidLinkError.error_message || 'Plaid Link initialization failed.',
    });
  }, [plaidLinkError]);

  const handleConnect = () => {
    if (!plaidStatus?.enabled) {
      setStatus({
        type: 'error',
        text: 'Plaid is not configured on the backend yet.',
      });
      return;
    }
    if (!ready) {
      setStatus({
        type: 'info',
        text: loadingLinkToken ? 'Preparing Plaid Link...' : 'Plaid Link is not ready yet. Try again in a moment.',
      });
      return;
    }
    open();
  };

  const handleSync = async (itemId = null) => {
    const syncKey = itemId || 'all';
    setSyncingKey(syncKey);
    setStatus({ type: 'info', text: itemId ? 'Syncing account...' : 'Syncing all connected accounts...' });
    try {
      const response = await axios.post(`${API}/plaid/sync`, itemId ? { item_id: itemId } : {});
      setStatus({
        type: 'success',
        text: `Sync complete. Added ${response.data?.total_added || 0}, merged ${response.data?.total_merged || 0}, updated ${response.data?.total_modified || 0}.`,
      });
      await refreshConnections();
      if (onImported) {
        onImported();
      }
    } catch (error) {
      console.error('Plaid sync failed:', error);
      setStatus({
        type: 'error',
        text: error.response?.data?.detail || 'Sync failed.',
      });
    } finally {
      setSyncingKey(null);
    }
  };

  const handleDisconnect = async (itemId) => {
    const confirmed = window.confirm('Disconnect this bank account? Imported transactions will remain unless you remove them manually.');
    if (!confirmed) return;

    setDisconnectingItemId(itemId);
    try {
      await axios.delete(`${API}/plaid/item/${itemId}`);
      setStatus({ type: 'success', text: 'Bank connection removed.' });
      await refreshConnections();
    } catch (error) {
      console.error('Failed to disconnect Plaid item:', error);
      setStatus({
        type: 'error',
        text: error.response?.data?.detail || 'Failed to remove connection.',
      });
    } finally {
      setDisconnectingItemId(null);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <AccountBalanceIcon sx={{ fontSize: 20, opacity: 0.6 }} />
          <div>
            <h3 className="text-lg font-medium text-gray-900">Connect Bank (Plaid)</h3>
            <p className="text-sm text-gray-600">Secure sync for transactions without PDF uploads.</p>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={() => handleSync()}
            disabled={syncingKey === 'all' || connections.length === 0}
            className="px-3 py-2 text-sm border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-1.5"
          >
            <SyncIcon sx={{ fontSize: 16 }} className={syncingKey === 'all' ? 'animate-spin' : ''} />
            <span>{syncingKey === 'all' ? 'Syncing...' : 'Sync All'}</span>
          </button>
          <button
            onClick={handleConnect}
            disabled={!plaidStatus?.enabled || !ready || loadingLinkToken}
            className="px-3 py-2 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-blue-300 disabled:cursor-not-allowed flex items-center space-x-1.5"
          >
            <LinkIcon sx={{ fontSize: 16 }} />
            <span>{loadingLinkToken ? 'Preparing...' : 'Connect Bank'}</span>
          </button>
        </div>
      </div>

      <div className="p-6 space-y-4">
        {loading && <p className="text-sm text-gray-500">Loading Plaid status...</p>}

        {!loading && !plaidStatus?.enabled && (
          <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800 flex items-start space-x-2">
            <WarningAmberIcon sx={{ fontSize: 16, marginTop: '2px' }} />
            <span>
              Plaid is not configured on the backend. Add `PLAID_CLIENT_ID`, `PLAID_SECRET`, and `PLAID_ENV` to backend env.
            </span>
          </div>
        )}

        {status && (
          <div className={`rounded-md px-3 py-2 text-sm flex items-start space-x-2 ${
            status.type === 'error'
              ? 'bg-red-50 text-red-700 border border-red-200'
              : status.type === 'success'
                ? 'bg-green-50 text-green-700 border border-green-200'
                : 'bg-blue-50 text-blue-700 border border-blue-200'
          }`}>
            {status.type === 'success' ? (
              <CheckCircleOutlinedIcon sx={{ fontSize: 16, marginTop: '2px' }} />
            ) : (
              <WarningAmberIcon sx={{ fontSize: 16, marginTop: '2px' }} />
            )}
            <span>{status.text}</span>
          </div>
        )}

        <div className="space-y-2">
          {connections.length === 0 && (
            <p className="text-sm text-gray-500">No bank connections yet.</p>
          )}
          {connections.map((connection) => (
            <div key={connection.item_id} className="border border-gray-200 rounded-lg p-3 flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-900">{connection.institution_name || 'Connected Bank'}</p>
                <p className="text-xs text-gray-500">
                  {connection.account_count || 0} accounts
                  {connection.last_successful_sync ? ` • Last sync ${new Date(connection.last_successful_sync).toLocaleString()}` : ''}
                </p>
                {connection.status === 'error' && connection.last_error && (
                  <p className="text-xs text-red-600 mt-1">{connection.last_error}</p>
                )}
              </div>
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => handleSync(connection.item_id)}
                  disabled={syncingKey === connection.item_id}
                  className="px-2.5 py-1.5 text-xs border border-gray-300 rounded text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-1"
                >
                  <SyncIcon sx={{ fontSize: 14 }} className={syncingKey === connection.item_id ? 'animate-spin' : ''} />
                  <span>{syncingKey === connection.item_id ? 'Syncing' : 'Sync'}</span>
                </button>
                <button
                  onClick={() => handleDisconnect(connection.item_id)}
                  disabled={disconnectingItemId === connection.item_id}
                  className="px-2.5 py-1.5 text-xs border border-red-200 rounded text-red-600 hover:bg-red-50 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-1"
                >
                  <DeleteOutlineOutlinedIcon sx={{ fontSize: 14 }} />
                  <span>{disconnectingItemId === connection.item_id ? 'Removing' : 'Disconnect'}</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default PlaidConnectPanel;
