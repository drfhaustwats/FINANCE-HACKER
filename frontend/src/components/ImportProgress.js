import React, { useState, useRef, useEffect } from 'react';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import AutorenewIcon from '@mui/icons-material/Autorenew';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import RuleIcon from '@mui/icons-material/Rule';

const ImportProgress = ({ onComplete }) => {
  const [importing, setImporting] = useState(false);
  const [events, setEvents] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [categorized, setCategorized] = useState({});
  const [progress, setProgress] = useState({ current: 0, total: 0 });
  const [step, setStep] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [method, setMethod] = useState(null);
  const fileInputRef = useRef(null);
  const scrollRef = useRef(null);

  const API = process.env.REACT_APP_BACKEND_URL + '/api' || 'http://localhost:8001/api';

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [categorized]);

  const handleFileSelect = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setImporting(true);
    setEvents([]);
    setTransactions([]);
    setCategorized({});
    setProgress({ current: 0, total: 0 });
    setStep(null);
    setResult(null);
    setError(null);
    setMethod(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API}/transactions/pdf-import-stream`, {
        method: 'POST',
        headers: {
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        },
        body: formData
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop();

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              handleEvent(data);
            } catch (e) {
              // skip malformed JSON
            }
          }
        }
      }
    } catch (err) {
      setError(err.message);
    }

    setImporting(false);
    event.target.value = '';
  };

  const handleEvent = (data) => {
    setStep(data.step);
    setEvents(prev => [...prev, data]);

    switch (data.step) {
      case 'parsed':
        setTransactions(data.transactions || []);
        setProgress({ current: 0, total: data.total || 0 });
        break;

      case 'categorizing':
        setMethod(data.method);
        break;

      case 'categorized':
        setCategorized(prev => ({ ...prev, [data.index]: data.category }));
        setProgress({ current: data.progress, total: data.total });
        break;

      case 'done':
        setResult(data);
        if (onComplete) onComplete();
        break;

      case 'error':
        setError(data.message);
        break;

      default:
        break;
    }
  };

  const getStepLabel = () => {
    switch (step) {
      case 'extracting': return 'Extracting PDF text...';
      case 'parsing': return 'Parsing transactions...';
      case 'parsed': return `Found ${progress.total} transactions`;
      case 'categorizing': return method === 'llm' ? 'AI categorizing...' : 'Rule-based categorizing...';
      case 'categorized': return `Categorized ${progress.current} / ${progress.total}`;
      case 'saving': return 'Saving to database...';
      case 'done': return 'Import complete';
      case 'error': return 'Error occurred';
      default: return '';
    }
  };

  const progressPercent = progress.total > 0 ? Math.round((progress.current / progress.total) * 100) : 0;

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Upload Area */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-medium text-gray-900">Import Bank Statement</h3>
          <p className="text-sm text-gray-600 mt-1">
            Upload a PDF and {method === 'llm' || !importing ? 'AI' : 'the system'} will categorize every transaction
          </p>
        </div>
        <div className="p-6">
          <div
            className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center cursor-pointer hover:border-blue-400 transition-colors"
            onClick={() => !importing && fileInputRef.current?.click()}
          >
            {!importing ? (
              <div className="space-y-3">
                <UploadFileIcon sx={{ fontSize: 48, opacity: 0.3 }} />
                <div>
                  <p className="text-lg font-medium text-gray-900">Drop your PDF here</p>
                  <p className="text-sm text-gray-500">or click to browse</p>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                <AutorenewIcon sx={{ fontSize: 48, opacity: 0.5 }} className="animate-spin" />
                <p className="text-lg font-medium text-gray-900">{getStepLabel()}</p>
              </div>
            )}
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf"
              onChange={handleFileSelect}
              disabled={importing}
              className="hidden"
            />
          </div>
        </div>
      </div>

      {/* Progress Bar */}
      {importing && progress.total > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center space-x-2">
              {method === 'llm' ? (
                <SmartToyIcon sx={{ fontSize: 18, opacity: 0.6 }} />
              ) : (
                <RuleIcon sx={{ fontSize: 18, opacity: 0.6 }} />
              )}
              <span className="text-sm font-medium text-gray-700">
                {method === 'llm' ? 'AI Categorization' : 'Rule-Based Categorization'}
              </span>
            </div>
            <span className="text-sm text-gray-500">
              {progress.current} / {progress.total} ({progressPercent}%)
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>
      )}

      {/* Transaction List with Live Categorization */}
      {transactions.length > 0 && (
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900">
              Transactions ({transactions.length})
            </h3>
          </div>
          <div ref={scrollRef} className="max-h-96 overflow-y-auto divide-y divide-gray-100">
            {transactions.map((t, idx) => (
              <div
                key={idx}
                className={`px-6 py-3 flex items-center justify-between transition-all duration-300 ${
                  categorized[idx] ? 'bg-gray-50' : ''
                }`}
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center space-x-2">
                    {categorized[idx] ? (
                      <CheckCircleIcon sx={{ fontSize: 16, color: '#16a34a' }} />
                    ) : step === 'categorizing' || step === 'categorized' ? (
                      <AutorenewIcon sx={{ fontSize: 16, opacity: 0.4 }} className="animate-spin" />
                    ) : (
                      <div className="w-4 h-4 rounded-full border border-gray-300" />
                    )}
                    <p className="text-sm text-gray-900 truncate">{t.description}</p>
                  </div>
                  {categorized[idx] && (
                    <p className="text-xs text-blue-600 ml-6 mt-0.5">{categorized[idx]}</p>
                  )}
                </div>
                <div className="ml-4 text-right">
                  <p className={`text-sm font-medium ${t.amount < 0 ? 'text-green-600' : 'text-gray-900'}`}>
                    ${Math.abs(t.amount).toFixed(2)}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Result */}
      {result && (
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center space-x-3">
            <CheckCircleIcon sx={{ fontSize: 32, color: '#16a34a' }} />
            <div>
              <h3 className="text-lg font-medium text-gray-900">Import Complete</h3>
              <p className="text-sm text-gray-600">
                {result.imported_count} imported, {result.duplicate_count} duplicates skipped
                {result.method === 'llm' && ' (AI categorized)'}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center space-x-3">
            <ErrorIcon sx={{ fontSize: 32, color: '#dc2626' }} />
            <div>
              <h3 className="text-lg font-medium text-red-600">Import Error</h3>
              <p className="text-sm text-gray-600">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Info */}
      {!importing && !result && (
        <div className="bg-white rounded-lg shadow p-6">
          <h4 className="font-medium text-gray-900 mb-3">How it works</h4>
          <div className="space-y-2 text-sm text-gray-600">
            <div className="flex items-start space-x-3">
              <span className="text-gray-400 font-mono">1.</span>
              <span>Upload your bank statement PDF (ATB, RBC, CIBC, TD supported)</span>
            </div>
            <div className="flex items-start space-x-3">
              <span className="text-gray-400 font-mono">2.</span>
              <span>Transactions are extracted and parsed automatically</span>
            </div>
            <div className="flex items-start space-x-3">
              <span className="text-gray-400 font-mono">3.</span>
              <span>AI reads each transaction and assigns the best category</span>
            </div>
            <div className="flex items-start space-x-3">
              <span className="text-gray-400 font-mono">4.</span>
              <span>Duplicates are detected and skipped -- safe to re-import</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ImportProgress;
