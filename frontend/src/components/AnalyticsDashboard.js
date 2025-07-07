import React, { useState } from 'react';
import ApexChart from './ApexChart';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

function SortableWidget({ widget, widgetId, children }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
  } = useSortable({ id: widgetId });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <div ref={setNodeRef} style={style} {...attributes} {...listeners} className="mb-6">
      {children}
    </div>
  );
}

const AnalyticsDashboard = ({ 
  categoryBreakdown, 
  monthlyReports, 
  transactions,
  formatCurrency,
  getMonthName 
}) => {
  const [dashboardLayout, setDashboardLayout] = useState('default');
  const [selectedWidgets, setSelectedWidgets] = useState([
    'monthlyTrend',
    'categoryBreakdown',
    'accountTypeAnalysis',
    'sourceAnalysis'
  ]);

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const availableWidgets = {
    categoryBreakdown: {
      title: '🏷️ Category Breakdown',
      component: 'chart',
      data: categoryBreakdown.map(cat => ({
        category: cat.category,
        amount: cat.amount,
        value: cat.percentage
      }))
    },
    monthlyTrend: {
      title: '📈 Monthly Spending Trend',
      component: 'chart',
      data: monthlyReports.slice(-6).map(report => ({
        label: getMonthName(report.month).split(' ')[0],
        amount: report.total_spent,
        value: report.total_spent
      }))
    },
    accountTypeAnalysis: {
      title: '💳 Account Type Analysis',
      component: 'custom',
      render: () => (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            {/* Debit Summary */}
            <div className="bg-blue-50 rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-medium text-blue-900">Debit Accounts</h4>
                  <p className="text-sm text-blue-700">
                    {transactions.filter(t => t.account_type === 'debit').length} transactions
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-lg font-semibold text-blue-900">
                    {formatCurrency(Math.abs(transactions.filter(t => t.account_type === 'debit').reduce((sum, t) => sum + t.amount, 0)))}
                  </p>
                  <p className="text-xs text-blue-600">
                    {transactions.length > 0 ? ((Math.abs(transactions.filter(t => t.account_type === 'debit').reduce((sum, t) => sum + t.amount, 0)) / Math.abs(transactions.reduce((sum, t) => sum + t.amount, 0))) * 100).toFixed(1) : 0}%
                  </p>
                </div>
              </div>
            </div>

            {/* Credit Summary */}
            <div className="bg-purple-50 rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-medium text-purple-900">Credit Cards</h4>
                  <p className="text-sm text-purple-700">
                    {transactions.filter(t => t.account_type === 'credit_card').length} transactions
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-lg font-semibold text-purple-900">
                    {formatCurrency(Math.abs(transactions.filter(t => t.account_type === 'credit_card').reduce((sum, t) => sum + t.amount, 0)))}
                  </p>
                  <p className="text-xs text-purple-600">
                    {transactions.length > 0 ? ((Math.abs(transactions.filter(t => t.account_type === 'credit_card').reduce((sum, t) => sum + t.amount, 0)) / Math.abs(transactions.reduce((sum, t) => sum + t.amount, 0))) * 100).toFixed(1) : 0}%
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )
    },
    sourceAnalysis: {
      title: '📄 Source Analysis',
      component: 'custom',
      render: () => (
        <div className="space-y-3">
          {Array.from(new Set(transactions.map(t => t.pdf_source || 'Manual')))
            .map(source => {
              const sourceTransactions = transactions.filter(t => (t.pdf_source || 'Manual') === source);
              const totalAmount = Math.abs(sourceTransactions.reduce((sum, t) => sum + t.amount, 0));
              const percentage = transactions.length > 0 ? (totalAmount / Math.abs(transactions.reduce((sum, t) => sum + t.amount, 0))) * 100 : 0;
              
              return (
                <div key={source} className="flex items-center justify-between p-3 border rounded-lg hover:bg-gray-50 transition-colors">
                  <div className="flex items-center space-x-3">
                    <div className={`w-3 h-3 rounded-full ${
                      source === 'Manual' ? 'bg-gray-500' :
                      source.toLowerCase().includes('debit') ? 'bg-blue-500' : 'bg-purple-500'
                    }`}></div>
                    <div>
                      <p className="font-medium text-gray-900">{source}</p>
                      <p className="text-sm text-gray-500">{sourceTransactions.length} transactions</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="font-semibold text-gray-900">{formatCurrency(totalAmount)}</p>
                    <p className="text-sm text-gray-500">{percentage.toFixed(1)}%</p>
                  </div>
                </div>
              );
            })}
        </div>
      )
    }
  };

  const layoutPresets = {
    default: {
      name: '📊 Default Layout',
      grid: 'grid-cols-1 lg:grid-cols-2 gap-6 items-start'
    },
    single: {
      name: '📱 Single Column',
      grid: 'grid-cols-1 gap-6'
    },
    triple: {
      name: '🖥️ Triple Column',
      grid: 'grid-cols-1 lg:grid-cols-3 gap-4 items-start'
    },
    compact: {
      name: '📄 Compact View',
      grid: 'grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 items-start'
    }
  };

  const toggleWidget = (widgetId) => {
    setSelectedWidgets(prev => 
      prev.includes(widgetId) 
        ? prev.filter(id => id !== widgetId)
        : [...prev, widgetId]
    );
  };

  function handleDragEnd(event) {
    const { active, over } = event;
    
    if (active.id !== over.id) {
      setSelectedWidgets((items) => {
        const oldIndex = items.indexOf(active.id);
        const newIndex = items.indexOf(over.id);
        
        return arrayMove(items, oldIndex, newIndex);
      });
    }
  }

  return (
    <div className="space-y-6">
      {/* Dashboard Controls */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <h2 className="text-xl font-bold text-gray-900">📊 Customizable Analytics Dashboard</h2>
          
          <div className="flex items-center space-x-4">
            {/* Layout Selector */}
            <div className="flex items-center space-x-2">
              <label className="text-sm font-medium text-gray-700">Layout:</label>
              <select
                value={dashboardLayout}
                onChange={(e) => setDashboardLayout(e.target.value)}
                className="text-sm border border-gray-300 rounded px-3 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {Object.entries(layoutPresets).map(([key, preset]) => (
                  <option key={key} value={key}>{preset.name}</option>
                ))}
              </select>
            </div>

            {/* Widget Selector */}
            <div className="flex items-center space-x-2">
              <label className="text-sm font-medium text-gray-700">Widgets:</label>
              <div className="flex flex-wrap gap-2">
                {Object.entries(availableWidgets).map(([widgetId, widget]) => (
                  <button
                    key={widgetId}
                    onClick={() => toggleWidget(widgetId)}
                    className={`text-xs px-2 py-1 rounded transition-colors ${
                      selectedWidgets.includes(widgetId)
                        ? 'bg-blue-100 text-blue-800 hover:bg-blue-200'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                  >
                    {widget.title}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Dashboard Grid */}
      <DndContext 
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragEnd={handleDragEnd}
      >
        <div className={`${layoutPresets[dashboardLayout].grid}`}>
          <SortableContext 
            items={selectedWidgets}
            strategy={verticalListSortingStrategy}
          >
            {selectedWidgets.map((widgetId) => {
              const widget = availableWidgets[widgetId];
              if (!widget) return null;

              return (
                <SortableWidget key={widgetId} widgetId={widgetId} widget={widget}>
                  <div className="bg-white rounded-lg shadow p-4">
                    {widget.component === 'chart' ? (
                      <ApexChart
                        data={widget.data}
                        type={widgetId === 'monthlyTrend' ? 'line' : 'bar'}
                        title={widget.title}
                        isMoneyValue={widgetId === 'monthlyTrend'}
                      />
                    ) : (
                      <div className="p-2">
                        <h3 className="text-lg font-medium text-gray-900 mb-4">{widget.title}</h3>
                        {widget.render()}
                      </div>
                    )}
                  </div>
                </SortableWidget>
              );
            })}
          </SortableContext>
        </div>
      </DndContext>

      {/* Quick Stats Bar */}
      <div className="bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg p-6 text-white mt-8">
        <h3 className="text-lg font-semibold mb-4">📈 Quick Insights</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
          <div>
            <div className="text-2xl font-bold">{transactions.length}</div>
            <div className="text-sm opacity-90">Total Transactions</div>
          </div>
          <div>
            <div className="text-2xl font-bold">{categoryBreakdown.length}</div>
            <div className="text-sm opacity-90">Active Categories</div>
          </div>
          <div>
            <div className="text-2xl font-bold">
              {formatCurrency(Math.abs(categoryBreakdown.reduce((sum, cat) => sum + cat.amount, 0)))}
            </div>
            <div className="text-sm opacity-90">Total Volume</div>
          </div>
          <div>
            <div className="text-2xl font-bold">
              {transactions.length > 0 
                ? formatCurrency(Math.abs(categoryBreakdown.reduce((sum, cat) => sum + cat.amount, 0)) / transactions.length)
                : '$0.00'
              }
            </div>
            <div className="text-sm opacity-90">Avg. Transaction</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AnalyticsDashboard;
