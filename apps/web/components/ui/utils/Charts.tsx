"use client";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';
import { Line, Bar, Doughnut } from 'react-chartjs-2';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: 'top' as const,
    },
  },
  scales: {
    y: {
      beginAtZero: true,
    },
  },
};

const doughnutOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: 'bottom' as const,
    },
  },
};

interface TrendChartProps {
  data: {
    labels: string[];
    datasets: Array<{
      label: string;
      data: number[];
      borderColor: string;
      backgroundColor: string;
      fill?: boolean;
    }>;
  };
  title?: string;
}

export function TrendChart({ data, title }: TrendChartProps) {
  return (
    <div className="h-80 w-full">
      {title && <h3 className="text-lg font-medium mb-4 text-gray-900 dark:text-white">{title}</h3>}
      <Line data={data} options={chartOptions} />
    </div>
  );
}

interface BarChartProps {
  data: {
    labels: string[];
    datasets: Array<{
      label: string;
      data: number[];
      backgroundColor: string;
      borderColor?: string;
    }>;
  };
  title?: string;
}

export function BarChart({ data, title }: BarChartProps) {
  return (
    <div className="h-80 w-full">
      {title && <h3 className="text-lg font-medium mb-4 text-gray-900 dark:text-white">{title}</h3>}
      <Bar data={data} options={chartOptions} />
    </div>
  );
}

interface ConversionFunnelProps {
  steps: Array<{
    name: string;
    count: number;
    percentage: number;
    color: string;
  }>;
}

export function ConversionFunnel({ steps }: ConversionFunnelProps) {
  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Dönüşüm Hunisi</h3>
      {steps.map((step, index) => (
        <div key={step.name} className="relative">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{step.name}</span>
            <div className="text-sm text-gray-600 dark:text-gray-400">
              <span className="font-semibold">{step.count}</span>
              <span className="ml-1">(%{step.percentage})</span>
            </div>
          </div>
          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-6 relative overflow-hidden">
            <div
              className="h-6 rounded-full transition-all duration-300 flex items-center justify-center text-xs font-medium text-white"
              style={{
                width: `${step.percentage}%`,
                backgroundColor: step.color,
              }}
            >
              {step.percentage > 20 && `%${step.percentage}`}
            </div>
          </div>
          {index < steps.length - 1 && (
            <div className="flex justify-center my-2">
              <div className="w-0 h-0 border-l-4 border-r-4 border-t-8 border-transparent border-t-gray-400"></div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

interface DonutChartProps {
  data: {
    labels: string[];
    datasets: Array<{
      data: number[];
      backgroundColor: string[];
      borderColor?: string[];
    }>;
  };
  title?: string;
}

export function DonutChart({ data, title }: DonutChartProps) {
  return (
    <div className="h-80 w-full">
      {title && <h3 className="text-lg font-medium mb-4 text-gray-900 dark:text-white">{title}</h3>}
      <Doughnut data={data} options={doughnutOptions} />
    </div>
  );
}

interface MetricCardProps {
  title: string;
  value: number | string;
  change?: number;
  trend?: 'up' | 'down' | 'neutral';
  icon?: React.ReactNode;
  color?: string;
}

export function MetricCard({ title, value, change, trend, icon, color = 'blue' }: MetricCardProps) {
  const colorClasses = {
    blue: 'bg-blue-500',
    green: 'bg-green-500',
    yellow: 'bg-yellow-500',
    red: 'bg-red-500',
    purple: 'bg-purple-500',
    indigo: 'bg-indigo-500',
  };

  const trendColor = trend === 'up' ? 'text-green-600' : trend === 'down' ? 'text-red-600' : 'text-gray-600';

  return (
    <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-600 dark:text-gray-400">{title}</p>
          <p className="text-3xl font-bold text-gray-900 dark:text-white mt-2">{value}</p>
          {change !== undefined && (
            <p className={`text-sm mt-1 ${trendColor}`}>
              {trend === 'up' && '↗'} {trend === 'down' && '↘'} 
              {change > 0 ? '+' : ''}{change}%
            </p>
          )}
        </div>
        {icon && (
          <div className={`p-3 rounded-full ${colorClasses[color as keyof typeof colorClasses]} bg-opacity-10`}>
            <div className={`w-6 h-6 text-${color}-600`}>{icon}</div>
          </div>
        )}
      </div>
    </div>
  );
}

interface HeatmapData {
  label: string;
  value: number;
  color: string;
}

interface HeatmapProps {
  data: HeatmapData[];
  title?: string;
  maxValue?: number;
}

export function Heatmap({ data, title, maxValue }: HeatmapProps) {
  const max = maxValue || Math.max(...data.map(d => d.value));
  
  const getIntensity = (value: number) => {
    const intensity = value / max;
    if (intensity > 0.8) return 'bg-green-500';
    if (intensity > 0.6) return 'bg-green-400';
    if (intensity > 0.4) return 'bg-yellow-400';
    if (intensity > 0.2) return 'bg-orange-400';
    return 'bg-red-400';
  };

  return (
    <div className="space-y-4">
      {title && <h3 className="text-lg font-medium text-gray-900 dark:text-white">{title}</h3>}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
        {data.map((item, index) => (
          <div
            key={index}
            className={`p-4 rounded-lg text-center text-white font-medium ${getIntensity(item.value)} hover:scale-105 transition-transform cursor-pointer`}
            title={`${item.label}: ${item.value}%`}
          >
            <div className="text-sm truncate mb-1">{item.label}</div>
            <div className="text-xl font-bold">{item.value}%</div>
          </div>
        ))}
      </div>
      <div className="flex items-center justify-center gap-2 text-sm text-gray-600 dark:text-gray-400">
        <span>Düşük</span>
        <div className="flex gap-1">
          <div className="w-3 h-3 bg-red-400 rounded"></div>
          <div className="w-3 h-3 bg-orange-400 rounded"></div>
          <div className="w-3 h-3 bg-yellow-400 rounded"></div>
          <div className="w-3 h-3 bg-green-400 rounded"></div>
          <div className="w-3 h-3 bg-green-500 rounded"></div>
        </div>
        <span>Yüksek</span>
      </div>
    </div>
  );
}
