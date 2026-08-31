import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import CloseIcon from '@mui/icons-material/Close';

import EditIcon from '@mui/icons-material/Edit';

const RecategorizeProgress = ({ onComplete, onClose, categories = [] }) => {
  const [running, setRunning] = useState(false);
  const [changes, setChanges] = useState([]);
  const [selected, setSelected] = useState(new Set());
  const [progress, setProgress] = useState({ current: 0, total: 0 });
  const [done, setDone] = useState(false);
  const [applied, setApplied] = useState(false);
  const [applying, setApplying] = useState(false);
  const [error, setError] = useState(null);
  const [editingIdx, setEditingIdx] = useState(null);
  const [userInput, setUserInput] = useState('');
  const [resolving, setResolving] = useState(false);
  const scrollRef = useRef(null);

  const API = process.env.REACT_APP_BACKEND_URL + '/api' || 'http://localhost:8001/api';

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [changes]);

  const startRecategorize = async () => {
    setRunning(true);
    setChanges([]);
    setSelected(new Set());
    setProgress({ current: 0, total: 0 });
    setDone(false);
    setApplied(false);
    setError(null);

    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API}/ai/recategorize`, {
        method: 'POST',
        headers: { ...(token ? { 'Authorization': `Bearer ${token}` } : {}) }
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done: streamDone, value } = await reader.read();
        if (streamDone) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop();

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              handleEvent(data);
            } catch (e) { /* skip */ }
          }
        }
      }
    } catch (err) {
      setError(err.message);
    }
    setRunning(false);
  };

  const handleEvent = (data) => {
    switch (data.step) {
      case 'starting':
        setProgress({ current: 0, total: data.total });
        break;
      case 'analyzing':
      case 'progress':
        setProgress({ current: data.progress, total: data.total });
        break;
      case 'proposed':
        setChanges(prev => {
          const next = [...prev, data.change];
          // Auto-select all by default
          setSelected(prevSel => {
            const nextSel = new Set(prevSel);
            nextSel.add(next.length - 1);
            return nextSel;
          });
          return next;
        });
        setProgress({ current: data.progress, total: data.total });
        break;
      case 'done':
        setDone(true);
        break;
      default:
        break;
    }
  };

  const toggleChange = (index) => {
    setSelected(prev => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  };

  const selectAll = () => {
    setSelected(new Set(changes.map((_, i) => i)));
  };

  const selectNone = () => {
    setSelected(new Set());
  };

  const overrideCategory = (index, newCategory) => {
    setChanges(prev => prev.map((c, i) => i === index ? { ...c, new_category: newCategory, reason: 'User override' } : c));
    setEditingIdx(null);
    setUserInput('');
  };

  const handleUserSuggestion = async (index) => {
    if (!userInput.trim()) return;
    setResolving(true);
    try {
      const change = changes[index];
      const response = await axios.post(`${API}/ai/resolve-category`, {
        description: change.description,
        user_input: userInput,
        current_category: change.new_category,
      });
      const resolved = response.data;
      setChanges(prev => prev.map((c, i) => i === index ? {
        ...c,
        new_category: resolved.category,
        reason: resolved.reason || `User: "${userInput}"`
      } : c));
      setEditingIdx(null);
      setUserInput('');
    } catch (err) {
      // Fallback: just use user input as-is to find closest match
      const match = categories.find(c => c.name.toLowerCase().includes(userInput.toLowerCase()));
      if (match) {
        overrideCategory(index, match.name);
      }
    }
    setResolving(false);
  };

  const applyChanges = async () => {
    const selectedChanges = changes.filter((_, i) => selected.has(i));
    if (selectedChanges.length === 0) return;

    setApplying(true);
    try {
      await axios.post(`${API}/ai/recategorize/apply`, { changes: selectedChanges });
      setApplied(true);
      if (onComplete) onComplete();
    } catch (err) {
      setError('Failed to apply changes: ' + (err.response?.data?.detail || err.message));
    }
    setApplying(false);
  };

  const progressPercent = progress.total > 0 ? Math.round((progress.current / progress.total) * 100) : 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ backgroundColor: 'rgba(0,0,0,0.6)' }}>
      <div className="relative bg-white rounded-lg shadow-lg w-full max-w-2xl mx-4 max-h-[85vh] flex flex-col" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-gray-200 flex-shrink-0">
          <div className="flex items-center space-x-2">
            <SmartToyIcon sx={{ fontSize: 22, opacity: 0.6 }} />
            <h2 className="text-lg font-semibold text-gray-900">AI Re-categorize</h2>
          </div>
          {!running && (
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
              <CloseIcon sx={{ fontSize: 22 }} />
            </button>
          )}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-hidden flex flex-col min-h-0">
          {/* Not started */}
          {!running && !done && changes.length === 0 && !applied && (
            <div className="p-8 text-center">
              <SmartToyIcon sx={{ fontSize: 48, opacity: 0.15 }} />
              <h3 className="text-lg font-medium text-gray-900 mt-4">Re-categorize with AI</h3>
              <p className="text-sm text-gray-500 mt-2 max-w-md mx-auto">
                Claude will review every transaction and propose changes.
                You pick which ones to keep before anything is saved.
              </p>
              <button
                onClick={startRecategorize}
                className="mt-6 px-6 py-2.5 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors text-sm font-medium"
              >
                Start Analysis
              </button>
            </div>
          )}

          {/* Progress bar */}
          {(running || (done && !applied)) && (
            <div className="px-5 pt-4 pb-2 flex-shrink-0">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-gray-600">
                  {running ? 'Analyzing...' : `${changes.length} proposed change${changes.length !== 1 ? 's' : ''}`}
                </span>
                <span className="text-sm text-gray-500">
                  {progress.current} / {progress.total} ({progressPercent}%)
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-1.5">
                <div
                  className={`h-1.5 rounded-full transition-all duration-300 ${done ? 'bg-green-500' : 'bg-blue-600'}`}
                  style={{ width: `${progressPercent}%` }}
                />
              </div>
            </div>
          )}

          {/* Selection controls */}
          {done && changes.length > 0 && !applied && (
            <div className="px-5 py-2 flex items-center justify-between border-b border-gray-200 flex-shrink-0">
              <div className="flex items-center space-x-3">
                <span className="text-sm text-gray-600">{selected.size} of {changes.length} selected</span>
                <button onClick={selectAll} className="text-xs text-blue-600 hover:text-blue-800">Select all</button>
                <button onClick={selectNone} className="text-xs text-gray-500 hover:text-gray-700">Select none</button>
              </div>
            </div>
          )}

          {/* Changes list */}
          {changes.length > 0 && !applied && (
            <div ref={scrollRef} className="flex-1 overflow-y-auto px-5 pb-4 min-h-0">
              <div className="space-y-2 mt-3">
                {changes.map((change, i) => (
                  <div
                    key={i}
                    onClick={() => done && toggleChange(i)}
                    className={`p-3 rounded-lg border transition-colors ${
                      done ? 'cursor-pointer' : ''
                    } ${
                      selected.has(i)
                        ? 'border-blue-400 bg-blue-50'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <div className="flex items-center space-x-3">
                      {done && (
                        <input
                          type="checkbox"
                          checked={selected.has(i)}
                          onChange={() => toggleChange(i)}
                          className="h-4 w-4 text-blue-600 border-gray-300 rounded flex-shrink-0"
                          onClick={(e) => e.stopPropagation()}
                        />
                      )}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between">
                          <p className="text-sm font-medium text-gray-900 truncate">
                            {change.description}
                          </p>
                          <span className="text-xs text-gray-500 ml-2 flex-shrink-0">
                            ${Math.abs(change.amount).toFixed(2)}
                          </span>
                        </div>
                        <div className="flex items-center space-x-2 mt-1.5">
                          <span className="text-xs px-2 py-0.5 rounded-full bg-red-100 text-red-700 line-through">
                            {change.old_category}
                          </span>
                          <ArrowForwardIcon sx={{ fontSize: 12, color: '#9ca3af' }} />
                          <span
                            className={`text-xs px-2 py-0.5 rounded-full bg-green-100 text-green-700 ${done ? 'cursor-pointer hover:bg-green-200' : ''} flex items-center space-x-1`}
                            onClick={(e) => { e.stopPropagation(); if (done) { setEditingIdx(editingIdx === i ? null : i); setUserInput(''); } }}
                            title={done ? "Click to suggest a different category" : ""}
                          >
                            <span>{change.new_category}</span>
                            {done && <EditIcon sx={{ fontSize: 10 }} />}
                          </span>
                        </div>
                        {change.reason && (
                          <p className="text-xs text-gray-500 mt-1 italic">{change.reason}</p>
                        )}
                        {editingIdx === i && (
                          <form
                            onSubmit={(e) => { e.preventDefault(); handleUserSuggestion(i); }}
                            className="mt-2 flex items-center space-x-2"
                            onClick={(e) => e.stopPropagation()}
                          >
                            <input
                              type="text"
                              value={userInput}
                              onChange={(e) => setUserInput(e.target.value)}
                              placeholder='e.g. "this is a car purchase", "put in Transportation"'
                              className="flex-1 px-2 py-1.5 border border-gray-300 rounded text-xs focus:outline-none focus:ring-1 focus:ring-blue-500"
                              autoFocus
                              disabled={resolving}
                            />
                            <button
                              type="submit"
                              disabled={resolving || !userInput.trim()}
                              className="px-3 py-1.5 bg-blue-600 text-white rounded text-xs hover:bg-blue-700 disabled:bg-blue-300 transition-colors"
                            >
                              {resolving ? '...' : 'Go'}
                            </button>
                          </form>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Done with no changes */}
          {done && changes.length === 0 && !applied && (
            <div className="p-8 text-center">
              <CheckCircleIcon sx={{ fontSize: 48, color: '#16a34a' }} />
              <h3 className="text-lg font-medium text-gray-900 mt-3">All categories look good</h3>
              <p className="text-sm text-gray-500 mt-1">AI reviewed all transactions and found nothing to change.</p>
            </div>
          )}

          {/* Applied confirmation */}
          {applied && (
            <div className="p-8 text-center">
              <CheckCircleIcon sx={{ fontSize: 48, color: '#16a34a' }} />
              <h3 className="text-lg font-medium text-gray-900 mt-3">Changes Applied</h3>
              <p className="text-sm text-gray-500 mt-1">
                {selected.size} transaction{selected.size !== 1 ? 's' : ''} updated successfully.
              </p>
            </div>
          )}

          {error && (
            <div className="px-5 py-4 text-sm text-red-600">Error: {error}</div>
          )}
        </div>

        {/* Footer */}
        <div className="px-5 py-4 border-t border-gray-200 flex-shrink-0">
          {done && changes.length > 0 && !applied ? (
            <div className="flex space-x-3">
              <button
                onClick={applyChanges}
                disabled={selected.size === 0 || applying}
                className="flex-1 px-4 py-2.5 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-blue-300 disabled:cursor-not-allowed transition-colors text-sm font-medium"
              >
                {applying ? 'Applying...' : `Apply ${selected.size} Change${selected.size !== 1 ? 's' : ''}`}
              </button>
              <button
                onClick={onClose}
                className="px-4 py-2.5 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 transition-colors text-sm"
              >
                Cancel
              </button>
            </div>
          ) : (
            <button
              onClick={onClose}
              disabled={running}
              className="w-full px-4 py-2.5 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 disabled:opacity-50 transition-colors text-sm"
            >
              {running ? 'Analyzing... please wait' : 'Close'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default RecategorizeProgress;
