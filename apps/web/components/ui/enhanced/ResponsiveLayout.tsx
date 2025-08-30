'use client';

import React, { useState, useEffect } from 'react';
import { cn } from '@/components/ui/utils/cn';

// Hook to detect screen size
export function useResponsive() {
  const [screenSize, setScreenSize] = useState({
    isMobile: false,
    isTablet: false,
    isDesktop: false,
    width: 0,
    height: 0,
  });

  useEffect(() => {
    const checkScreenSize = () => {
      const width = window.innerWidth;
      const height = window.innerHeight;
      
      setScreenSize({
        isMobile: width < 768,
        isTablet: width >= 768 && width < 1024,
        isDesktop: width >= 1024,
        width,
        height,
      });
    };

    checkScreenSize();
    window.addEventListener('resize', checkScreenSize);
    
    return () => window.removeEventListener('resize', checkScreenSize);
  }, []);

  return screenSize;
}

// Responsive Grid Component
interface ResponsiveGridProps {
  children: React.ReactNode;
  cols?: {
    mobile: number;
    tablet: number;
    desktop: number;
  };
  gap?: 'sm' | 'md' | 'lg';
  className?: string;
}

export function ResponsiveGrid({
  children,
  cols = { mobile: 1, tablet: 2, desktop: 3 },
  gap = 'md',
  className,
}: ResponsiveGridProps) {
  const gapClasses = {
    sm: 'gap-2',
    md: 'gap-4',
    lg: 'gap-6',
  };

  const gridCols = {
    1: 'grid-cols-1',
    2: 'grid-cols-2',
    3: 'grid-cols-3',
    4: 'grid-cols-4',
    5: 'grid-cols-5',
    6: 'grid-cols-6',
  };

  return (
    <div
      className={cn(
        'grid',
        gapClasses[gap],
        gridCols[cols.mobile as keyof typeof gridCols],
        `md:${gridCols[cols.tablet as keyof typeof gridCols]}`,
        `lg:${gridCols[cols.desktop as keyof typeof gridCols]}`,
        className
      )}
    >
      {children}
    </div>
  );
}

// Mobile-First Dashboard Layout
interface MobileDashboardProps {
  children: React.ReactNode;
  sidebar?: React.ReactNode;
  header?: React.ReactNode;
  className?: string;
}

export function MobileDashboard({
  children,
  sidebar,
  header,
  className,
}: MobileDashboardProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { isMobile } = useResponsive();

  return (
    <div className={cn('min-h-screen bg-gray-50 dark:bg-gray-900', className)}>
      {/* Mobile Header */}
      {header && (
        <div className="sticky top-0 z-40 lg:hidden">
          <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-4 py-3">
            <div className="flex items-center justify-between">
              {header}
              {sidebar && (
                <button
                  onClick={() => setSidebarOpen(!sidebarOpen)}
                  className="lg:hidden p-2 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                  </svg>
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      <div className="flex">
        {/* Sidebar */}
        {sidebar && (
          <>
            {/* Mobile Sidebar Overlay */}
            {sidebarOpen && isMobile && (
              <div
                className="fixed inset-0 z-40 bg-gray-600 bg-opacity-75 lg:hidden"
                onClick={() => setSidebarOpen(false)}
              />
            )}

            {/* Sidebar */}
            <div
              className={cn(
                'fixed inset-y-0 left-0 z-50 w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 transform transition-transform duration-300 ease-in-out lg:translate-x-0 lg:static lg:inset-0',
                sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
              )}
            >
              <div className="h-full overflow-y-auto">
                {sidebar}
              </div>
            </div>
          </>
        )}

        {/* Main Content */}
        <div className="flex-1 min-w-0">
          <main className="p-4 lg:p-6">
            {children}
          </main>
        </div>
      </div>
    </div>
  );
}

// Responsive Cards Stack
interface ResponsiveStackProps {
  children: React.ReactNode;
  spacing?: 'sm' | 'md' | 'lg';
  mobileColumns?: 1 | 2;
  className?: string;
}

export function ResponsiveStack({
  children,
  spacing = 'md',
  mobileColumns = 1,
  className,
}: ResponsiveStackProps) {
  const spacingClasses = {
    sm: 'space-y-2 md:space-y-3',
    md: 'space-y-4 md:space-y-6',
    lg: 'space-y-6 md:space-y-8',
  };

  const mobileGridClasses = {
    1: 'grid-cols-1',
    2: 'grid-cols-2',
  };

  return (
    <div
      className={cn(
        'grid gap-4',
        mobileGridClasses[mobileColumns],
        'md:grid-cols-1 md:space-y-0',
        spacingClasses[spacing],
        className
      )}
    >
      {children}
    </div>
  );
}

// Mobile-Optimized Chart Container
interface MobileChartContainerProps {
  children: React.ReactNode;
  title?: string;
  subtitle?: string;
  height?: 'sm' | 'md' | 'lg' | 'xl';
  scrollable?: boolean;
  className?: string;
}

export function MobileChartContainer({
  children,
  title,
  subtitle,
  height = 'md',
  scrollable = false,
  className,
}: MobileChartContainerProps) {
  const heightClasses = {
    sm: 'h-48 md:h-56',
    md: 'h-64 md:h-80',
    lg: 'h-80 md:h-96',
    xl: 'h-96 md:h-[500px]',
  };

  return (
    <div className={cn('bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4', className)}>
      {(title || subtitle) && (
        <div className="mb-4">
          {title && (
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              {title}
            </h3>
          )}
          {subtitle && (
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              {subtitle}
            </p>
          )}
        </div>
      )}
      
      <div
        className={cn(
          heightClasses[height],
          scrollable && 'overflow-x-auto'
        )}
      >
        {children}
      </div>
    </div>
  );
}

// Mobile-First Table Container
interface MobileTableProps {
  children: React.ReactNode;
  headers?: string[];
  mobileCardView?: boolean;
  className?: string;
}

export function MobileTable({
  children,
  headers,
  mobileCardView = true,
  className,
}: MobileTableProps) {
  const { isMobile } = useResponsive();

  if (isMobile && mobileCardView) {
    return (
      <div className={cn('space-y-3', className)}>
        {children}
      </div>
    );
  }

  return (
    <div className={cn('overflow-x-auto', className)}>
      <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
        {headers && (
          <thead className="bg-gray-50 dark:bg-gray-800">
            <tr>
              {headers.map((header, index) => (
                <th
                  key={index}
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"
                >
                  {header}
                </th>
              ))}
            </tr>
          </thead>
        )}
        <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
          {children}
        </tbody>
      </table>
    </div>
  );
}

// Touch-Friendly Action Bar
interface MobileActionBarProps {
  actions: Array<{
    label: string;
    icon?: React.ReactNode;
    onClick: () => void;
    variant?: 'primary' | 'secondary' | 'danger';
    disabled?: boolean;
  }>;
  position?: 'top' | 'bottom' | 'floating';
  className?: string;
}

export function MobileActionBar({
  actions,
  position = 'bottom',
  className,
}: MobileActionBarProps) {
  const positionClasses = {
    top: 'top-0 border-b',
    bottom: 'bottom-0 border-t',
    floating: 'bottom-4 left-4 right-4 rounded-lg shadow-lg border',
  };

  const variantClasses = {
    primary: 'bg-blue-600 text-white hover:bg-blue-700',
    secondary: 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600',
    danger: 'bg-red-600 text-white hover:bg-red-700',
  };

  return (
    <div
      className={cn(
        'fixed left-0 right-0 z-30 bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 p-4',
        positionClasses[position],
        className
      )}
    >
      <div className="flex items-center justify-center space-x-2 overflow-x-auto">
        {actions.map((action, index) => (
          <button
            key={index}
            onClick={action.onClick}
            disabled={action.disabled}
            className={cn(
              'flex items-center space-x-2 px-4 py-2 rounded-lg font-medium transition-colors min-w-0 flex-shrink-0',
              action.disabled && 'opacity-50 cursor-not-allowed',
              variantClasses[action.variant || 'secondary']
            )}
          >
            {action.icon && <span className="flex-shrink-0">{action.icon}</span>}
            <span className="truncate">{action.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

// Mobile Pull-to-Refresh
interface PullToRefreshProps {
  children: React.ReactNode;
  onRefresh: () => Promise<void>;
  disabled?: boolean;
  className?: string;
}

export function PullToRefresh({
  children,
  onRefresh,
  disabled = false,
  className,
}: PullToRefreshProps) {
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [pullDistance, setPullDistance] = useState(0);
  const [startY, setStartY] = useState(0);

  const handleTouchStart = (e: React.TouchEvent) => {
    if (disabled || window.scrollY > 0) return;
    setStartY(e.touches[0].clientY);
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    if (disabled || isRefreshing || window.scrollY > 0) return;
    
    const currentY = e.touches[0].clientY;
    const distance = Math.max(0, (currentY - startY) * 0.5);
    setPullDistance(Math.min(distance, 100));
  };

  const handleTouchEnd = async () => {
    if (disabled || isRefreshing || pullDistance < 60) {
      setPullDistance(0);
      return;
    }

    setIsRefreshing(true);
    try {
      await onRefresh();
    } finally {
      setIsRefreshing(false);
      setPullDistance(0);
    }
  };

  return (
    <div
      className={cn('relative', className)}
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleTouchEnd}
    >
      {/* Pull indicator */}
      {(pullDistance > 0 || isRefreshing) && (
        <div
          className="absolute top-0 left-0 right-0 flex items-center justify-center bg-blue-50 dark:bg-blue-900/20 transition-all duration-200"
          style={{ height: Math.max(pullDistance, isRefreshing ? 60 : 0) }}
        >
          <div className="flex items-center space-x-2 text-blue-600 dark:text-blue-400">
            {isRefreshing ? (
              <>
                <svg className="animate-spin w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                <span className="text-sm">Yenileniyor...</span>
              </>
            ) : (
              <>
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                </svg>
                <span className="text-sm">
                  {pullDistance >= 60 ? 'Bırakın yenilemek için' : 'Yenilemek için çekin'}
                </span>
              </>
            )}
          </div>
        </div>
      )}
      
      <div
        style={{
          transform: `translateY(${pullDistance}px)`,
          transition: isRefreshing ? 'transform 0.2s' : 'none',
        }}
      >
        {children}
      </div>
    </div>
  );
}
