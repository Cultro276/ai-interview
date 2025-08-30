'use client';

import React, { forwardRef } from 'react';
import { cn } from '@/components/ui/utils/cn';


export interface EnhancedButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'success' | 'warning' | 'error' | 'ghost' | 'outline' | 'gradient';
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  loading?: boolean;
  icon?: React.ReactNode;
  iconPosition?: 'left' | 'right';
  fullWidth?: boolean;
  elevated?: boolean;
  animation?: 'none' | 'pulse' | 'bounce' | 'scale' | 'glow';
}

const EnhancedButton = forwardRef<HTMLButtonElement, EnhancedButtonProps>(
  ({
    className,
    variant = 'primary',
    size = 'md',
    loading = false,
    icon,
    iconPosition = 'left',
    fullWidth = false,
    elevated = false,
    animation = 'scale',
    children,
    disabled,
    ...props
  }, ref) => {


    const baseClasses = [
      'inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-all duration-300',
      'focus:outline-none focus:ring-2 focus:ring-offset-2',
      'disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none',
      fullWidth && 'w-full',
      elevated && 'shadow-lg hover:shadow-xl',
    ];

    const sizeClasses = {
      xs: 'px-2.5 py-1.5 text-xs',
      sm: 'px-3 py-2 text-sm',
      md: 'px-4 py-2.5 text-sm',
      lg: 'px-6 py-3 text-base',
      xl: 'px-8 py-4 text-lg',
    };

    const variantClasses = {
      primary: [
        'bg-gradient-to-r from-blue-600 to-blue-700 text-white',
        'hover:from-blue-700 hover:to-blue-800',
        'focus:ring-blue-500',
        'dark:from-blue-500 dark:to-blue-600 dark:hover:from-blue-600 dark:hover:to-blue-700',
      ],
      secondary: [
        'bg-gray-100 text-gray-900 border border-gray-300',
        'hover:bg-gray-200 hover:border-gray-400',
        'focus:ring-gray-500',
        'dark:bg-gray-800 dark:text-gray-100 dark:border-gray-600',
        'dark:hover:bg-gray-700 dark:hover:border-gray-500',
      ],
      success: [
        'bg-gradient-to-r from-green-600 to-emerald-600 text-white',
        'hover:from-green-700 hover:to-emerald-700',
        'focus:ring-green-500',
      ],
      warning: [
        'bg-gradient-to-r from-yellow-500 to-orange-500 text-white',
        'hover:from-yellow-600 hover:to-orange-600',
        'focus:ring-yellow-500',
      ],
      error: [
        'bg-gradient-to-r from-red-600 to-pink-600 text-white',
        'hover:from-red-700 hover:to-pink-700',
        'focus:ring-red-500',
      ],
      ghost: [
        'text-gray-700 hover:bg-gray-100',
        'focus:ring-gray-500',
        'dark:text-gray-300 dark:hover:bg-gray-800',
      ],
      outline: [
        'border-2 border-current text-blue-600 hover:bg-blue-50',
        'focus:ring-blue-500',
        'dark:text-blue-400 dark:hover:bg-blue-900/20',
      ],
      gradient: [
        'bg-gradient-to-r from-purple-600 via-pink-600 to-blue-600 text-white',
        'hover:from-purple-700 hover:via-pink-700 hover:to-blue-700',
        'focus:ring-purple-500',
        'bg-size-200 bg-pos-0 hover:bg-pos-100',
      ],
    };

    const animationClasses = {
      none: '',
      pulse: 'hover:animate-pulse',
      bounce: 'hover:animate-bounce',
      scale: 'hover:scale-105 active:scale-95',
      glow: 'hover:shadow-2xl hover:shadow-blue-500/25',
    };

    // Loading spinner
    const LoadingSpinner = () => (
      <svg
        className="animate-spin h-4 w-4"
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
      >
        <circle
          className="opacity-25"
          cx="12"
          cy="12"
          r="10"
          stroke="currentColor"
          strokeWidth="4"
        />
        <path
          className="opacity-75"
          fill="currentColor"
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
        />
      </svg>
    );

    const content = (
      <>
        {loading && <LoadingSpinner />}
        {!loading && icon && iconPosition === 'left' && (
          <span className="flex-shrink-0">{icon}</span>
        )}
        {children && <span className={loading ? 'opacity-0' : ''}>{children}</span>}
        {!loading && icon && iconPosition === 'right' && (
          <span className="flex-shrink-0">{icon}</span>
        )}
      </>
    );

    return (
      <button
        ref={ref}
        className={cn(
          ...baseClasses,
          sizeClasses[size],
          ...variantClasses[variant],
          animationClasses[animation],
          className
        )}
        disabled={disabled || loading}
        {...props}
      >
        {content}
      </button>
    );
  }
);

EnhancedButton.displayName = 'EnhancedButton';

export { EnhancedButton };
