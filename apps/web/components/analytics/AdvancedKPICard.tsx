'use client';

import React from 'react';
import { EnhancedCard } from '@/components/ui';
import { cn } from '@/components/ui/utils/cn';


export interface KPIData {
  title: string;
  value: number | string;
  change?: number;
  changeType?: 'increase' | 'decrease' | 'neutral';
  period?: string;
  target?: number;
  unit?: string;
  format?: 'number' | 'percentage' | 'currency' | 'duration';
  trend?: number[];
  status?: 'excellent' | 'good' | 'warning' | 'critical';
}

interface AdvancedKPICardProps {
  data: KPIData;
  size?: 'sm' | 'md' | 'lg';
  showTrend?: boolean;
  showTarget?: boolean;
  interactive?: boolean;
  loading?: boolean;
  onClick?: () => void;
}

export function AdvancedKPICard({
  data,
  size = 'md',
  showTrend = false,
  showTarget = false,
  interactive = false,
  loading = false,
  onClick,
}: AdvancedKPICardProps) {


  const formatValue = (value: number | string, format?: string, unit?: string) => {
    if (typeof value === 'string') return value;

    switch (format) {
      case 'percentage':
        return `${value.toFixed(1)}%`;
      case 'currency':
        return `₺${value.toLocaleString('tr-TR')}`;
      case 'duration':
        return `${value} dk`;
      default:
        return `${value.toLocaleString('tr-TR')}${unit ? ` ${unit}` : ''}`;
    }
  };

  const getChangeColor = (changeType?: string) => {
    switch (changeType) {
      case 'increase':
        return 'text-green-600 dark:text-green-400';
      case 'decrease':
        return 'text-red-600 dark:text-red-400';
      default:
        return 'text-gray-600 dark:text-gray-400';
    }
  };

  const getChangeIcon = (changeType?: string) => {
    switch (changeType) {
      case 'increase':
        return (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
          </svg>
        );
      case 'decrease':
        return (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6" />
          </svg>
        );
      default:
        return (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
          </svg>
        );
    }
  };

  const getStatusColor = (status?: string) => {
    switch (status) {
      case 'excellent':
        return 'border-l-green-500 bg-green-50 dark:bg-green-900/20';
      case 'good':
        return 'border-l-blue-500 bg-blue-50 dark:bg-blue-900/20';
      case 'warning':
        return 'border-l-yellow-500 bg-yellow-50 dark:bg-yellow-900/20';
      case 'critical':
        return 'border-l-red-500 bg-red-50 dark:bg-red-900/20';
      default:
        return 'border-l-gray-300';
    }
  };

  const sizeClasses = {
    sm: 'p-4',
    md: 'p-6',
    lg: 'p-8',
  };

  const textSizes = {
    sm: { title: 'text-sm', value: 'text-2xl', change: 'text-xs' },
    md: { title: 'text-base', value: 'text-3xl', change: 'text-sm' },
    lg: { title: 'text-lg', value: 'text-4xl', change: 'text-base' },
  };

  // Mini trend chart
  const TrendChart = ({ trend }: { trend: number[] }) => {
    if (!trend || trend.length === 0) return null;

    const max = Math.max(...trend);
    const min = Math.min(...trend);
    const range = max - min || 1;

    return (
      <div className="flex items-end space-x-0.5 h-8">
        {trend.map((value, index) => {
          const height = ((value - min) / range) * 100;
          return (
            <div
              key={index}
              className="bg-blue-500 rounded-sm transition-all duration-300"
              style={{
                height: `${Math.max(height, 10)}%`,
                width: '4px',
              }}
            />
          );
        })}
      </div>
    );
  };

  // Progress bar for target
  const TargetProgress = ({ current, target }: { current: number; target: number }) => {
    const progress = (current / target) * 100;
    const progressClamped = Math.min(progress, 100);

    return (
      <div className="space-y-1">
        <div className="flex justify-between text-xs text-gray-500">
          <span>İlerleme</span>
          <span>{formatValue(target, data.format, data.unit)} hedef</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2 dark:bg-gray-700">
          <div
            className={cn(
              'h-2 rounded-full transition-all duration-500',
              progress >= 100 ? 'bg-green-500' : progress >= 80 ? 'bg-blue-500' : 'bg-yellow-500'
            )}
            style={{ width: `${progressClamped}%` }}
          />
        </div>
      </div>
    );
  };

  return (
    <EnhancedCard
      variant="elevated"
      padding="none"
      interactive={interactive}
      loading={loading}
      onClick={onClick}
      className={cn(
        'border-l-4 transition-all duration-300',
        getStatusColor(data.status),
        sizeClasses[size],
        interactive && 'hover:shadow-xl cursor-pointer'
      )}
    >
      <div className="space-y-4">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <h3 className={cn('font-medium text-gray-900 dark:text-gray-100', textSizes[size].title)}>
              {data.title}
            </h3>
            {data.period && (
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {data.period}
              </p>
            )}
          </div>
          
          {showTrend && data.trend && (
            <div className="flex-shrink-0">
              <TrendChart trend={data.trend} />
            </div>
          )}
        </div>

        {/* Value */}
        <div className="space-y-2">
          <div className={cn('font-bold text-gray-900 dark:text-gray-100', textSizes[size].value)}>
            {formatValue(data.value, data.format, data.unit)}
          </div>

          {/* Change indicator */}
          {data.change !== undefined && (
            <div className={cn('flex items-center space-x-1', textSizes[size].change)}>
              <span className={getChangeColor(data.changeType)}>
                <div className="flex items-center space-x-1">
                  {getChangeIcon(data.changeType)}
                  <span>
                    {Math.abs(data.change)}% {data.changeType === 'increase' ? 'artış' : data.changeType === 'decrease' ? 'azalış' : 'değişim'}
                  </span>
                </div>
              </span>
            </div>
          )}
        </div>

        {/* Target progress */}
        {showTarget && data.target && typeof data.value === 'number' && (
          <TargetProgress current={data.value} target={data.target} />
        )}
      </div>
    </EnhancedCard>
  );
}

// Multiple KPI Cards Grid
interface KPIGridProps {
  kpis: KPIData[];
  columns?: 2 | 3 | 4;
  size?: 'sm' | 'md' | 'lg';
  showTrend?: boolean;
  showTarget?: boolean;
  loading?: boolean;
}

export function KPIGrid({
  kpis,
  columns = 4,
  size = 'md',
  showTrend = false,
  showTarget = false,
  loading = false,
}: KPIGridProps) {
  const gridCols = {
    2: 'grid-cols-1 md:grid-cols-2',
    3: 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3',
    4: 'grid-cols-1 md:grid-cols-2 lg:grid-cols-4',
  };

  if (loading) {
    return (
      <div className={cn('grid gap-6', gridCols[columns])}>
        {Array.from({ length: columns }).map((_, index) => (
          <AdvancedKPICard
            key={index}
            data={{ title: '', value: 0 }}
            size={size}
            loading={true}
          />
        ))}
      </div>
    );
  }

  return (
    <div className={cn('grid gap-6', gridCols[columns])}>
      {kpis.map((kpi, index) => (
        <AdvancedKPICard
          key={index}
          data={kpi}
          size={size}
          showTrend={showTrend}
          showTarget={showTarget}
        />
      ))}
    </div>
  );
}
