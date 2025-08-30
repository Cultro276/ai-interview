'use client';

import React, { useState, useEffect, useRef } from 'react';
import { EnhancedCard, EnhancedButton } from '@/components/ui';
import { cn } from '@/components/ui/cn';

interface RealTimeMetric {
  id: string;
  label: string;
  value: number;
  change: number;
  unit?: string;
  color?: string;
}

interface RealTimeEvent {
  id: string;
  timestamp: Date;
  type: 'interview_started' | 'interview_completed' | 'candidate_registered' | 'user_login';
  message: string;
  metadata?: Record<string, any>;
}

interface RealTimeAnalyticsProps {
  title?: string;
  refreshInterval?: number;
  maxEvents?: number;
  showChart?: boolean;
  onMetricClick?: (metric: RealTimeMetric) => void;
}

export function RealTimeAnalytics({
  title = 'Canlı Sistem Durumu',
  refreshInterval = 5000,
  maxEvents = 50,
  showChart = true,
  onMetricClick,
}: RealTimeAnalyticsProps) {
  const [isLive, setIsLive] = useState(true);
  const [metrics, setMetrics] = useState<RealTimeMetric[]>([]);
  const [events, setEvents] = useState<RealTimeEvent[]>([]);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  // Mock data generator for demo
  const generateMockMetrics = (): RealTimeMetric[] => [
    {
      id: 'active_interviews',
      label: 'Aktif Mülakatlar',
      value: Math.floor(Math.random() * 15) + 5,
      change: (Math.random() - 0.5) * 10,
      color: '#3b82f6',
    },
    {
      id: 'online_users',
      label: 'Çevrimiçi Kullanıcılar',
      value: Math.floor(Math.random() * 50) + 20,
      change: (Math.random() - 0.5) * 20,
      color: '#10b981',
    },
    {
      id: 'completed_today',
      label: 'Bugün Tamamlanan',
      value: Math.floor(Math.random() * 30) + 10,
      change: (Math.random() - 0.5) * 15,
      color: '#8b5cf6',
    },
    {
      id: 'avg_response_time',
      label: 'Ort. Yanıt Süresi',
      value: Math.floor(Math.random() * 500) + 200,
      change: (Math.random() - 0.5) * 100,
      unit: 'ms',
      color: '#f59e0b',
    },
  ];

  const generateMockEvent = (): RealTimeEvent => {
    const eventTypes = [
      { type: 'interview_started', message: 'Yeni mülakat başlatıldı' },
      { type: 'interview_completed', message: 'Mülakat tamamlandı' },
      { type: 'candidate_registered', message: 'Yeni aday kaydı' },
      { type: 'user_login', message: 'Kullanıcı girişi' },
    ] as const;

    const event = eventTypes[Math.floor(Math.random() * eventTypes.length)];
    
    return {
      id: `event_${Date.now()}_${Math.random()}`,
      timestamp: new Date(),
      type: event.type,
      message: event.message,
      metadata: {
        userId: `user_${Math.floor(Math.random() * 1000)}`,
        duration: Math.floor(Math.random() * 300) + 60,
      },
    };
  };

  // Fetch real-time data
  const fetchRealTimeData = async () => {
    try {
      // In a real app, this would be an API call
      const newMetrics = generateMockMetrics();
      setMetrics(newMetrics);
      
      // Add random events occasionally
      if (Math.random() < 0.3) {
        const newEvent = generateMockEvent();
        setEvents(prev => [newEvent, ...prev.slice(0, maxEvents - 1)]);
      }
      
      setLastUpdate(new Date());
    } catch (error) {
      console.error('Error fetching real-time data:', error);
    }
  };

  // Start/stop live updates
  useEffect(() => {
    if (isLive) {
      fetchRealTimeData(); // Initial load
      intervalRef.current = setInterval(fetchRealTimeData, refreshInterval);
    } else {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [isLive, refreshInterval]);

  const toggleLive = () => {
    setIsLive(!isLive);
  };

  const formatTimestamp = (date: Date) => {
    return date.toLocaleTimeString('tr-TR', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  const getEventIcon = (type: RealTimeEvent['type']) => {
    switch (type) {
      case 'interview_started':
        return '🎬';
      case 'interview_completed':
        return '✅';
      case 'candidate_registered':
        return '👤';
      case 'user_login':
        return '🔐';
      default:
        return '📊';
    }
  };

  const getEventColor = (type: RealTimeEvent['type']) => {
    switch (type) {
      case 'interview_started':
        return 'text-blue-600 bg-blue-50 dark:bg-blue-900/20';
      case 'interview_completed':
        return 'text-green-600 bg-green-50 dark:bg-green-900/20';
      case 'candidate_registered':
        return 'text-purple-600 bg-purple-50 dark:bg-purple-900/20';
      case 'user_login':
        return 'text-orange-600 bg-orange-50 dark:bg-orange-900/20';
      default:
        return 'text-gray-600 bg-gray-50 dark:bg-gray-900/20';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
            {title}
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Son güncelleme: {formatTimestamp(lastUpdate)}
          </p>
        </div>
        
        <div className="flex items-center space-x-4">
          {/* Live indicator */}
          <div className="flex items-center space-x-2">
            <div className={cn(
              'w-2 h-2 rounded-full',
              isLive ? 'bg-green-500 animate-pulse' : 'bg-gray-400'
            )} />
            <span className="text-sm text-gray-600 dark:text-gray-400">
              {isLive ? 'Canlı' : 'Durduruldu'}
            </span>
          </div>
          
          {/* Controls */}
          <EnhancedButton
            size="sm"
            variant={isLive ? 'error' : 'success'}
            onClick={toggleLive}
            icon={
              isLive ? (
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              ) : (
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.828 14.828a4 4 0 01-5.656 0M9 10h1m4 0h1m-6 4h8m2 2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v11a2 2 0 002 2z" />
                </svg>
              )
            }
          >
            {isLive ? 'Durdur' : 'Başlat'}
          </EnhancedButton>
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {metrics.map((metric) => (
          <EnhancedCard
            key={metric.id}
            variant="elevated"
            padding="md"
            interactive={!!onMetricClick}
            onClick={() => onMetricClick?.(metric)}
            className="cursor-pointer hover:scale-105 transition-transform"
          >
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-gray-600 dark:text-gray-400">
                  {metric.label}
                </span>
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: metric.color }}
                />
              </div>
              
              <div className="space-y-1">
                <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                  {metric.value.toLocaleString('tr-TR')}
                  {metric.unit && <span className="text-sm text-gray-500 ml-1">{metric.unit}</span>}
                </div>
                
                <div className={cn(
                  'flex items-center text-xs',
                  metric.change > 0 ? 'text-green-600' : metric.change < 0 ? 'text-red-600' : 'text-gray-500'
                )}>
                  {metric.change > 0 ? '↗' : metric.change < 0 ? '↘' : '→'}
                  <span className="ml-1">
                    {Math.abs(metric.change).toFixed(1)}%
                  </span>
                </div>
              </div>
            </div>
          </EnhancedCard>
        ))}
      </div>

      {/* Event Stream */}
      <EnhancedCard variant="default" padding="none">
        <div className="p-4 border-b border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Canlı Aktiviteler
          </h3>
        </div>
        
        <div className="max-h-96 overflow-y-auto">
          {events.length === 0 ? (
            <div className="p-8 text-center text-gray-500 dark:text-gray-400">
              <svg className="w-12 h-12 mx-auto mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
              <p>Henüz aktivite yok</p>
              <p className="text-sm mt-1">Canlı güncelleme başladığında aktiviteler burada görünecek</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-200 dark:divide-gray-700">
              {events.map((event) => (
                <div key={event.id} className="p-4 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
                  <div className="flex items-start space-x-3">
                    <div className={cn(
                      'flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-sm',
                      getEventColor(event.type)
                    )}>
                      {getEventIcon(event.type)}
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                          {event.message}
                        </p>
                        <span className="text-xs text-gray-500 dark:text-gray-400">
                          {formatTimestamp(event.timestamp)}
                        </span>
                      </div>
                      
                      {event.metadata && (
                        <div className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                          {Object.entries(event.metadata).map(([key, value]) => (
                            <span key={key} className="mr-3">
                              {key}: {value}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </EnhancedCard>
    </div>
  );
}
