import React, { useEffect, useRef, useState } from 'react';

const GoogleChart = ({ 
  data, 
  type = 'LineChart',
  options = {},
  title,
  customizable = false 
}) => {
  const chartRef = useRef(null);
  const chartInstance = useRef(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const loadGoogleCharts = async () => {
      try {
        setIsLoading(true);
        setError(null);

        // Check if Google Charts is available
        if (!window.google) {
          setError('Google Charts library not found. Please check your internet connection.');
          setIsLoading(false);
          return;
        }

        // Load Google Charts
        await new Promise((resolve) => {
          window.google.charts.load('current', { 
            packages: ['corechart', 'controls']
          });
          window.google.charts.setOnLoadCallback(resolve);
        });

        drawChart();
        setIsLoading(false);
      } catch (err) {
        setError(err.message || 'Error loading chart');
        setIsLoading(false);
      }
    };

    loadGoogleCharts();
  }, []);

  useEffect(() => {
    if (window.google && window.google.visualization) {
      drawChart();
    }
  }, [data, type, options]);

  const drawChart = () => {
    if (!chartRef.current) return;

    // Convert data to Google Charts format
    const dataTable = new window.google.visualization.DataTable();
    
    // Add columns based on data structure
    if (type === 'LineChart') {
      dataTable.addColumn('string', 'Month');
      dataTable.addColumn('number', 'Amount');
      data.forEach(item => {
        dataTable.addRow([item.label, Math.abs(item.value || item.amount)]);
      });
    } else if (type === 'BarChart') {
      dataTable.addColumn('string', 'Category');
      dataTable.addColumn('number', 'Percentage');
      data.forEach(item => {
        dataTable.addRow([item.category, item.value || item.percentage]);
      });
    }

    // Default chart options
    const defaultOptions = {
      title,
      titleTextStyle: { color: '#1F2937', fontSize: 16, bold: false },
      backgroundColor: 'transparent',
      chartArea: { width: '80%', height: '70%' },
      legend: { position: 'none' },
      animation: {
        startup: true,
        duration: 1000,
        easing: 'out'
      },
      colors: ['#3B82F6'],
      vAxis: {
        format: type === 'LineChart' ? 'currency' : '#\'%\'',
        gridlines: { color: '#f3f4f6' }
      },
      hAxis: {
        gridlines: { color: 'transparent' }
      }
    };

    // If customizable, wrap chart in a dashboard with controls
    if (customizable) {
      const dashboard = new window.google.visualization.Dashboard(chartRef.current);
      
      // Add controls for customization
      const controlWrapper = new window.google.visualization.ControlWrapper({
        controlType: 'ChartRangeFilter',
        containerId: 'control_div',
        options: {
          filterColumnIndex: 1,
          ui: {
            chartType: 'LineChart',
            chartOptions: {
              chartArea: { width: '80%', height: '50%' },
              hAxis: { baselineColor: 'none' }
            }
          }
        }
      });

      const chartWrapper = new window.google.visualization.ChartWrapper({
        chartType: type,
        containerId: 'chart_div',
        options: { ...defaultOptions, ...options }
      });

      dashboard.bind(controlWrapper, chartWrapper);
      dashboard.draw(dataTable);
    } else {
      // Regular chart without controls
      chartInstance.current = new window.google.visualization[type](chartRef.current);
      chartInstance.current.draw(dataTable, { ...defaultOptions, ...options });
    }
  };

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="text-red-500 text-center py-8">
          <p className="text-lg font-medium">Error loading chart</p>
          <p className="text-sm mt-2">{error}</p>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-center h-[300px]">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      {customizable ? (
        <>
          <div id="chart_div" style={{ height: '300px' }}></div>
          <div id="control_div" style={{ height: '50px', marginTop: '10px' }}></div>
        </>
      ) : (
        <div ref={chartRef} style={{ height: '300px' }}></div>
      )}
    </div>
  );
};

export default GoogleChart;
