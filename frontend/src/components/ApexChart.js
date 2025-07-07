import React, { useState } from 'react';
import Chart from 'react-apexcharts';

const ApexChart = ({
  data,
  type = 'line',
  title,
  isMoneyValue = false
}) => {
  const [internalChartType, setInternalChartType] = useState(type);
  const [colorPalette, setColorPalette] = useState(['#3B82F6', '#60A5FA', '#93C5FD', '#BFDBFE']);

  const colorPalettes = [
    { name: 'Blue', value: ['#3B82F6', '#60A5FA', '#93C5FD', '#BFDBFE'] },
    { name: 'Green', value: ['#10B981', '#34D399', '#6EE7B7', '#A7F3D0'] },
    { name: 'Purple', value: ['#8B5CF6', '#A78BFA', '#C4B5FD', '#DDD6FE'] },
    { name: 'Red', value: ['#EF4444', '#F87171', '#FCA5A5', '#FECACA'] },
    { name: 'Orange', value: ['#F59E0B', '#FBBF24', '#FCD34D', '#FDE68A'] }
  ];

  // Guard against empty or null data
  if (!data || data.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-medium text-gray-900">
            {title || 'Chart'}
          </h3>
        </div>
        <div className="text-center py-10 text-red-500">
          No data to display.
        </div>
      </div>
    );
  }

  // Transform data based on chart type.
  const transformedData = {
    line: {
      series: [
        {
          name: 'Amount',
          data: data.map(item => Math.abs(item.value || item.amount || 0))
        }
      ],
      options: {
        chart: {
          type: 'line',
          toolbar: {
            show: true,
            tools: {
              download: true,
              selection: true,
              zoom: true,
              zoomin: true,
              zoomout: true,
              pan: true,
              reset: true
            }
          },
          animations: {
            enabled: true,
            easing: 'easeinout',
            speed: 800
          },
          dropShadow: {
            enabled: true,
            opacity: 0.1,
            blur: 3
          }
        },
        stroke: {
          curve: 'smooth',
          width: 3
        },
        fill: {
          type: 'gradient',
          gradient: {
            shadeIntensity: 1,
            opacityFrom: 0.4,
            opacityTo: 0.1,
            stops: [0, 90, 100],
            gradientToColors: ['#93C5FD']
          }
        },
        title: {
          text: title,
          align: 'left',
          style: {
            fontSize: '16px',
            fontWeight: 'normal',
            color: '#1F2937'
          }
        },
        xaxis: {
          categories: data.map(item => item.label || ''),
          labels: {
            style: {
              colors: '#6B7280',
              fontSize: '12px'
            }
          },
          axisBorder: {
            show: false
          },
          axisTicks: {
            show: false
          }
        },
        yaxis: {
          labels: {
            formatter: function (value) {
              if (isMoneyValue) {
                return new Intl.NumberFormat('en-US', {
                  style: 'currency',
                  currency: 'USD',
                  minimumFractionDigits: 0,
                  maximumFractionDigits: 0
                }).format(value);
              }
              return value + '%';
            },
            style: {
              colors: '#6B7280',
              fontSize: '12px'
            }
          }
        },
        grid: {
          borderColor: '#E5E7EB',
          strokeDashArray: 2,
          xaxis: {
            lines: {
              show: true
            }
          },
          padding: {
            top: 10,
            right: 20,
            bottom: 10,
            left: 20
          }
        },
        colors: ['#60A5FA'],
        tooltip: {
          theme: 'light',
          y: {
            formatter: function (value) {
              if (isMoneyValue) {
                return new Intl.NumberFormat('en-US', {
                  style: 'currency',
                  currency: 'USD',
                  minimumFractionDigits: 0,
                  maximumFractionDigits: 0
                }).format(value);
              }
              return value + '%';
            }
          },
          style: {
            fontSize: '12px'
          }
        },
        markers: {
          size: 5,
          colors: ['#60A5FA'],
          strokeColors: '#fff',
          strokeWidth: 2,
          hover: {
            size: 7,
            sizeOffset: 3
          }
        },
        theme: {
          mode: 'light'
        }
      }
    },
    bar: {
      series: [
        {
          name: 'Percentage',
          data: data.map(item => item.value || item.percentage || 0)
        }
      ],
      options: {
        chart: {
          type: 'bar',
          toolbar: {
            show: true
          },
          animations: {
            enabled: true,
            easing: 'easeinout',
            speed: 800
          },
          dropShadow: {
            enabled: true,
            opacity: 0.1,
            blur: 3
          }
        },
        plotOptions: {
          bar: {
            borderRadius: 4,
            horizontal: false,
            columnWidth: '50%',
            distributed: true,
            dataLabels: {
              position: 'top'
            }
          }
        },
        title: {
          text: title,
          align: 'left',
          style: {
            fontSize: '16px',
            fontWeight: 'normal',
            color: '#1F2937'
          }
        },
        xaxis: {
          categories: data.map(item => item.category || item.label || ''),
          labels: {
            style: {
              colors: '#6B7280',
              fontSize: '12px'
            },
            rotate: -45,
            trim: true,
            offsetY: 5
          },
          axisBorder: {
            show: false
          },
          axisTicks: {
            show: false
          }
        },
        yaxis: {
          labels: {
            formatter: function (value) {
              return value + '%';
            },
            style: {
              colors: '#6B7280',
              fontSize: '12px'
            }
          }
        },
        grid: {
          borderColor: '#E5E7EB',
          strokeDashArray: 2,
          padding: {
            top: 20,
            right: 20,
            bottom: 40,
            left: 20
          }
        },
        colors: ['#3B82F6', '#60A5FA', '#93C5FD', '#BFDBFE'],
        tooltip: {
          theme: 'light',
          y: {
            formatter: function (value) {
              return value + '%';
            }
          },
          style: {
            fontSize: '12px'
          }
        },
        dataLabels: {
          enabled: true,
          formatter: function (value) {
            return value + '%';
          },
          offsetY: -25,
          style: {
            fontSize: '12px',
            colors: ['#4B5563'],
            background: {
              enabled: true,
              foreColor: '#fff',
              padding: 4,
              borderRadius: 2,
              borderWidth: 1,
              borderColor: '#E5E7EB',
              opacity: 0.9
            }
          }
        },
        theme: {
          mode: 'light'
        }
      }
    }
  };

  // Handle unsupported chart types
  if (!transformedData[internalChartType]) {
    console.error('Unsupported chart type: ' + internalChartType);
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-medium text-gray-900">{title}</h3>
          <div className="flex items-center space-x-2">
            <select
              value={internalChartType}
              onChange={e => setInternalChartType(e.target.value)}
              className="text-sm border border-gray-300 rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="line">Line</option>
              <option value="bar">Bar</option>
            </select>
            <select
              value={JSON.stringify(colorPalette)}
              onChange={e => {
                try {
                  setColorPalette(JSON.parse(e.target.value));
                } catch (error) {
                  console.error('Invalid color palette JSON:', e.target.value);
                }
              }}
              className="text-sm border border-gray-300 rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {colorPalettes.map((paletteItem, idx) => (
                <option key={idx} value={JSON.stringify(paletteItem.value)}>
                  {paletteItem.name}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="text-center py-10 text-red-500">
          Unsupported chart type: {internalChartType}
        </div>
      </div>
    );
  }

  // Deep copy the chart data for the current type
  const chartData = JSON.parse(JSON.stringify(transformedData[internalChartType]));
  // Update the colors in the options
  chartData.options.colors = colorPalette;

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-medium text-gray-900">
          {title}
        </h3>
        <div className="flex items-center space-x-2">
          <select
            value={internalChartType}
            onChange={e => setInternalChartType(e.target.value)}
            className="text-sm border border-gray-300 rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="line">Line</option>
            <option value="bar">Bar</option>
          </select>
          <select
            value={JSON.stringify(colorPalette)}
            onChange={e => {
              try {
                setColorPalette(JSON.parse(e.target.value));
              } catch (error) {
                console.error('Invalid color palette JSON:', e.target.value);
              }
            }}
            className="text-sm border border-gray-300 rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {colorPalettes.map((paletteItem, idx) => (
              <option key={idx} value={JSON.stringify(paletteItem.value)}>
                {paletteItem.name}
              </option>
            ))}
          </select>
        </div>
      </div>
      <Chart
        options={chartData.options}
        series={chartData.series}
        type={internalChartType}
        height={350}
      />
    </div>
  );
};

export default ApexChart;
