"use client";

import React, { useState } from 'react';
import { useInterviewTheme } from './InterviewDesignSystem';
import { cn } from '@/components/ui/utils';

// Smart navigation system
interface NavigationAction {
  id: string;
  label: string;
  icon: string;
  action: () => void;
  disabled?: boolean;
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
  tooltip?: string;
  keyboard?: string; // keyboard shortcut
}

interface InterviewNavigationProps {
  actions: NavigationAction[];
  showBackButton?: boolean;
  showHelp?: boolean;
  showSettings?: boolean;
  onBack?: () => void;
  onHelp?: () => void;
  onSettings?: () => void;
  className?: string;
  position?: 'top' | 'bottom' | 'floating';
  compact?: boolean;
}

export function InterviewNavigation({
  actions,
  showBackButton = true,
  showHelp = true,
  showSettings = false,
  onBack,
  onHelp,
  onSettings,
  className = '',
  position = 'top',
  compact = false
}: InterviewNavigationProps) {
  const theme = useInterviewTheme();
  const [showTooltip, setShowTooltip] = useState<string | null>(null);

  const navigationClasses = cn(
    'interview-navigation flex items-center justify-between px-4 py-3',
    {
      'border-b': position === 'top',
      'border-t': position === 'bottom',
      'fixed top-4 right-4 z-50 bg-white rounded-lg shadow-lg border': position === 'floating',
      'py-2': compact,
    },
    className
  );

  const getActionVariantStyles = (variant: NavigationAction['variant'] = 'secondary') => {
    switch (variant) {
      case 'primary':
        return {
          backgroundColor: theme.colors.primary,
          color: 'white',
          border: 'none',
        };
      case 'secondary':
        return {
          backgroundColor: theme.colors.surface,
          color: theme.colors.text.primary,
          border: `1px solid ${theme.colors.text.muted}30`,
        };
      case 'danger':
        return {
          backgroundColor: theme.colors.status.error,
          color: 'white',
          border: 'none',
        };
      case 'ghost':
        return {
          backgroundColor: 'transparent',
          color: theme.colors.text.secondary,
          border: 'none',
        };
      default:
        return {
          backgroundColor: theme.colors.surface,
          color: theme.colors.text.primary,
          border: `1px solid ${theme.colors.text.muted}30`,
        };
    }
  };

  return (
    <nav 
      className={navigationClasses}
      style={{
        backgroundColor: position === 'floating' ? theme.colors.background : theme.colors.surface,
        borderColor: `${theme.colors.text.muted}20`,
      }}
    >
      {/* Left Section */}
      <div className="nav-left flex items-center space-x-2">
        {showBackButton && onBack && (
          <button
            onClick={onBack}
            className={cn(
              "nav-back flex items-center space-x-2 px-3 py-2 rounded-md transition-all duration-200 hover:opacity-80",
              {
                'px-2 py-1': compact,
              }
            )}
            style={{
              backgroundColor: theme.colors.surface,
              color: theme.colors.text.secondary,
              border: `1px solid ${theme.colors.text.muted}30`,
            }}
          >
            <span>←</span>
            {!compact && <span>Geri</span>}
          </button>
        )}
      </div>

      {/* Center Section - Main Actions */}
      <div className="nav-center flex items-center space-x-2">
        {actions.map(action => (
          <div key={action.id} className="relative">
            <button
              onClick={action.action}
              disabled={action.disabled}
              className={cn(
                "nav-action flex items-center space-x-2 px-4 py-2 rounded-md font-medium transition-all duration-200 hover:opacity-80 focus:outline-none focus:ring-2 focus:ring-opacity-50",
                {
                  'px-3 py-1 text-sm': compact,
                  'opacity-50 cursor-not-allowed': action.disabled,
                }
              )}
              style={{
                ...getActionVariantStyles(action.variant),
              }}
              onMouseEnter={() => action.tooltip && setShowTooltip(action.id)}
              onMouseLeave={() => setShowTooltip(null)}
            >
              <span className="action-icon">{action.icon}</span>
              {!compact && <span className="action-label">{action.label}</span>}
              {action.keyboard && !compact && (
                <span 
                  className="keyboard-shortcut text-xs px-1 py-0.5 rounded"
                  style={{ 
                    backgroundColor: `${theme.colors.text.muted}20`,
                    color: theme.colors.text.muted,
                  }}
                >
                  {action.keyboard}
                </span>
              )}
            </button>

            {/* Tooltip */}
            {showTooltip === action.id && action.tooltip && (
              <div 
                className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-2 py-1 text-xs rounded whitespace-nowrap z-10"
                style={{
                  backgroundColor: theme.colors.text.primary,
                  color: theme.colors.background,
                }}
              >
                {action.tooltip}
                {action.keyboard && (
                  <span className="ml-2 opacity-75">({action.keyboard})</span>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Right Section */}
      <div className="nav-right flex items-center space-x-2">
        {showSettings && onSettings && (
          <button
            onClick={onSettings}
            className={cn(
              "nav-settings p-2 rounded-md transition-all duration-200 hover:opacity-80",
              {
                'p-1': compact,
              }
            )}
            style={{
              backgroundColor: theme.colors.surface,
              color: theme.colors.text.muted,
              border: `1px solid ${theme.colors.text.muted}30`,
            }}
          >
            ⚙️
          </button>
        )}

        {showHelp && onHelp && (
          <button
            onClick={onHelp}
            className={cn(
              "nav-help w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-all duration-200 hover:opacity-80",
              {
                'w-6 h-6 text-xs': compact,
              }
            )}
            style={{
              backgroundColor: theme.colors.primary,
              color: 'white',
            }}
          >
            ?
          </button>
        )}
      </div>
    </nav>
  );
}

// Navigation Context Provider
interface NavigationContextType {
  currentPage: string;
  canGoBack: boolean;
  canGoForward: boolean;
  navigate: (page: string) => void;
  goBack: () => void;
  goForward: () => void;
}

const NavigationContext = React.createContext<NavigationContextType | null>(null);

interface NavigationProviderProps {
  children: React.ReactNode;
  initialPage?: string;
}

export function NavigationProvider({ 
  children, 
  initialPage = 'consent' 
}: NavigationProviderProps) {
  const [history, setHistory] = useState<string[]>([initialPage]);
  const [currentIndex, setCurrentIndex] = useState(0);

  const currentPage = history[currentIndex];
  const canGoBack = currentIndex > 0;
  const canGoForward = currentIndex < history.length - 1;

  const navigate = (page: string) => {
    const newHistory = history.slice(0, currentIndex + 1);
    newHistory.push(page);
    setHistory(newHistory);
    setCurrentIndex(newHistory.length - 1);
  };

  const goBack = () => {
    if (canGoBack) {
      setCurrentIndex(currentIndex - 1);
    }
  };

  const goForward = () => {
    if (canGoForward) {
      setCurrentIndex(currentIndex + 1);
    }
  };

  const value: NavigationContextType = {
    currentPage,
    canGoBack,
    canGoForward,
    navigate,
    goBack,
    goForward,
  };

  return (
    <NavigationContext.Provider value={value}>
      {children}
    </NavigationContext.Provider>
  );
}

export function useNavigation() {
  const context = React.useContext(NavigationContext);
  if (!context) {
    throw new Error('useNavigation must be used within NavigationProvider');
  }
  return context;
}

// Quick Action Buttons
interface QuickActionsProps {
  actions: NavigationAction[];
  layout?: 'horizontal' | 'vertical' | 'grid';
  className?: string;
}

export function QuickActions({
  actions,
  layout = 'horizontal',
  className = ''
}: QuickActionsProps) {
  const theme = useInterviewTheme();

  const containerClasses = cn(
    'quick-actions',
    {
      'flex space-x-2': layout === 'horizontal',
      'flex flex-col space-y-2': layout === 'vertical',
      'grid grid-cols-2 gap-2': layout === 'grid',
    },
    className
  );

  return (
    <div className={containerClasses}>
      {actions.map(action => (
        <button
          key={action.id}
          onClick={action.action}
          disabled={action.disabled}
          className={cn(
            "quick-action flex items-center justify-center space-x-2 px-4 py-3 rounded-lg font-medium transition-all duration-200 hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-opacity-50",
            {
              'opacity-50 cursor-not-allowed': action.disabled,
            }
          )}
          style={{
            backgroundColor: theme.colors.surface,
            color: theme.colors.text.primary,
            border: `1px solid ${theme.colors.text.muted}30`,
          }}
        >
          <span className="text-lg">{action.icon}</span>
          <span>{action.label}</span>
        </button>
      ))}
    </div>
  );
}

// Breadcrumb Navigation
interface BreadcrumbItem {
  id: string;
  label: string;
  href?: string;
  onClick?: () => void;
}

interface BreadcrumbProps {
  items: BreadcrumbItem[];
  separator?: string;
  className?: string;
}

export function Breadcrumb({
  items,
  separator = '/',
  className = ''
}: BreadcrumbProps) {
  const theme = useInterviewTheme();

  return (
    <nav 
      className={cn('breadcrumb flex items-center space-x-2', className)}
      aria-label="Breadcrumb"
    >
      {items.map((item, index) => (
        <React.Fragment key={item.id}>
          {index > 0 && (
            <span 
              className="breadcrumb-separator"
              style={{ color: theme.colors.text.muted }}
            >
              {separator}
            </span>
          )}
          
          {item.onClick ? (
            <button
              onClick={item.onClick}
              className={cn(
                "breadcrumb-item text-sm transition-colors duration-200 hover:opacity-80",
                {
                  'font-medium': index === items.length - 1,
                }
              )}
              style={{
                color: index === items.length - 1 
                  ? theme.colors.text.primary 
                  : theme.colors.primary,
              }}
            >
              {item.label}
            </button>
          ) : (
            <span 
              className={cn(
                "breadcrumb-item text-sm",
                {
                  'font-medium': index === items.length - 1,
                }
              )}
              style={{
                color: index === items.length - 1 
                  ? theme.colors.text.primary 
                  : theme.colors.text.muted,
              }}
            >
              {item.label}
            </span>
          )}
        </React.Fragment>
      ))}
    </nav>
  );
}

// Step Navigation
interface StepNavigationProps {
  currentStep: number;
  totalSteps: number;
  onPrevious?: () => void;
  onNext?: () => void;
  onSkip?: () => void;
  previousLabel?: string;
  nextLabel?: string;
  skipLabel?: string;
  showSkip?: boolean;
  className?: string;
}

export function StepNavigation({
  currentStep,
  totalSteps,
  onPrevious,
  onNext,
  onSkip,
  previousLabel = 'Önceki',
  nextLabel = 'Sonraki',
  skipLabel = 'Atla',
  showSkip = false,
  className = ''
}: StepNavigationProps) {
  const theme = useInterviewTheme();

  const canGoPrevious = currentStep > 1;
  const canGoNext = currentStep < totalSteps;
  const isLastStep = currentStep === totalSteps;

  return (
    <div 
      className={cn('step-navigation flex items-center justify-between', className)}
    >
      {/* Previous Button */}
      <div className="nav-previous">
        {canGoPrevious ? (
          <button
            onClick={onPrevious}
            className="flex items-center space-x-2 px-4 py-2 rounded-md transition-all duration-200 hover:opacity-80"
            style={{
              backgroundColor: theme.colors.surface,
              color: theme.colors.text.primary,
              border: `1px solid ${theme.colors.text.muted}30`,
            }}
          >
            <span>←</span>
            <span>{previousLabel}</span>
          </button>
        ) : (
          <div /> // Placeholder for alignment
        )}
      </div>

      {/* Step Indicator */}
      <div className="step-indicator flex items-center space-x-2">
        <span 
          className="text-sm"
          style={{ color: theme.colors.text.muted }}
        >
          {currentStep} / {totalSteps}
        </span>
      </div>

      {/* Next/Skip Buttons */}
      <div className="nav-next flex items-center space-x-2">
        {showSkip && onSkip && !isLastStep && (
          <button
            onClick={onSkip}
            className="px-4 py-2 rounded-md transition-all duration-200 hover:opacity-80"
            style={{
              backgroundColor: 'transparent',
              color: theme.colors.text.muted,
              border: 'none',
            }}
          >
            {skipLabel}
          </button>
        )}

        {canGoNext && onNext && (
          <button
            onClick={onNext}
            className="flex items-center space-x-2 px-4 py-2 rounded-md transition-all duration-200 hover:opacity-90"
            style={{
              backgroundColor: theme.colors.primary,
              color: 'white',
              border: 'none',
            }}
          >
            <span>{isLastStep ? 'Tamamla' : nextLabel}</span>
            <span>→</span>
          </button>
        )}
      </div>
    </div>
  );
}
