"use client";

import React from 'react';
import { useInterviewTheme } from './InterviewDesignSystem';
import { cn } from '@/components/ui/utils';

// Enhanced progress tracking
interface InterviewStep {
  id: string;
  title: string;
  description: string;
  status: 'pending' | 'active' | 'completed' | 'error' | 'skipped';
  icon?: string;
  duration?: number; // in seconds
  completedAt?: Date;
  order: number;
}

interface InterviewProgressProps {
  steps: InterviewStep[];
  currentStep: string;
  onStepClick?: (stepId: string) => void;
  showTimeline?: boolean;
  showDuration?: boolean;
  showDescription?: boolean;
  variant?: 'horizontal' | 'vertical' | 'compact';
  className?: string;
}

export function InterviewProgress({
  steps,
  currentStep,
  onStepClick,
  showTimeline = true,
  showDuration = true,
  showDescription = true,
  variant = 'horizontal',
  className = ''
}: InterviewProgressProps) {
  const theme = useInterviewTheme();
  
  // Sort steps by order
  const sortedSteps = [...steps].sort((a, b) => a.order - b.order);
  const currentStepIndex = sortedSteps.findIndex(step => step.id === currentStep);
  const totalSteps = sortedSteps.length;
  const completedSteps = sortedSteps.filter(step => step.status === 'completed').length;
  const progressPercentage = totalSteps > 0 ? (completedSteps / totalSteps) * 100 : 0;

  const getStepColor = (step: InterviewStep) => {
    switch (step.status) {
      case 'completed':
        return theme.colors.status.success;
      case 'active':
        return theme.colors.primary;
      case 'error':
        return theme.colors.status.error;
      case 'skipped':
        return theme.colors.text.muted;
      default:
        return theme.colors.text.muted;
    }
  };

  const getStepIcon = (step: InterviewStep) => {
    if (step.icon) return step.icon;
    
    switch (step.status) {
      case 'completed':
        return '✓';
      case 'active':
        return '●';
      case 'error':
        return '✗';
      case 'skipped':
        return '○';
      default:
        return step.order.toString();
    }
  };

  const formatDuration = (seconds: number) => {
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return remainingSeconds > 0 ? `${minutes}m ${remainingSeconds}s` : `${minutes}m`;
  };

  const progressClasses = cn(
    'interview-progress',
    {
      'flex flex-col space-y-4': variant === 'vertical',
      'flex items-center space-x-4': variant === 'horizontal',
      'flex items-center space-x-2': variant === 'compact',
    },
    className
  );

  if (variant === 'compact') {
    return (
      <div className={progressClasses}>
        <div className="progress-summary flex items-center space-x-2">
          <span 
            className="text-sm font-medium"
            style={{ color: theme.colors.text.primary }}
          >
            {completedSteps} / {totalSteps}
          </span>
          <div 
            className="w-24 h-2 rounded-full overflow-hidden"
            style={{ backgroundColor: `${theme.colors.text.muted}20` }}
          >
            <div 
              className="h-full transition-all duration-300 ease-out"
              style={{ 
                width: `${progressPercentage}%`,
                backgroundColor: theme.colors.primary,
              }}
            />
          </div>
          <span 
            className="text-xs"
            style={{ color: theme.colors.text.muted }}
          >
            {Math.round(progressPercentage)}%
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className={progressClasses}>
      {/* Overall Progress Bar */}
      {showTimeline && (
        <div className="progress-overview mb-6">
          <div className="flex items-center justify-between mb-2">
            <h3 
              className="text-sm font-medium"
              style={{ color: theme.colors.text.primary }}
            >
              Görüşme İlerlemesi
            </h3>
            <span 
              className="text-xs"
              style={{ color: theme.colors.text.muted }}
            >
              {completedSteps} / {totalSteps} adım tamamlandı
            </span>
          </div>
          <div 
            className="w-full h-2 rounded-full overflow-hidden"
            style={{ backgroundColor: `${theme.colors.text.muted}20` }}
          >
            <div 
              className="h-full transition-all duration-500 ease-out"
              style={{ 
                width: `${progressPercentage}%`,
                backgroundColor: theme.colors.primary,
              }}
            />
          </div>
        </div>
      )}

      {/* Step List */}
      <div className="progress-steps w-full">
        {variant === 'vertical' ? (
          <div className="space-y-4">
            {sortedSteps.map((step, index) => (
              <StepItem
                key={step.id}
                step={step}
                isActive={step.id === currentStep}
                isClickable={!!onStepClick}
                onClick={() => onStepClick?.(step.id)}
                showDuration={showDuration}
                showDescription={showDescription}
                showConnector={index < sortedSteps.length - 1}
                variant={variant}
                theme={theme}
              />
            ))}
          </div>
        ) : (
          <div className="flex items-center justify-between w-full">
            {sortedSteps.map((step, index) => (
              <React.Fragment key={step.id}>
                <StepItem
                  step={step}
                  isActive={step.id === currentStep}
                  isClickable={!!onStepClick}
                  onClick={() => onStepClick?.(step.id)}
                  showDuration={showDuration}
                  showDescription={showDescription}
                  showConnector={false}
                  variant={variant}
                  theme={theme}
                />
                {index < sortedSteps.length - 1 && (
                  <div 
                    className="flex-1 h-0.5 mx-2"
                    style={{ 
                      backgroundColor: step.status === 'completed' 
                        ? theme.colors.status.success 
                        : `${theme.colors.text.muted}30`
                    }}
                  />
                )}
              </React.Fragment>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// Individual Step Item Component
interface StepItemProps {
  step: InterviewStep;
  isActive: boolean;
  isClickable: boolean;
  onClick: () => void;
  showDuration: boolean;
  showDescription: boolean;
  showConnector: boolean;
  variant: 'horizontal' | 'vertical' | 'compact';
  theme: any;
}

function StepItem({
  step,
  isActive,
  isClickable,
  onClick,
  showDuration,
  showDescription,
  showConnector,
  variant,
  theme
}: StepItemProps) {
  const stepColor = (() => {
    switch (step.status) {
      case 'completed':
        return theme.colors.status.success;
      case 'active':
        return theme.colors.primary;
      case 'error':
        return theme.colors.status.error;
      case 'skipped':
        return theme.colors.text.muted;
      default:
        return theme.colors.text.muted;
    }
  })();

  const stepIcon = (() => {
    if (step.icon) return step.icon;
    
    switch (step.status) {
      case 'completed':
        return '✓';
      case 'active':
        return '●';
      case 'error':
        return '✗';
      case 'skipped':
        return '○';
      default:
        return step.order.toString();
    }
  })();

  const formatDuration = (seconds: number) => {
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return remainingSeconds > 0 ? `${minutes}m ${remainingSeconds}s` : `${minutes}m`;
  };

  return (
    <div className="step-item relative">
      <div 
        className={cn(
          "step-content flex items-start space-x-3 p-3 rounded-lg transition-all duration-200",
          {
            'cursor-pointer hover:bg-opacity-80': isClickable,
            'bg-opacity-10': isActive,
            'flex-col items-center text-center space-x-0 space-y-1': variant === 'horizontal',
          }
        )}
        style={{
          backgroundColor: isActive ? `${stepColor}10` : 'transparent',
          border: isActive ? `1px solid ${stepColor}30` : '1px solid transparent',
        }}
        onClick={isClickable ? onClick : undefined}
      >
        {/* Step Icon */}
        <div 
          className={cn(
            "step-icon flex-shrink-0 flex items-center justify-center rounded-full text-white font-bold transition-all duration-200",
            {
              'w-8 h-8 text-sm': variant === 'horizontal',
              'w-10 h-10 text-base': variant === 'vertical',
            }
          )}
          style={{
            backgroundColor: stepColor,
            boxShadow: step.status === 'active' ? `0 0 0 3px ${stepColor}20` : 'none',
          }}
        >
          {stepIcon}
        </div>

        {/* Step Details */}
        <div className={cn(
          "step-details flex-1",
          {
            'min-w-0': variant === 'vertical',
            'text-center': variant === 'horizontal',
          }
        )}>
          <h4 
            className={cn(
              "step-title font-medium",
              {
                'text-sm': variant === 'horizontal',
                'text-base': variant === 'vertical',
              }
            )}
            style={{ 
              color: isActive ? stepColor : theme.colors.text.primary,
              fontSize: variant === 'horizontal' ? theme.typography.fontSize.sm : theme.typography.fontSize.md,
              fontWeight: theme.typography.fontWeight.medium,
            }}
          >
            {step.title}
          </h4>

          {showDescription && step.description && variant === 'vertical' && (
            <p 
              className="step-description text-sm mt-1"
              style={{ 
                color: theme.colors.text.secondary,
                fontSize: theme.typography.fontSize.sm,
              }}
            >
              {step.description}
            </p>
          )}

          {/* Step Metadata */}
          <div className="step-meta flex items-center space-x-3 mt-1">
            {showDuration && step.duration && (
              <span 
                className="duration text-xs"
                style={{ color: theme.colors.text.muted }}
              >
                {formatDuration(step.duration)}
              </span>
            )}

            {step.completedAt && (
              <span 
                className="completed-time text-xs"
                style={{ color: theme.colors.status.success }}
              >
                {step.completedAt.toLocaleTimeString()}
              </span>
            )}

            {step.status === 'error' && (
              <span 
                className="error-indicator text-xs"
                style={{ color: theme.colors.status.error }}
              >
                Hata
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Connector Line for Vertical Layout */}
      {showConnector && variant === 'vertical' && (
        <div 
          className="step-connector absolute left-5 top-12 w-0.5 h-6"
          style={{ 
            backgroundColor: step.status === 'completed' 
              ? theme.colors.status.success 
              : `${theme.colors.text.muted}30`
          }}
        />
      )}
    </div>
  );
}

// Progress Summary Component
interface ProgressSummaryProps {
  steps: InterviewStep[];
  currentStep: string;
  className?: string;
}

export function ProgressSummary({
  steps,
  currentStep,
  className = ''
}: ProgressSummaryProps) {
  const theme = useInterviewTheme();
  
  const totalSteps = steps.length;
  const completedSteps = steps.filter(step => step.status === 'completed').length;
  const currentStepData = steps.find(step => step.id === currentStep);
  const progressPercentage = totalSteps > 0 ? (completedSteps / totalSteps) * 100 : 0;

  const totalDuration = steps.reduce((sum, step) => sum + (step.duration || 0), 0);
  const completedDuration = steps
    .filter(step => step.status === 'completed')
    .reduce((sum, step) => sum + (step.duration || 0), 0);

  const formatDuration = (seconds: number) => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  return (
    <div 
      className={cn('progress-summary p-4 rounded-lg border', className)}
      style={{
        backgroundColor: theme.colors.surface,
        borderColor: `${theme.colors.text.muted}20`,
      }}
    >
      <div className="summary-content space-y-3">
        {/* Current Step */}
        {currentStepData && (
          <div className="current-step">
            <p 
              className="text-sm font-medium"
              style={{ color: theme.colors.text.primary }}
            >
              Şu an: <span style={{ color: theme.colors.primary }}>{currentStepData.title}</span>
            </p>
          </div>
        )}

        {/* Progress Stats */}
        <div className="progress-stats grid grid-cols-2 gap-4 text-center">
          <div>
            <p 
              className="text-lg font-bold"
              style={{ color: theme.colors.primary }}
            >
              {completedSteps}/{totalSteps}
            </p>
            <p 
              className="text-xs"
              style={{ color: theme.colors.text.muted }}
            >
              Adım
            </p>
          </div>
          
          <div>
            <p 
              className="text-lg font-bold"
              style={{ color: theme.colors.status.success }}
            >
              {Math.round(progressPercentage)}%
            </p>
            <p 
              className="text-xs"
              style={{ color: theme.colors.text.muted }}
            >
              Tamamlandı
            </p>
          </div>
        </div>

        {/* Time Progress */}
        {totalDuration > 0 && (
          <div className="time-progress">
            <div className="flex justify-between text-xs mb-1">
              <span style={{ color: theme.colors.text.muted }}>
                {formatDuration(completedDuration)}
              </span>
              <span style={{ color: theme.colors.text.muted }}>
                {formatDuration(totalDuration)}
              </span>
            </div>
            <div 
              className="w-full h-1 rounded-full overflow-hidden"
              style={{ backgroundColor: `${theme.colors.text.muted}20` }}
            >
              <div 
                className="h-full transition-all duration-300"
                style={{ 
                  width: `${(completedDuration / totalDuration) * 100}%`,
                  backgroundColor: theme.colors.status.success,
                }}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
