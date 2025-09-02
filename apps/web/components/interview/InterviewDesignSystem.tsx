"use client";

// Professional Interview Design System
export interface InterviewTheme {
  colors: {
    primary: string;
    secondary: string;
    accent: string;
    background: string;
    surface: string;
    text: {
      primary: string;
      secondary: string;
      muted: string;
    };
    status: {
      success: string;
      warning: string;
      error: string;
      info: string;
    };
    interview: {
      speaking: string;
      listening: string;
      thinking: string;
      idle: string;
      recording: string;
    };
  };
  spacing: {
    xs: string;
    sm: string;
    md: string;
    lg: string;
    xl: string;
    '2xl': string;
  };
  typography: {
    fontFamily: string;
    fontSize: {
      xs: string;
      sm: string;
      md: string;
      lg: string;
      xl: string;
      '2xl': string;
      '3xl': string;
    };
    fontWeight: {
      normal: string;
      medium: string;
      semibold: string;
      bold: string;
    };
  };
  borderRadius: {
    sm: string;
    md: string;
    lg: string;
    xl: string;
    full: string;
  };
  shadows: {
    sm: string;
    md: string;
    lg: string;
    xl: string;
  };
}

// Professional Interview Theme
export const professionalInterviewTheme: InterviewTheme = {
  colors: {
    primary: '#1e40af', // Blue 700
    secondary: '#3b82f6', // Blue 500
    accent: '#8b5cf6', // Purple 500
    background: '#ffffff',
    surface: '#f8fafc',
    text: {
      primary: '#0f172a',
      secondary: '#475569',
      muted: '#64748b',
    },
    status: {
      success: '#10b981',
      warning: '#f59e0b',
      error: '#ef4444',
      info: '#3b82f6',
    },
    interview: {
      speaking: '#3b82f6', // Blue when AI is speaking
      listening: '#10b981', // Green when listening to candidate
      thinking: '#f59e0b', // Orange when processing
      idle: '#64748b', // Gray when idle
      recording: '#ef4444', // Red for recording indicator
    },
  },
  spacing: {
    xs: '0.25rem',
    sm: '0.5rem',
    md: '1rem',
    lg: '1.5rem',
    xl: '2rem',
    '2xl': '3rem',
  },
  typography: {
    fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, sans-serif',
    fontSize: {
      xs: '0.75rem',
      sm: '0.875rem',
      md: '1rem',
      lg: '1.125rem',
      xl: '1.25rem',
      '2xl': '1.5rem',
      '3xl': '1.875rem',
    },
    fontWeight: {
      normal: '400',
      medium: '500',
      semibold: '600',
      bold: '700',
    },
  },
  borderRadius: {
    sm: '0.25rem',
    md: '0.375rem',
    lg: '0.5rem',
    xl: '0.75rem',
    full: '9999px',
  },
  shadows: {
    sm: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
    md: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
    lg: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
    xl: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
  },
};

// Interview Design System Provider
import React, { createContext, useContext } from 'react';

const InterviewThemeContext = createContext<InterviewTheme>(professionalInterviewTheme);

interface InterviewThemeProviderProps {
  theme?: InterviewTheme;
  children: React.ReactNode;
}

export function InterviewThemeProvider({ 
  theme = professionalInterviewTheme, 
  children 
}: InterviewThemeProviderProps) {
  return (
    <InterviewThemeContext.Provider value={theme}>
      <div 
        className="interview-theme-root"
        style={{
          '--interview-primary': theme.colors.primary,
          '--interview-secondary': theme.colors.secondary,
          '--interview-accent': theme.colors.accent,
          '--interview-background': theme.colors.background,
          '--interview-surface': theme.colors.surface,
          '--interview-text-primary': theme.colors.text.primary,
          '--interview-text-secondary': theme.colors.text.secondary,
          '--interview-text-muted': theme.colors.text.muted,
          '--interview-success': theme.colors.status.success,
          '--interview-warning': theme.colors.status.warning,
          '--interview-error': theme.colors.status.error,
          '--interview-info': theme.colors.status.info,
          '--interview-speaking': theme.colors.interview.speaking,
          '--interview-listening': theme.colors.interview.listening,
          '--interview-thinking': theme.colors.interview.thinking,
          '--interview-idle': theme.colors.interview.idle,
          '--interview-recording': theme.colors.interview.recording,
        } as React.CSSProperties}
      >
        {children}
      </div>
    </InterviewThemeContext.Provider>
  );
}

export function useInterviewTheme() {
  const context = useContext(InterviewThemeContext);
  if (!context) {
    throw new Error('useInterviewTheme must be used within InterviewThemeProvider');
  }
  return context;
}

// CSS-in-JS utility for theme-aware styling
export function themeStyles(theme: InterviewTheme) {
  return {
    // Button styles
    button: {
      primary: {
        backgroundColor: theme.colors.primary,
        color: 'white',
        border: 'none',
        borderRadius: theme.borderRadius.md,
        padding: `${theme.spacing.sm} ${theme.spacing.lg}`,
        fontSize: theme.typography.fontSize.md,
        fontWeight: theme.typography.fontWeight.medium,
        boxShadow: theme.shadows.sm,
        cursor: 'pointer',
        transition: 'all 0.2s ease',
      },
      secondary: {
        backgroundColor: theme.colors.surface,
        color: theme.colors.text.primary,
        border: `1px solid ${theme.colors.text.muted}`,
        borderRadius: theme.borderRadius.md,
        padding: `${theme.spacing.sm} ${theme.spacing.lg}`,
        fontSize: theme.typography.fontSize.md,
        fontWeight: theme.typography.fontWeight.medium,
        cursor: 'pointer',
        transition: 'all 0.2s ease',
      },
    },
    // Card styles
    card: {
      default: {
        backgroundColor: theme.colors.surface,
        border: `1px solid ${theme.colors.text.muted}20`,
        borderRadius: theme.borderRadius.lg,
        padding: theme.spacing.lg,
        boxShadow: theme.shadows.md,
      },
      elevated: {
        backgroundColor: theme.colors.background,
        border: 'none',
        borderRadius: theme.borderRadius.lg,
        padding: theme.spacing.xl,
        boxShadow: theme.shadows.lg,
      },
    },
    // Status indicators
    status: {
      speaking: {
        color: theme.colors.interview.speaking,
        backgroundColor: `${theme.colors.interview.speaking}10`,
        border: `1px solid ${theme.colors.interview.speaking}30`,
      },
      listening: {
        color: theme.colors.interview.listening,
        backgroundColor: `${theme.colors.interview.listening}10`,
        border: `1px solid ${theme.colors.interview.listening}30`,
      },
      thinking: {
        color: theme.colors.interview.thinking,
        backgroundColor: `${theme.colors.interview.thinking}10`,
        border: `1px solid ${theme.colors.interview.thinking}30`,
      },
      idle: {
        color: theme.colors.interview.idle,
        backgroundColor: `${theme.colors.interview.idle}10`,
        border: `1px solid ${theme.colors.interview.idle}30`,
      },
    },
  };
}

// Pre-built interview-specific components
interface InterviewCardProps {
  children: React.ReactNode;
  variant?: 'default' | 'elevated';
  className?: string;
}

export function InterviewCard({ 
  children, 
  variant = 'default', 
  className = '' 
}: InterviewCardProps) {
  const theme = useInterviewTheme();
  const styles = themeStyles(theme);
  
  return (
    <div 
      style={styles.card[variant]}
      className={`interview-card ${className}`}
    >
      {children}
    </div>
  );
}

interface InterviewButtonProps {
  children: React.ReactNode;
  variant?: 'primary' | 'secondary';
  onClick?: () => void;
  disabled?: boolean;
  className?: string;
}

export function InterviewButton({ 
  children, 
  variant = 'primary', 
  onClick, 
  disabled = false,
  className = '' 
}: InterviewButtonProps) {
  const theme = useInterviewTheme();
  const styles = themeStyles(theme);
  
  return (
    <button
      style={{
        ...styles.button[variant],
        opacity: disabled ? 0.5 : 1,
        cursor: disabled ? 'not-allowed' : 'pointer',
      }}
      onClick={onClick}
      disabled={disabled}
      className={`interview-button ${className}`}
    >
      {children}
    </button>
  );
}

interface InterviewStatusProps {
  status: 'speaking' | 'listening' | 'thinking' | 'idle';
  children: React.ReactNode;
  className?: string;
}

export function InterviewStatus({ 
  status, 
  children, 
  className = '' 
}: InterviewStatusProps) {
  const theme = useInterviewTheme();
  const styles = themeStyles(theme);
  
  return (
    <div
      style={{
        ...styles.status[status],
        padding: `${theme.spacing.sm} ${theme.spacing.md}`,
        borderRadius: theme.borderRadius.md,
        display: 'inline-flex',
        alignItems: 'center',
        gap: theme.spacing.sm,
        fontSize: theme.typography.fontSize.sm,
        fontWeight: theme.typography.fontWeight.medium,
      }}
      className={`interview-status interview-status-${status} ${className}`}
    >
      {children}
    </div>
  );
}
