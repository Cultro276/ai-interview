"use client";

import React, { useEffect, useState, useRef } from 'react';
import { useInterviewTheme } from './InterviewDesignSystem';
import { cn } from '@/components/ui/utils';

// Audio quality and feedback
interface AudioMetrics {
  volume: number; // 0-100
  clarity: number; // 0-100
  noise: number; // 0-100
  connection: 'excellent' | 'good' | 'poor' | 'disconnected';
  latency: number; // in milliseconds
  bitrate: number; // in kbps
  sampleRate: number; // in Hz
  frequency?: number[]; // frequency spectrum data
}

interface InterviewAudioProps {
  metrics: AudioMetrics;
  showVisualizer?: boolean;
  showQualityIndicator?: boolean;
  showDetailedMetrics?: boolean;
  onQualityChange?: (quality: AudioMetrics) => void;
  onMicrophoneTest?: () => void;
  className?: string;
  variant?: 'compact' | 'detailed' | 'minimal';
}

export function InterviewAudio({
  metrics,
  showVisualizer = true,
  showQualityIndicator = true,
  showDetailedMetrics = false,
  onQualityChange,
  onMicrophoneTest,
  className = '',
  variant = 'detailed'
}: InterviewAudioProps) {
  const theme = useInterviewTheme();
  const [isListening, setIsListening] = useState(false);
  const [audioContext, setAudioContext] = useState<AudioContext | null>(null);
  const [analyzer, setAnalyzer] = useState<AnalyserNode | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number | undefined>(undefined);

  useEffect(() => {
    if (showVisualizer && canvasRef.current) {
      startAudioVisualization();
    }
    
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
      if (audioContext) {
        audioContext.close();
      }
    };
  }, [showVisualizer]);

  const startAudioVisualization = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const context = new AudioContext();
      const analyserNode = context.createAnalyser();
      const source = context.createMediaStreamSource(stream);
      
      analyserNode.fftSize = 256;
      source.connect(analyserNode);
      
      setAudioContext(context);
      setAnalyzer(analyserNode);
      setIsListening(true);
      
      drawVisualization(analyserNode);
    } catch (error) {
      console.error('Error accessing microphone:', error);
    }
  };

  const drawVisualization = (analyserNode: AnalyserNode) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    const bufferLength = analyserNode.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    
    const draw = () => {
      analyserNode.getByteFrequencyData(dataArray);
      
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      
      const barWidth = canvas.width / bufferLength;
      let x = 0;
      
      for (let i = 0; i < bufferLength; i++) {
        const barHeight = (dataArray[i] / 255) * canvas.height;
        
        const hue = (i / bufferLength) * 360;
        ctx.fillStyle = `hsl(${hue}, 70%, 60%)`;
        ctx.fillRect(x, canvas.height - barHeight, barWidth, barHeight);
        
        x += barWidth;
      }
      
      animationRef.current = requestAnimationFrame(draw);
    };
    
    draw();
  };

  const getQualityColor = (connection: string) => {
    switch (connection) {
      case 'excellent':
        return theme.colors.status.success;
      case 'good':
        return theme.colors.status.warning;
      case 'poor':
        return theme.colors.status.error;
      default:
        return theme.colors.text.muted;
    }
  };

  const getQualityIcon = (connection: string) => {
    switch (connection) {
      case 'excellent':
        return '🟢';
      case 'good':
        return '🟡';
      case 'poor':
        return '🔴';
      default:
        return '⚫';
    }
  };

  const getConnectionLabel = (connection: string) => {
    switch (connection) {
      case 'excellent':
        return 'Mükemmel';
      case 'good':
        return 'İyi';
      case 'poor':
        return 'Zayıf';
      default:
        return 'Bağlantı Yok';
    }
  };

  const getOverallQualityScore = () => {
    const volumeScore = Math.min(metrics.volume, 80) / 80 * 100; // Optimal volume is around 80%
    const clarityScore = metrics.clarity;
    const noiseScore = Math.max(0, 100 - metrics.noise);
    const connectionScore = {
      excellent: 100,
      good: 75,
      poor: 40,
      disconnected: 0
    }[metrics.connection];
    
    return Math.round((volumeScore + clarityScore + noiseScore + connectionScore) / 4);
  };

  if (variant === 'minimal') {
    return (
      <div className={cn('interview-audio-minimal flex items-center space-x-2', className)}>
        <div className="quality-indicator flex items-center space-x-1">
          <span>{getQualityIcon(metrics.connection)}</span>
          <span 
            className="text-xs"
            style={{ color: getQualityColor(metrics.connection) }}
          >
            {getConnectionLabel(metrics.connection)}
          </span>
        </div>
        {showVisualizer && (
          <div className="volume-indicator flex items-center space-x-1">
            <div 
              className="w-16 h-1 rounded-full overflow-hidden"
              style={{ backgroundColor: `${theme.colors.text.muted}30` }}
            >
              <div 
                className="h-full transition-all duration-100"
                style={{ 
                  width: `${metrics.volume}%`,
                  backgroundColor: theme.colors.primary,
                }}
              />
            </div>
          </div>
        )}
      </div>
    );
  }

  const audioClasses = cn(
    'interview-audio',
    {
      'p-4 bg-white rounded-lg border': variant === 'detailed',
      'p-2': variant === 'compact',
    },
    className
  );

  return (
    <div 
      className={audioClasses}
      style={{
        backgroundColor: variant === 'detailed' ? theme.colors.surface : 'transparent',
        borderColor: `${theme.colors.text.muted}20`,
      }}
    >
      {/* Audio Header */}
      {variant === 'detailed' && (
        <div className="audio-header flex items-center justify-between mb-4">
          <h3 
            className="text-lg font-semibold"
            style={{ 
              color: theme.colors.text.primary,
              fontSize: theme.typography.fontSize.lg,
              fontWeight: theme.typography.fontWeight.semibold,
            }}
          >
            Ses Kalitesi
          </h3>
          
          {onMicrophoneTest && (
            <button
              onClick={onMicrophoneTest}
              className="test-mic-btn flex items-center space-x-1 px-3 py-1 text-xs rounded-md transition-all duration-200 hover:opacity-80"
              style={{
                backgroundColor: theme.colors.primary,
                color: 'white',
              }}
            >
              <span>🎤</span>
              <span>Test Et</span>
            </button>
          )}
        </div>
      )}

      {/* Quality Overview */}
      {showQualityIndicator && (
        <div 
          className="quality-overview p-3 rounded-lg mb-4"
          style={{
            backgroundColor: `${getQualityColor(metrics.connection)}10`,
            border: `1px solid ${getQualityColor(metrics.connection)}30`,
          }}
        >
          <div className="flex items-center justify-between">
            <div className="quality-status flex items-center space-x-2">
              <span className="text-lg">{getQualityIcon(metrics.connection)}</span>
              <div>
                <p 
                  className="font-medium"
                  style={{ 
                    color: getQualityColor(metrics.connection),
                    fontSize: theme.typography.fontSize.sm,
                  }}
                >
                  {getConnectionLabel(metrics.connection)}
                </p>
                <p 
                  className="text-xs"
                  style={{ color: theme.colors.text.muted }}
                >
                  Kalite Skoru: {getOverallQualityScore()}/100
                </p>
              </div>
            </div>
            
            {metrics.latency > 0 && (
              <div className="latency-info text-right">
                <p 
                  className="text-sm font-medium"
                  style={{ color: theme.colors.text.primary }}
                >
                  {metrics.latency}ms
                </p>
                <p 
                  className="text-xs"
                  style={{ color: theme.colors.text.muted }}
                >
                  Gecikme
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Audio Visualizer */}
      {showVisualizer && (
        <div className="audio-visualizer mb-4">
          <div className="visualizer-container">
            {/* Volume Bar */}
            <div className="volume-section mb-3">
              <div className="flex items-center justify-between mb-1">
                <span 
                  className="text-xs font-medium"
                  style={{ color: theme.colors.text.secondary }}
                >
                  Ses Seviyesi
                </span>
                <span 
                  className="text-xs"
                  style={{ color: theme.colors.text.muted }}
                >
                  {metrics.volume}%
                </span>
              </div>
              <div 
                className="volume-bar w-full h-2 rounded-full overflow-hidden"
                style={{ backgroundColor: `${theme.colors.text.muted}20` }}
              >
                <div 
                  className="volume-fill h-full transition-all duration-100 rounded-full"
                  style={{ 
                    width: `${metrics.volume}%`,
                    backgroundColor: metrics.volume > 80 ? theme.colors.status.warning :
                                   metrics.volume > 20 ? theme.colors.status.success :
                                   theme.colors.status.error,
                  }}
                />
              </div>
            </div>

            {/* Frequency Visualizer Canvas */}
            <div className="frequency-visualizer">
              <canvas
                ref={canvasRef}
                width={300}
                height={60}
                className="w-full h-15 rounded border"
                style={{ 
                  backgroundColor: `${theme.colors.text.muted}05`,
                  borderColor: `${theme.colors.text.muted}20`,
                }}
              />
            </div>
          </div>
        </div>
      )}

      {/* Detailed Metrics */}
      {showDetailedMetrics && (
        <div className="detailed-metrics">
          <div className="metrics-grid grid grid-cols-2 gap-3">
            {/* Clarity */}
            <div className="metric-item">
              <div className="flex items-center justify-between mb-1">
                <span 
                  className="text-xs font-medium"
                  style={{ color: theme.colors.text.secondary }}
                >
                  Netlik
                </span>
                <span 
                  className="text-xs"
                  style={{ color: theme.colors.text.muted }}
                >
                  {metrics.clarity}%
                </span>
              </div>
              <div 
                className="metric-bar w-full h-1.5 rounded-full overflow-hidden"
                style={{ backgroundColor: `${theme.colors.text.muted}20` }}
              >
                <div 
                  className="metric-fill h-full transition-all duration-300"
                  style={{ 
                    width: `${metrics.clarity}%`,
                    backgroundColor: theme.colors.status.info,
                  }}
                />
              </div>
            </div>

            {/* Noise Level */}
            <div className="metric-item">
              <div className="flex items-center justify-between mb-1">
                <span 
                  className="text-xs font-medium"
                  style={{ color: theme.colors.text.secondary }}
                >
                  Gürültü
                </span>
                <span 
                  className="text-xs"
                  style={{ color: theme.colors.text.muted }}
                >
                  {metrics.noise}%
                </span>
              </div>
              <div 
                className="metric-bar w-full h-1.5 rounded-full overflow-hidden"
                style={{ backgroundColor: `${theme.colors.text.muted}20` }}
              >
                <div 
                  className="metric-fill h-full transition-all duration-300"
                  style={{ 
                    width: `${metrics.noise}%`,
                    backgroundColor: metrics.noise > 50 ? theme.colors.status.error :
                                   metrics.noise > 25 ? theme.colors.status.warning :
                                   theme.colors.status.success,
                  }}
                />
              </div>
            </div>

            {/* Bitrate */}
            {metrics.bitrate > 0 && (
              <div className="metric-item">
                <p 
                  className="text-xs font-medium"
                  style={{ color: theme.colors.text.secondary }}
                >
                  Bit Hızı
                </p>
                <p 
                  className="text-sm font-bold"
                  style={{ color: theme.colors.text.primary }}
                >
                  {metrics.bitrate} kbps
                </p>
              </div>
            )}

            {/* Sample Rate */}
            {metrics.sampleRate > 0 && (
              <div className="metric-item">
                <p 
                  className="text-xs font-medium"
                  style={{ color: theme.colors.text.secondary }}
                >
                  Örnekleme
                </p>
                <p 
                  className="text-sm font-bold"
                  style={{ color: theme.colors.text.primary }}
                >
                  {metrics.sampleRate / 1000} kHz
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Audio Status Indicators */}
      <div className="audio-status mt-4 flex items-center justify-between">
        <div className="status-indicators flex items-center space-x-3">
          {/* Microphone Status */}
          <div className="mic-status flex items-center space-x-1">
            <span className={cn(
              "w-2 h-2 rounded-full",
              isListening ? "animate-pulse" : ""
            )} style={{ 
              backgroundColor: isListening ? theme.colors.status.success : theme.colors.text.muted 
            }} />
            <span 
              className="text-xs"
              style={{ color: theme.colors.text.muted }}
            >
              {isListening ? 'Mikrofon Aktif' : 'Mikrofon Pasif'}
            </span>
          </div>

          {/* Connection Status */}
          <div className="connection-status flex items-center space-x-1">
            <span>{getQualityIcon(metrics.connection)}</span>
            <span 
              className="text-xs"
              style={{ color: getQualityColor(metrics.connection) }}
            >
              {getConnectionLabel(metrics.connection)}
            </span>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="quick-actions flex items-center space-x-2">
          <button
            className="action-btn w-6 h-6 rounded-full flex items-center justify-center text-xs transition-all duration-200 hover:opacity-80"
            style={{
              backgroundColor: `${theme.colors.primary}20`,
              color: theme.colors.primary,
            }}
          >
            ⚙️
          </button>
        </div>
      </div>
    </div>
  );
}

// Audio Level Meter Component
interface AudioLevelMeterProps {
  level: number; // 0-100
  orientation?: 'horizontal' | 'vertical';
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
  className?: string;
}

export function AudioLevelMeter({
  level,
  orientation = 'horizontal',
  size = 'md',
  showLabel = true,
  className = ''
}: AudioLevelMeterProps) {
  const theme = useInterviewTheme();

  const sizeClasses = {
    sm: orientation === 'horizontal' ? 'w-16 h-1' : 'w-1 h-16',
    md: orientation === 'horizontal' ? 'w-24 h-2' : 'w-2 h-24',
    lg: orientation === 'horizontal' ? 'w-32 h-3' : 'w-3 h-32',
  };

  const getLevelColor = (level: number) => {
    if (level > 80) return theme.colors.status.error;
    if (level > 60) return theme.colors.status.warning;
    if (level > 20) return theme.colors.status.success;
    return theme.colors.text.muted;
  };

  return (
    <div className={cn('audio-level-meter flex items-center space-x-2', className)}>
      {showLabel && orientation === 'horizontal' && (
        <span 
          className="text-xs font-medium"
          style={{ color: theme.colors.text.secondary }}
        >
          Ses
        </span>
      )}
      
      <div 
        className={cn('level-container rounded-full overflow-hidden', sizeClasses[size])}
        style={{ backgroundColor: `${theme.colors.text.muted}20` }}
      >
        <div 
          className="level-fill transition-all duration-100"
          style={{ 
            [orientation === 'horizontal' ? 'width' : 'height']: `${level}%`,
            backgroundColor: getLevelColor(level),
            [orientation === 'horizontal' ? 'height' : 'width']: '100%',
          }}
        />
      </div>
      
      {showLabel && (
        <span 
          className="text-xs"
          style={{ color: theme.colors.text.muted }}
        >
          {level}%
        </span>
      )}
    </div>
  );
}

// Audio Device Selector
interface AudioDeviceInfo {
  deviceId: string;
  label: string;
  kind: 'audioinput' | 'audiooutput';
}

interface AudioDeviceSelectorProps {
  devices: AudioDeviceInfo[];
  selectedDevice?: string;
  onDeviceChange: (deviceId: string) => void;
  className?: string;
}

export function AudioDeviceSelector({
  devices,
  selectedDevice,
  onDeviceChange,
  className = ''
}: AudioDeviceSelectorProps) {
  const theme = useInterviewTheme();

  return (
    <div className={cn('audio-device-selector', className)}>
      <label 
        className="block text-sm font-medium mb-2"
        style={{ color: theme.colors.text.primary }}
      >
        Mikrofon Seçimi
      </label>
      
      <select
        value={selectedDevice}
        onChange={(e) => onDeviceChange(e.target.value)}
        className="w-full px-3 py-2 text-sm border rounded-md focus:outline-none focus:ring-2 focus:ring-opacity-50"
        style={{
          backgroundColor: theme.colors.background,
          borderColor: `${theme.colors.text.muted}30`,
          color: theme.colors.text.primary,
          '--focus-ring-color': `${theme.colors.primary}50`,
        } as React.CSSProperties}
      >
        {devices.map(device => (
          <option key={device.deviceId} value={device.deviceId}>
            {device.label || `Mikrofon ${device.deviceId.slice(0, 8)}...`}
          </option>
        ))}
      </select>
    </div>
  );
}
