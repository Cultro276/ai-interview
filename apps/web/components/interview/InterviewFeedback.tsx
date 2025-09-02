"use client";

import React, { useState, useEffect, useRef } from 'react';
import { useInterviewTheme } from './InterviewDesignSystem';
import { cn } from '@/components/ui/utils';

// Real-time feedback and status
interface FeedbackMessage {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error' | 'tip';
  title: string;
  message: string;
  duration?: number; // auto-dismiss after milliseconds
  timestamp: Date;
  persistent?: boolean; // don't auto-dismiss
  action?: {
    label: string;
    onClick: () => void;
  };
  metadata?: Record<string, any>;
}

interface InterviewFeedbackProps {
  messages: FeedbackMessage[];
  showNotifications?: boolean;
  autoDismiss?: boolean;
  maxMessages?: number;
  position?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left' | 'center';
  onMessageDismiss?: (messageId: string) => void;
  onMessageAction?: (messageId: string, action: string) => void;
  className?: string;
  variant?: 'toast' | 'inline' | 'sidebar';
}

export function InterviewFeedback({
  messages,
  showNotifications = true,
  autoDismiss = true,
  maxMessages = 5,
  position = 'top-right',
  onMessageDismiss,
  onMessageAction,
  className = '',
  variant = 'toast'
}: InterviewFeedbackProps) {
  const theme = useInterviewTheme();
  const [visibleMessages, setVisibleMessages] = useState<FeedbackMessage[]>([]);
  const timeoutRefs = useRef<Map<string, NodeJS.Timeout>>(new Map());

  // Filter and sort messages
  useEffect(() => {
    const sortedMessages = [...messages]
      .sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime())
      .slice(0, maxMessages);
    
    setVisibleMessages(sortedMessages);
  }, [messages, maxMessages]);

  // Auto-dismiss messages
  useEffect(() => {
    if (!autoDismiss) return;

    visibleMessages.forEach(message => {
      if (message.persistent || timeoutRefs.current.has(message.id)) return;

      const duration = message.duration || getDefaultDuration(message.type);
      const timeout = setTimeout(() => {
        handleDismiss(message.id);
      }, duration);

      timeoutRefs.current.set(message.id, timeout);
    });

    return () => {
      timeoutRefs.current.forEach(timeout => clearTimeout(timeout));
      timeoutRefs.current.clear();
    };
  }, [visibleMessages, autoDismiss]);

  const getDefaultDuration = (type: FeedbackMessage['type']) => {
    switch (type) {
      case 'error':
        return 8000;
      case 'warning':
        return 6000;
      case 'success':
        return 4000;
      case 'info':
        return 5000;
      case 'tip':
        return 7000;
      default:
        return 5000;
    }
  };

  const handleDismiss = (messageId: string) => {
    const timeout = timeoutRefs.current.get(messageId);
    if (timeout) {
      clearTimeout(timeout);
      timeoutRefs.current.delete(messageId);
    }
    onMessageDismiss?.(messageId);
  };

  const getPositionClasses = () => {
    const baseClasses = 'fixed z-50';
    
    switch (position) {
      case 'top-right':
        return `${baseClasses} top-4 right-4`;
      case 'top-left':
        return `${baseClasses} top-4 left-4`;
      case 'bottom-right':
        return `${baseClasses} bottom-4 right-4`;
      case 'bottom-left':
        return `${baseClasses} bottom-4 left-4`;
      case 'center':
        return `${baseClasses} top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2`;
      default:
        return `${baseClasses} top-4 right-4`;
    }
  };

  const containerClasses = cn(
    'interview-feedback',
    {
      [getPositionClasses()]: variant === 'toast',
      'w-full': variant === 'inline',
      'h-full flex flex-col': variant === 'sidebar',
    },
    className
  );

  if (!showNotifications || visibleMessages.length === 0) {
    return null;
  }

  return (
    <div className={containerClasses}>
      <div className={cn(
        'feedback-container',
        {
          'space-y-2 max-w-sm': variant === 'toast',
          'space-y-3': variant === 'inline',
          'flex-1 overflow-auto space-y-2': variant === 'sidebar',
        }
      )}>
        {visibleMessages.map(message => (
          <FeedbackMessageItem
            key={message.id}
            message={message}
            onDismiss={() => handleDismiss(message.id)}
            onAction={(action) => onMessageAction?.(message.id, action)}
            variant={variant}
            theme={theme}
          />
        ))}
      </div>
    </div>
  );
}

// Individual Feedback Message Component
interface FeedbackMessageItemProps {
  message: FeedbackMessage;
  onDismiss: () => void;
  onAction: (action: string) => void;
  variant: 'toast' | 'inline' | 'sidebar';
  theme: any;
}

function FeedbackMessageItem({
  message,
  onDismiss,
  onAction,
  variant,
  theme
}: FeedbackMessageItemProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [isLeaving, setIsLeaving] = useState(false);

  useEffect(() => {
    // Entrance animation
    setTimeout(() => setIsVisible(true), 10);
  }, []);

  const getTypeConfig = (type: FeedbackMessage['type']) => {
    switch (type) {
      case 'success':
        return {
          icon: '✅',
          color: theme.colors.status.success,
          bgColor: `${theme.colors.status.success}10`,
          borderColor: `${theme.colors.status.success}30`,
        };
      case 'error':
        return {
          icon: '❌',
          color: theme.colors.status.error,
          bgColor: `${theme.colors.status.error}10`,
          borderColor: `${theme.colors.status.error}30`,
        };
      case 'warning':
        return {
          icon: '⚠️',
          color: theme.colors.status.warning,
          bgColor: `${theme.colors.status.warning}10`,
          borderColor: `${theme.colors.status.warning}30`,
        };
      case 'info':
        return {
          icon: 'ℹ️',
          color: theme.colors.status.info,
          bgColor: `${theme.colors.status.info}10`,
          borderColor: `${theme.colors.status.info}30`,
        };
      case 'tip':
        return {
          icon: '💡',
          color: theme.colors.primary,
          bgColor: `${theme.colors.primary}10`,
          borderColor: `${theme.colors.primary}30`,
        };
      default:
        return {
          icon: 'ℹ️',
          color: theme.colors.text.primary,
          bgColor: `${theme.colors.text.muted}10`,
          borderColor: `${theme.colors.text.muted}30`,
        };
    }
  };

  const typeConfig = getTypeConfig(message.type);

  const handleDismissWithAnimation = () => {
    setIsLeaving(true);
    setTimeout(() => onDismiss(), 300);
  };

  const formatTimestamp = (timestamp: Date) => {
    const now = new Date();
    const diff = now.getTime() - timestamp.getTime();
    
    if (diff < 60000) return 'şimdi';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}dk önce`;
    return timestamp.toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div 
      className={cn(
        'feedback-message border rounded-lg p-3 transition-all duration-300 ease-out',
        {
          'opacity-0 transform translate-x-full': (!isVisible || isLeaving) && variant === 'toast',
          'opacity-100 transform translate-x-0': isVisible && !isLeaving && variant === 'toast',
          'opacity-0 transform -translate-y-2': (!isVisible || isLeaving) && variant !== 'toast',
          'opacity-100 transform translate-y-0': isVisible && !isLeaving && variant !== 'toast',
          'shadow-lg': variant === 'toast',
        }
      )}
      style={{
        backgroundColor: typeConfig.bgColor,
        borderColor: typeConfig.borderColor,
        boxShadow: variant === 'toast' ? theme.shadows.lg : 'none',
      }}
    >
      <div className="message-content">
        <div className="message-header flex items-start justify-between">
          <div className="message-info flex items-start space-x-2 flex-1">
            <div className="message-icon text-lg flex-shrink-0">
              {typeConfig.icon}
            </div>
            <div className="message-text flex-1 min-w-0">
              <h4 
                className="message-title text-sm font-medium"
                style={{ 
                  color: typeConfig.color,
                  fontSize: theme.typography.fontSize.sm,
                  fontWeight: theme.typography.fontWeight.medium,
                }}
              >
                {message.title}
              </h4>
              <p 
                className="message-description text-sm mt-1 leading-relaxed"
                style={{ 
                  color: theme.colors.text.secondary,
                  fontSize: theme.typography.fontSize.sm,
                }}
              >
                {message.message}
              </p>
            </div>
          </div>
          
          <button
            onClick={handleDismissWithAnimation}
            className="message-dismiss ml-2 w-5 h-5 flex items-center justify-center text-xs transition-colors duration-200 hover:opacity-70 flex-shrink-0"
            style={{ color: theme.colors.text.muted }}
          >
            ×
          </button>
        </div>

        {/* Message Metadata */}
        <div className="message-meta flex items-center justify-between mt-2">
          <span 
            className="timestamp text-xs"
            style={{ color: theme.colors.text.muted }}
          >
            {formatTimestamp(message.timestamp)}
          </span>
          
          {message.action && (
            <button
              onClick={() => onAction(message.action!.label)}
              className="message-action text-xs px-2 py-1 rounded transition-all duration-200 hover:opacity-80"
              style={{
                backgroundColor: typeConfig.color,
                color: 'white',
              }}
            >
              {message.action.label}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// Real-time Status Indicator
interface StatusIndicatorProps {
  status: 'speaking' | 'listening' | 'thinking' | 'idle' | 'error';
  message?: string;
  showPulse?: boolean;
  className?: string;
}

export function StatusIndicator({
  status,
  message,
  showPulse = true,
  className = ''
}: StatusIndicatorProps) {
  const theme = useInterviewTheme();

  const getStatusConfig = (status: string) => {
    switch (status) {
      case 'speaking':
        return {
          icon: '🗣️',
          label: 'Konuşuyor',
          color: theme.colors.interview.speaking,
          bgColor: `${theme.colors.interview.speaking}15`,
        };
      case 'listening':
        return {
          icon: '👂',
          label: 'Dinliyor',
          color: theme.colors.interview.listening,
          bgColor: `${theme.colors.interview.listening}15`,
        };
      case 'thinking':
        return {
          icon: '🤔',
          label: 'Düşünüyor',
          color: theme.colors.interview.thinking,
          bgColor: `${theme.colors.interview.thinking}15`,
        };
      case 'idle':
        return {
          icon: '⏸️',
          label: 'Bekliyor',
          color: theme.colors.interview.idle,
          bgColor: `${theme.colors.interview.idle}15`,
        };
      case 'error':
        return {
          icon: '❌',
          label: 'Hata',
          color: theme.colors.status.error,
          bgColor: `${theme.colors.status.error}15`,
        };
      default:
        return {
          icon: '⏸️',
          label: 'Bilinmiyor',
          color: theme.colors.text.muted,
          bgColor: `${theme.colors.text.muted}15`,
        };
    }
  };

  const config = getStatusConfig(status);

  return (
    <div 
      className={cn(
        'status-indicator flex items-center space-x-2 px-3 py-2 rounded-lg',
        {
          'animate-pulse': showPulse && status !== 'idle',
        },
        className
      )}
      style={{
        backgroundColor: config.bgColor,
        border: `1px solid ${config.color}30`,
      }}
    >
      <span className="status-icon">{config.icon}</span>
      <div className="status-text">
        <p 
          className="status-label text-sm font-medium"
          style={{ color: config.color }}
        >
          {message || config.label}
        </p>
      </div>
    </div>
  );
}

// Live Feedback Provider
interface LiveFeedbackContextType {
  addMessage: (message: Omit<FeedbackMessage, 'id' | 'timestamp'>) => void;
  removeMessage: (messageId: string) => void;
  clearMessages: () => void;
  messages: FeedbackMessage[];
}

const LiveFeedbackContext = React.createContext<LiveFeedbackContextType | null>(null);

interface LiveFeedbackProviderProps {
  children: React.ReactNode;
  maxMessages?: number;
}

export function LiveFeedbackProvider({ 
  children, 
  maxMessages = 10 
}: LiveFeedbackProviderProps) {
  const [messages, setMessages] = useState<FeedbackMessage[]>([]);

  const addMessage = (messageData: Omit<FeedbackMessage, 'id' | 'timestamp'>) => {
    const newMessage: FeedbackMessage = {
      ...messageData,
      id: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      timestamp: new Date(),
    };

    setMessages(prev => {
      const updated = [newMessage, ...prev].slice(0, maxMessages);
      return updated;
    });
  };

  const removeMessage = (messageId: string) => {
    setMessages(prev => prev.filter(msg => msg.id !== messageId));
  };

  const clearMessages = () => {
    setMessages([]);
  };

  const value: LiveFeedbackContextType = {
    addMessage,
    removeMessage,
    clearMessages,
    messages,
  };

  return (
    <LiveFeedbackContext.Provider value={value}>
      {children}
    </LiveFeedbackContext.Provider>
  );
}

export function useLiveFeedback() {
  const context = React.useContext(LiveFeedbackContext);
  if (!context) {
    throw new Error('useLiveFeedback must be used within LiveFeedbackProvider');
  }
  return context;
}

// Progress Feedback Component
interface ProgressFeedbackProps {
  currentStep: number;
  totalSteps: number;
  stepName?: string;
  progress?: number; // 0-100
  estimatedTimeLeft?: number; // in seconds
  className?: string;
}

export function ProgressFeedback({
  currentStep,
  totalSteps,
  stepName,
  progress,
  estimatedTimeLeft,
  className = ''
}: ProgressFeedbackProps) {
  const theme = useInterviewTheme();

  const formatTime = (seconds: number) => {
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return remainingSeconds > 0 ? `${minutes}m ${remainingSeconds}s` : `${minutes}m`;
  };

  return (
    <div 
      className={cn('progress-feedback p-3 rounded-lg border', className)}
      style={{
        backgroundColor: `${theme.colors.primary}05`,
        borderColor: `${theme.colors.primary}30`,
      }}
    >
      <div className="progress-content space-y-2">
        {/* Step Info */}
        <div className="step-info flex items-center justify-between">
          <div>
            <p 
              className="text-sm font-medium"
              style={{ color: theme.colors.text.primary }}
            >
              {stepName ? `${currentStep}. ${stepName}` : `Adım ${currentStep}`}
            </p>
            <p 
              className="text-xs"
              style={{ color: theme.colors.text.muted }}
            >
              {totalSteps} adımdan {currentStep}
            </p>
          </div>
          
          {estimatedTimeLeft && (
            <div className="time-estimate text-right">
              <p 
                className="text-sm font-medium"
                style={{ color: theme.colors.primary }}
              >
                ~{formatTime(estimatedTimeLeft)}
              </p>
              <p 
                className="text-xs"
                style={{ color: theme.colors.text.muted }}
              >
                kalan süre
              </p>
            </div>
          )}
        </div>

        {/* Progress Bar */}
        {progress !== undefined && (
          <div className="progress-bar">
            <div 
              className="w-full h-2 rounded-full overflow-hidden"
              style={{ backgroundColor: `${theme.colors.text.muted}20` }}
            >
              <div 
                className="h-full transition-all duration-500 ease-out"
                style={{ 
                  width: `${progress}%`,
                  backgroundColor: theme.colors.primary,
                }}
              />
            </div>
            <div className="flex justify-between mt-1">
              <span 
                className="text-xs"
                style={{ color: theme.colors.text.muted }}
              >
                0%
              </span>
              <span 
                className="text-xs font-medium"
                style={{ color: theme.colors.primary }}
              >
                {Math.round(progress)}%
              </span>
              <span 
                className="text-xs"
                style={{ color: theme.colors.text.muted }}
              >
                100%
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
