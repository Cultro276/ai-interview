"use client";

import React, { useRef, useEffect, useState } from 'react';
import { useInterviewTheme } from './InterviewDesignSystem';
import { cn } from '@/components/ui/utils';

// Professional video interface
interface VideoStream {
  id: string;
  stream: MediaStream | null;
  type: 'camera' | 'screen' | 'avatar';
  label?: string;
  muted?: boolean;
  paused?: boolean;
  mirrored?: boolean;
  quality?: 'low' | 'medium' | 'high';
}

interface InterviewVideoProps {
  streams: VideoStream[];
  layout: 'grid' | 'focus' | 'side-by-side' | 'picture-in-picture';
  showControls?: boolean;
  showRecordingIndicator?: boolean;
  showQualityIndicator?: boolean;
  onStreamClick?: (streamId: string) => void;
  onMuteToggle?: (streamId: string) => void;
  onPauseToggle?: (streamId: string) => void;
  onQualityChange?: (streamId: string, quality: VideoStream['quality']) => void;
  className?: string;
  aspectRatio?: '16:9' | '4:3' | '1:1' | 'auto';
  maxWidth?: string;
  maxHeight?: string;
}

export function InterviewVideo({
  streams,
  layout,
  showControls = true,
  showRecordingIndicator = true,
  showQualityIndicator = false,
  onStreamClick,
  onMuteToggle,
  onPauseToggle,
  onQualityChange,
  className = '',
  aspectRatio = '16:9',
  maxWidth = '100%',
  maxHeight = '80vh'
}: InterviewVideoProps) {
  const theme = useInterviewTheme();
  const [focusedStream, setFocusedStream] = useState<string | null>(null);
  const [isRecording, setIsRecording] = useState(false);

  const getLayoutClasses = () => {
    switch (layout) {
      case 'grid':
        return cn('grid gap-4', {
          'grid-cols-1': streams.length === 1,
          'grid-cols-2': streams.length === 2,
          'grid-cols-2 md:grid-cols-3': streams.length >= 3,
        });
      case 'focus':
        return 'flex flex-col space-y-4';
      case 'side-by-side':
        return 'flex space-x-4';
      case 'picture-in-picture':
        return 'relative';
      default:
        return 'flex space-x-4';
    }
  };

  const getAspectRatioClasses = () => {
    switch (aspectRatio) {
      case '16:9':
        return 'aspect-video';
      case '4:3':
        return 'aspect-[4/3]';
      case '1:1':
        return 'aspect-square';
      default:
        return '';
    }
  };

  const videoContainerClasses = cn(
    'interview-video w-full',
    getLayoutClasses(),
    className
  );

  const getStreamPriority = (stream: VideoStream) => {
    if (layout === 'focus') {
      if (focusedStream === stream.id) return 'primary';
      return 'secondary';
    }
    if (layout === 'picture-in-picture') {
      if (stream.type === 'camera') return 'pip';
      return 'primary';
    }
    return 'equal';
  };

  return (
    <div 
      className={videoContainerClasses}
      style={{ maxWidth, maxHeight }}
    >
      {streams.map(stream => {
        const priority = getStreamPriority(stream);
        
        return (
          <VideoStreamItem
            key={stream.id}
            stream={stream}
            priority={priority}
            aspectRatio={aspectRatio}
            showControls={showControls}
            showRecordingIndicator={showRecordingIndicator}
            showQualityIndicator={showQualityIndicator}
            isRecording={isRecording}
            onClick={() => {
              onStreamClick?.(stream.id);
              if (layout === 'focus') {
                setFocusedStream(stream.id);
              }
            }}
            onMuteToggle={() => onMuteToggle?.(stream.id)}
            onPauseToggle={() => onPauseToggle?.(stream.id)}
            onQualityChange={(quality) => onQualityChange?.(stream.id, quality)}
            theme={theme}
          />
        );
      })}
    </div>
  );
}

// Individual Video Stream Component
interface VideoStreamItemProps {
  stream: VideoStream;
  priority: 'primary' | 'secondary' | 'pip' | 'equal';
  aspectRatio: string;
  showControls: boolean;
  showRecordingIndicator: boolean;
  showQualityIndicator: boolean;
  isRecording: boolean;
  onClick: () => void;
  onMuteToggle: () => void;
  onPauseToggle: () => void;
  onQualityChange: (quality: VideoStream['quality']) => void;
  theme: any;
}

function VideoStreamItem({
  stream,
  priority,
  aspectRatio,
  showControls,
  showRecordingIndicator,
  showQualityIndicator,
  isRecording,
  onClick,
  onMuteToggle,
  onPauseToggle,
  onQualityChange,
  theme
}: VideoStreamItemProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isHovered, setIsHovered] = useState(false);
  const [videoError, setVideoError] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);

  useEffect(() => {
    if (videoRef.current && stream.stream) {
      videoRef.current.srcObject = stream.stream;
    }
  }, [stream.stream]);

  const getContainerSize = () => {
    switch (priority) {
      case 'primary':
        return 'w-full h-full';
      case 'secondary':
        return 'w-32 h-20';
      case 'pip':
        return 'absolute bottom-4 right-4 w-32 h-20 z-10';
      default:
        return 'w-full h-full';
    }
  };

  const getVideoClasses = () => {
    const baseClasses = cn(
      'video-stream w-full h-full object-cover rounded-lg transition-all duration-300',
      {
        'transform scale-x-[-1]': stream.mirrored,
        'opacity-50': stream.paused,
        'cursor-pointer': !!onClick,
      }
    );

    if (aspectRatio !== 'auto') {
      return cn(baseClasses, {
        'aspect-video': aspectRatio === '16:9',
        'aspect-[4/3]': aspectRatio === '4:3',
        'aspect-square': aspectRatio === '1:1',
      });
    }

    return baseClasses;
  };

  const getStreamTypeIcon = () => {
    switch (stream.type) {
      case 'camera':
        return '📹';
      case 'screen':
        return '🖥️';
      case 'avatar':
        return '🤖';
      default:
        return '📺';
    }
  };

  const getQualityColor = (quality: VideoStream['quality']) => {
    switch (quality) {
      case 'high':
        return theme.colors.status.success;
      case 'medium':
        return theme.colors.status.warning;
      case 'low':
        return theme.colors.status.error;
      default:
        return theme.colors.text.muted;
    }
  };

  const handleFullscreen = async () => {
    if (!videoRef.current) return;

    try {
      if (!isFullscreen) {
        await videoRef.current.requestFullscreen();
        setIsFullscreen(true);
      } else {
        await document.exitFullscreen();
        setIsFullscreen(false);
      }
    } catch (error) {
      console.error('Fullscreen error:', error);
    }
  };

  return (
    <div 
      className={cn(
        'video-container relative bg-black rounded-lg overflow-hidden border-2 transition-all duration-200',
        getContainerSize(),
        {
          'border-blue-500': isHovered && priority !== 'pip',
          'shadow-lg': priority === 'primary',
          'shadow-md': priority === 'secondary',
          'shadow-xl': priority === 'pip',
        }
      )}
      style={{
        borderColor: isHovered ? theme.colors.primary : `${theme.colors.text.muted}30`,
      }}
      // Guard hover state updates to avoid update storms during layout thrashing
      onMouseEnter={() => { if (!isHovered) setIsHovered(true); }}
      onMouseLeave={() => { if (isHovered) setIsHovered(false); }}
      onClick={onClick}
    >
      {/* Video Element */}
      {stream.stream && !videoError ? (
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted={stream.muted}
          className={getVideoClasses()}
          onError={() => setVideoError(true)}
          onLoadedMetadata={() => setVideoError(false)}
        />
      ) : (
        <VideoPlaceholder 
          type={stream.type}
          label={stream.label}
          error={videoError}
          theme={theme}
        />
      )}

      {/* Stream Label */}
      {stream.label && (
        <div 
          className="absolute top-2 left-2 px-2 py-1 rounded text-xs font-medium"
          style={{
            backgroundColor: `${theme.colors.text.primary}80`,
            color: 'white',
          }}
        >
          <span className="mr-1">{getStreamTypeIcon()}</span>
          {stream.label}
        </div>
      )}

      {/* Recording Indicator */}
      {showRecordingIndicator && isRecording && (
        <div className="absolute top-2 right-2 flex items-center space-x-1">
          <div 
            className="w-2 h-2 rounded-full animate-pulse"
            style={{ backgroundColor: theme.colors.status.error }}
          />
          <span 
            className="text-xs font-medium"
            style={{ color: 'white' }}
          >
            REC
          </span>
        </div>
      )}

      {/* Quality Indicator */}
      {showQualityIndicator && stream.quality && (
        <div 
          className="absolute top-2 right-2 px-2 py-1 rounded text-xs font-medium"
          style={{
            backgroundColor: `${getQualityColor(stream.quality)}20`,
            color: getQualityColor(stream.quality),
            border: `1px solid ${getQualityColor(stream.quality)}50`,
          }}
        >
          {stream.quality.toUpperCase()}
        </div>
      )}

      {/* Paused Overlay */}
      {stream.paused && (
        <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-50">
          <div 
            className="w-16 h-16 rounded-full flex items-center justify-center"
            style={{ backgroundColor: `${theme.colors.primary}90` }}
          >
            <span className="text-white text-2xl">⏸️</span>
          </div>
        </div>
      )}

      {/* Video Controls */}
      {showControls && (isHovered || priority === 'primary') && (
        <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black to-transparent p-3">
          <div className="flex items-center justify-between">
            <div className="video-controls flex items-center space-x-2">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onMuteToggle();
                }}
                className={cn(
                  "control-btn w-8 h-8 rounded-full flex items-center justify-center text-white transition-all duration-200 hover:opacity-80",
                  {
                    'bg-red-500': stream.muted,
                    'bg-green-500': !stream.muted,
                  }
                )}
              >
                {stream.muted ? '🔇' : '🔊'}
              </button>
              
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onPauseToggle();
                }}
                className={cn(
                  "control-btn w-8 h-8 rounded-full flex items-center justify-center text-white transition-all duration-200 hover:opacity-80",
                  {
                    'bg-orange-500': stream.paused,
                    'bg-blue-500': !stream.paused,
                  }
                )}
              >
                {stream.paused ? '▶️' : '⏸️'}
              </button>

              {/* Quality Control */}
              <select
                value={stream.quality || 'medium'}
                onChange={(e) => {
                  e.stopPropagation();
                  onQualityChange(e.target.value as VideoStream['quality']);
                }}
                className="quality-select text-xs bg-black bg-opacity-50 text-white border border-white border-opacity-30 rounded px-2 py-1"
              >
                <option value="low">Düşük</option>
                <option value="medium">Orta</option>
                <option value="high">Yüksek</option>
              </select>
            </div>

            <div className="video-actions flex items-center space-x-2">
              {/* Fullscreen Button */}
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleFullscreen();
                }}
                className="control-btn w-8 h-8 rounded-full flex items-center justify-center text-white bg-black bg-opacity-50 transition-all duration-200 hover:opacity-80"
              >
                {isFullscreen ? '⤓' : '⤢'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Video Placeholder Component
interface VideoPlaceholderProps {
  type: VideoStream['type'];
  label?: string;
  error?: boolean;
  theme: any;
}

function VideoPlaceholder({ type, label, error = false, theme }: VideoPlaceholderProps) {
  const getPlaceholderIcon = () => {
    if (error) return '❌';
    
    switch (type) {
      case 'camera':
        return '📹';
      case 'screen':
        return '🖥️';
      case 'avatar':
        return '🤖';
      default:
        return '📺';
    }
  };

  const getPlaceholderMessage = () => {
    if (error) return 'Video yüklenirken hata oluştu';
    
    switch (type) {
      case 'camera':
        return 'Kamera bağlanıyor...';
      case 'screen':
        return 'Ekran paylaşımı bekleniyor...';
      case 'avatar':
        return 'AI Avatar hazırlanıyor...';
      default:
        return 'Video yükleniyor...';
    }
  };

  return (
    <div 
      className="video-placeholder w-full h-full flex flex-col items-center justify-center text-center p-4"
      style={{ backgroundColor: `${theme.colors.text.muted}10` }}
    >
      <div className="placeholder-icon text-4xl mb-2">
        {getPlaceholderIcon()}
      </div>
      
      <p 
        className="placeholder-text text-sm font-medium mb-1"
        style={{ color: theme.colors.text.primary }}
      >
        {label || getPlaceholderMessage()}
      </p>
      
      {error && (
        <p 
          className="error-text text-xs"
          style={{ color: theme.colors.status.error }}
        >
          Bağlantıyı kontrol edin ve tekrar deneyin
        </p>
      )}
      
      {!error && (
        <div className="loading-indicator mt-2">
          <div 
            className="w-6 h-1 rounded-full overflow-hidden"
            style={{ backgroundColor: `${theme.colors.text.muted}30` }}
          >
            <div 
              className="h-full rounded-full animate-pulse"
              style={{ backgroundColor: theme.colors.primary }}
            />
          </div>
        </div>
      )}
    </div>
  );
}

// Video Layout Controller
interface VideoLayoutControllerProps {
  currentLayout: InterviewVideoProps['layout'];
  onLayoutChange: (layout: InterviewVideoProps['layout']) => void;
  className?: string;
}

export function VideoLayoutController({
  currentLayout,
  onLayoutChange,
  className = ''
}: VideoLayoutControllerProps) {
  const theme = useInterviewTheme();

  const layouts = [
    { id: 'grid' as const, label: 'Izgara', icon: '▦' },
    { id: 'focus' as const, label: 'Odak', icon: '⬛' },
    { id: 'side-by-side' as const, label: 'Yan Yana', icon: '▥' },
    { id: 'picture-in-picture' as const, label: 'PiP', icon: '📱' },
  ];

  return (
    <div className={cn('video-layout-controller flex space-x-1', className)}>
      {layouts.map(layout => (
        <button
          key={layout.id}
          onClick={() => onLayoutChange(layout.id)}
          className={cn(
            'layout-btn flex items-center space-x-1 px-3 py-2 text-xs rounded-md transition-all duration-200',
            {
              'ring-2 ring-opacity-50': currentLayout === layout.id,
            }
          )}
          style={{
            backgroundColor: currentLayout === layout.id 
              ? `${theme.colors.primary}20` 
              : theme.colors.surface,
            color: currentLayout === layout.id 
              ? theme.colors.primary 
              : theme.colors.text.secondary,
            border: `1px solid ${theme.colors.text.muted}30`,
              // 'ringColor' is not a valid CSS property, so we remove it.
          }}
        >
          <span>{layout.icon}</span>
          <span>{layout.label}</span>
        </button>
      ))}
    </div>
  );
}
