import React, { useState } from 'react';

const CustomizableChart = ({ data, title, type: initialType = 'bar' }) => {
  const [chartType, setChartType] = useState(initialType);
  const [showValues, setShowValues] = useState(true);
  const [colorScheme, setColorScheme] = useState('blue');

  const colorSchemes = {
    blue: ['#3B82F6', '#1E40AF', '#1D4ED8', '#2563EB', '#3B82F6'],
    green: ['#10B981', '#059669', '#047857', '#065F46', '#064E3B'],
    purple: ['#8B5CF6', '#7C3AED', '#6D28D9', '#5B21B6', '#553C9A'],
    gradient: ['#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe'],
    rainbow: ['#EF4444', '#F59E0B', '#10B981', '#3B82F6', '#8B5CF6']
  };

  const maxValue = Math.max(...data.map(item => item.value || item.amount || 0));

  const renderBarChart = () => (
    <div className="space-y-3">
      {data.map((item, index) => (
        <div key={index} className="flex items-center space-x-3">
          <div className="w-24 text-sm font-medium text-gray-700 truncate" title={item.label || item.category}>
            {item.label || item.category}
          </div>
          <div className="flex-1 flex items-center space-x-2">
            <div className="flex-1 bg-gray-200 rounded-full h-6 relative overflow-hidden">
              <div 
                className="h-full rounded-full transition-all duration-500 ease-out"
                style={{ 
                  width: `${((item.value || item.amount || 0) / maxValue) * 100}%`,
                  backgroundColor: colorSchemes[colorScheme][index % colorSchemes[colorScheme].length]
                }}
              />
            </div>
            {showValues && (
              <div className="w-16 text-sm font-semibold text-gray-900 text-right">
                {item.value ? `${item.value}%` : `$${Math.abs(item.amount || 0).toFixed(0)}`}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );

  const renderPieChart = () => {
    const total = data.reduce((sum, item) => sum + (item.value || item.amount || 0), 0);
    let currentAngle = 0;

    return (
      <div className="flex items-center justify-center">
        <div className="relative">
          <svg width="200" height="200" className="transform -rotate-90">
            {data.map((item, index) => {
              const value = item.value || item.amount || 0;
              const percentage = (value / total) * 100;
              const angle = (percentage / 100) * 360;
              
              const startAngle = currentAngle;
              const endAngle = currentAngle + angle;
              currentAngle += angle;

              const startAngleRad = (startAngle * Math.PI) / 180;
              const endAngleRad = (endAngle * Math.PI) / 180;

              const x1 = 100 + 80 * Math.cos(startAngleRad);
              const y1 = 100 + 80 * Math.sin(startAngleRad);
              const x2 = 100 + 80 * Math.cos(endAngleRad);
              const y2 = 100 + 80 * Math.sin(endAngleRad);

              const largeArcFlag = angle > 180 ? 1 : 0;

              return (
                <path
                  key={index}
                  d={`M 100 100 L ${x1} ${y1} A 80 80 0 ${largeArcFlag} 1 ${x2} ${y2} Z`}
                  fill={colorSchemes[colorScheme][index % colorSchemes[colorScheme].length]}
                  className="hover:opacity-80 transition-opacity"
                />
              );
            })}
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <div className="text-lg font-bold text-gray-900">{data.length}</div>
              <div className="text-xs text-gray-500">Items</div>
            </div>
          </div>
        </div>
        
        {/* Legend */}
        <div className="ml-6 space-y-2">
          {data.map((item, index) => (
            <div key={index} className="flex items-center space-x-2 text-sm">
              <div 
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: colorSchemes[colorScheme][index % colorSchemes[colorScheme].length] }}
              />
              <span className="text-gray-700">{item.label || item.category}</span>
              {showValues && (
                <span className="text-gray-500">
                  ({item.value ? `${item.value}%` : `$${Math.abs(item.amount || 0).toFixed(0)}`})
                </span>
              )}
            </div>
          ))}
        </div>
      </div>
    );
  };

  const renderLineChart = () => (
    <div className="relative h-64">
      <svg width="100%" height="100%" className="overflow-visible">
        <defs>
          <linearGradient id={`gradient-${colorScheme}`} x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" style={{ stopColor: colorSchemes[colorScheme][0], stopOpacity: 0.3 }} />
            <stop offset="100%" style={{ stopColor: colorSchemes[colorScheme][0], stopOpacity: 0.1 }} />
          </linearGradient>
        </defs>
        
        {data.map((item, index) => {
          const x = (index / (data.length - 1)) * 100;
          const y = 100 - ((item.value || item.amount || 0) / maxValue) * 80;
          
          return (
            <g key={index}>
              <circle
                cx={`${x}%`}
                cy={`${y}%`}
                r="4"
                fill={colorSchemes[colorScheme][0]}
                className="hover:r-6 transition-all"
              />
              {showValues && (
                <text
                  x={`${x}%`}
                  y={`${y - 10}%`}
                  textAnchor="middle"
                  className="text-xs fill-gray-600"
                >
                  {item.value ? `${item.value}%` : `$${Math.abs(item.amount || 0).toFixed(0)}`}
                </text>
              )}
            </g>
          );
        })}
        
        <polyline
          fill="none"
          stroke={colorSchemes[colorScheme][0]}
          strokeWidth="2"
          points={data.map((item, index) => {
            const x = (index / (data.length - 1)) * 100;
            const y = 100 - ((item.value || item.amount || 0) / maxValue) * 80;
            return `${x},${y}`;
          }).join(' ')}
        />
      </svg>
    </div>
  );

  return (
    <div className="bg-white rounded-lg shadow p-6">
      {/* Chart Header with Controls */}
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-medium text-gray-900">{title}</h3>
        <div className="flex items-center space-x-2">
          {/* Chart Type Selector */}
          <select
            value={chartType}
            onChange={(e) => setChartType(e.target.value)}
            className="text-sm border border-gray-300 rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="bar">📊 Bar</option>
            <option value="pie">🥧 Pie</option>
            <option value="line">📈 Line</option>
          </select>
          
          {/* Color Scheme Selector */}
          <select
            value={colorScheme}
            onChange={(e) => setColorScheme(e.target.value)}
            className="text-sm border border-gray-300 rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="blue">🔵 Blue</option>
            <option value="green">🟢 Green</option>
            <option value="purple">🟣 Purple</option>
            <option value="gradient">🌈 Gradient</option>
            <option value="rainbow">🎨 Rainbow</option>
          </select>
          
          {/* Show Values Toggle */}
          <button
            onClick={() => setShowValues(!showValues)}
            className={`text-sm px-2 py-1 rounded transition-colors ${
              showValues 
                ? 'bg-blue-100 text-blue-800 hover:bg-blue-200' 
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {showValues ? '👁️' : '👁️‍🗨️'} Values
          </button>
        </div>
      </div>

      {/* Chart Content */}
      <div className="min-h-64">
        {chartType === 'bar' && renderBarChart()}
        {chartType === 'pie' && renderPieChart()}
        {chartType === 'line' && renderLineChart()}
      </div>
    </div>
  );
};

export default CustomizableChart;