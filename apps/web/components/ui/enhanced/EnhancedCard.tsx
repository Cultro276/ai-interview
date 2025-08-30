'use client';

import React, { forwardRef } from 'react';
import { cn } from '@/components/ui/utils/cn';


export interface EnhancedCardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'outlined' | 'elevated' | 'gradient' | 'glass';
  padding?: 'none' | 'sm' | 'md' | 'lg' | 'xl';
  hover?: boolean;
  interactive?: boolean;
  loading?: boolean;
  header?: React.ReactNode;
  footer?: React.ReactNode;
  badge?: {
    text: string;
    variant: 'primary' | 'success' | 'warning' | 'error' | 'info';
  };
}

const EnhancedCard = forwardRef<HTMLDivElement, EnhancedCardProps>(
  ({
    className,
    variant = 'default',
    padding = 'md',
    hover = false,
    interactive = false,
    loading = false,
    header,
    footer,
    badge,
    children,
    ...props
  }, ref) => {


    const baseClasses = [
      'relative rounded-xl transition-all duration-300',
      interactive && 'cursor-pointer',
      hover && 'hover:shadow-lg hover:scale-[1.02]',
    ];

    const variantClasses = {
      default: [
        'bg-white border border-gray-200',
        'dark:bg-gray-800 dark:border-gray-700',
      ],
      outlined: [
        'bg-transparent border-2 border-gray-300',
        'dark:border-gray-600',
      ],
      elevated: [
        'bg-white shadow-lg border-0',
        'dark:bg-gray-800 dark:shadow-gray-900/50',
      ],
      gradient: [
        'bg-gradient-to-br from-white to-gray-50 border border-gray-200',
        'dark:from-gray-800 dark:to-gray-900 dark:border-gray-700',
      ],
      glass: [
        'bg-white/80 backdrop-blur-md border border-white/20',
        'dark:bg-gray-800/80 dark:border-gray-700/20',
      ],
    };

    const paddingClasses = {
      none: '',
      sm: 'p-3',
      md: 'p-6',
      lg: 'p-8',
      xl: 'p-10',
    };

    const badgeVariants = {
      primary: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
      success: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
      warning: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
      error: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
      info: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
    };

    // Loading skeleton
    const LoadingSkeleton = () => (
      <div className="animate-pulse">
        <div className="h-4 bg-gray-200 rounded mb-4 dark:bg-gray-700"></div>
        <div className="h-4 bg-gray-200 rounded mb-2 dark:bg-gray-700"></div>
        <div className="h-4 bg-gray-200 rounded w-3/4 dark:bg-gray-700"></div>
      </div>
    );

    return (
      <div
        ref={ref}
        className={cn(
          ...baseClasses,
          ...variantClasses[variant],
          paddingClasses[padding],
          className
        )}
        {...props}
      >
        {/* Badge */}
        {badge && (
          <div className="absolute -top-2 -right-2 z-10">
            <span className={cn(
              'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
              badgeVariants[badge.variant]
            )}>
              {badge.text}
            </span>
          </div>
        )}

        {/* Header */}
        {header && (
          <div className="mb-4 pb-4 border-b border-gray-200 dark:border-gray-700">
            {header}
          </div>
        )}

        {/* Content */}
        <div className="flex-1">
          {loading ? <LoadingSkeleton /> : children}
        </div>

        {/* Footer */}
        {footer && (
          <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
            {footer}
          </div>
        )}

        {/* Gradient overlay for hover effect */}
        {interactive && (
          <div className="absolute inset-0 bg-gradient-to-r from-blue-500/0 to-purple-500/0 hover:from-blue-500/5 hover:to-purple-500/5 rounded-xl transition-all duration-300 pointer-events-none" />
        )}
      </div>
    );
  }
);

EnhancedCard.displayName = 'EnhancedCard';

// Sub-components for better composition
export const EnhancedCardHeader = forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn('flex flex-col space-y-1.5', className)}
      {...props}
    />
  )
);

export const EnhancedCardTitle = forwardRef<HTMLParagraphElement, React.HTMLAttributes<HTMLHeadingElement>>(
  ({ className, ...props }, ref) => (
    <h3
      ref={ref}
      className={cn('text-lg font-semibold leading-none tracking-tight', className)}
      {...props}
    />
  )
);

export const EnhancedCardDescription = forwardRef<HTMLParagraphElement, React.HTMLAttributes<HTMLParagraphElement>>(
  ({ className, ...props }, ref) => (
    <p
      ref={ref}
      className={cn('text-sm text-gray-600 dark:text-gray-400', className)}
      {...props}
    />
  )
);

export const EnhancedCardContent = forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn('space-y-4', className)}
      {...props}
    />
  )
);

export const EnhancedCardFooter = forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn('flex items-center space-x-2', className)}
      {...props}
    />
  )
);

EnhancedCardHeader.displayName = 'EnhancedCardHeader';
EnhancedCardTitle.displayName = 'EnhancedCardTitle';
EnhancedCardDescription.displayName = 'EnhancedCardDescription';
EnhancedCardContent.displayName = 'EnhancedCardContent';
EnhancedCardFooter.displayName = 'EnhancedCardFooter';

export { EnhancedCard };
