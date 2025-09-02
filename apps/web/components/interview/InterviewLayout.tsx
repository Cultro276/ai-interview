"use client";

import React from 'react';
import { useInterviewTheme } from './InterviewDesignSystem';
import { cn } from '@/components/ui/utils';

// Professional Interview Layout
interface InterviewLayoutProps {
  children: React.ReactNode;
  header?: React.ReactNode;
  sidebar?: React.ReactNode;
  footer?: React.ReactNode;
  className?: string;
  variant?: 'default' | 'centered' | 'fullscreen';
  showBorder?: boolean;
}

export function InterviewLayout({ 
  children, 
  header, 
  sidebar, 
  footer,
  className = '',
  variant = 'default',
  showBorder = true
}: InterviewLayoutProps) {
  const theme = useInterviewTheme();

  const layoutClasses = cn(
    'interview-layout min-h-screen flex flex-col',
    {
      'max-w-7xl mx-auto': variant === 'centered',
      'h-screen overflow-hidden': variant === 'fullscreen',
      'border-x border-gray-200': showBorder && variant === 'centered',
    },
    className
  );

  const contentClasses = cn(
    'interview-main flex-1 flex',
    {
      'flex-col': !sidebar,
      'flex-row': sidebar,
    }
  );

  return (
    <div 
      className={layoutClasses}
      style={{
        backgroundColor: theme.colors.background,
        color: theme.colors.text.primary,
        fontFamily: theme.typography.fontFamily,
      }}
    >
      {header && (
        <header 
          className="interview-header flex-shrink-0 border-b border-gray-200"
          style={{
            backgroundColor: theme.colors.surface,
            borderColor: `${theme.colors.text.muted}20`,
          }}
        >
          {header}
        </header>
      )}
      
      <main className={contentClasses}>
        {sidebar && (
          <aside 
            className="interview-sidebar w-64 flex-shrink-0 border-r border-gray-200"
            style={{
              backgroundColor: theme.colors.surface,
              borderColor: `${theme.colors.text.muted}20`,
            }}
          >
            {sidebar}
          </aside>
        )}
        
        <div className="interview-content flex-1 flex flex-col">
          {children}
        </div>
      </main>
      
      {footer && (
        <footer 
          className="interview-footer flex-shrink-0 border-t border-gray-200"
          style={{
            backgroundColor: theme.colors.surface,
            borderColor: `${theme.colors.text.muted}20`,
          }}
        >
          {footer}
        </footer>
      )}
    </div>
  );
}

// Interview Header Component
interface InterviewHeaderProps {
  title?: string;
  subtitle?: string;
  actions?: React.ReactNode;
  showLogo?: boolean;
  className?: string;
}

export function InterviewHeader({
  title,
  subtitle,
  actions,
  showLogo = true,
  className = ''
}: InterviewHeaderProps) {
  const theme = useInterviewTheme();

  return (
    <div 
      className={cn('interview-header-content px-6 py-4 flex items-center justify-between', className)}
    >
      <div className="header-left flex items-center space-x-4">
        {showLogo && (
          <div className="header-logo">
            <div 
              className="w-8 h-8 rounded-lg flex items-center justify-center text-white text-sm font-bold"
              style={{ backgroundColor: theme.colors.primary }}
            >
              AI
            </div>
          </div>
        )}
        
        <div className="header-text">
          {title && (
            <h1 
              className="text-lg font-semibold"
              style={{ 
                color: theme.colors.text.primary,
                fontSize: theme.typography.fontSize.lg,
                fontWeight: theme.typography.fontWeight.semibold,
              }}
            >
              {title}
            </h1>
          )}
          {subtitle && (
            <p 
              className="text-sm"
              style={{ 
                color: theme.colors.text.secondary,
                fontSize: theme.typography.fontSize.sm,
              }}
            >
              {subtitle}
            </p>
          )}
        </div>
      </div>
      
      {actions && (
        <div className="header-actions flex items-center space-x-2">
          {actions}
        </div>
      )}
    </div>
  );
}

// Interview Sidebar Component
interface InterviewSidebarProps {
  children: React.ReactNode;
  title?: string;
  className?: string;
  collapsible?: boolean;
  defaultCollapsed?: boolean;
}

export function InterviewSidebar({
  children,
  title,
  className = '',
  collapsible = false,
  defaultCollapsed = false
}: InterviewSidebarProps) {
  const theme = useInterviewTheme();
  const [collapsed, setCollapsed] = React.useState(defaultCollapsed);

  return (
    <div 
      className={cn(
        'interview-sidebar-content h-full flex flex-col',
        {
          'w-16': collapsed,
          'w-64': !collapsed,
        },
        className
      )}
    >
      {(title || collapsible) && (
        <div 
          className="sidebar-header px-4 py-3 border-b border-gray-200 flex items-center justify-between"
          style={{
            borderColor: `${theme.colors.text.muted}20`,
          }}
        >
          {title && !collapsed && (
            <h2 
              className="text-sm font-medium"
              style={{ 
                color: theme.colors.text.primary,
                fontSize: theme.typography.fontSize.sm,
                fontWeight: theme.typography.fontWeight.medium,
              }}
            >
              {title}
            </h2>
          )}
          
          {collapsible && (
            <button
              onClick={() => setCollapsed(!collapsed)}
              className="p-1 rounded hover:bg-gray-100 transition-colors"
              style={{ color: theme.colors.text.muted }}
            >
              {collapsed ? '→' : '←'}
            </button>
          )}
        </div>
      )}
      
      <div className="sidebar-content flex-1 overflow-auto">
        {!collapsed && children}
      </div>
    </div>
  );
}

// Interview Footer Component
interface InterviewFooterProps {
  children?: React.ReactNode;
  showPoweredBy?: boolean;
  className?: string;
}

export function InterviewFooter({
  children,
  showPoweredBy = true,
  className = ''
}: InterviewFooterProps) {
  const theme = useInterviewTheme();

  return (
    <div 
      className={cn('interview-footer-content px-6 py-3 flex items-center justify-between', className)}
    >
      <div className="footer-content">
        {children}
      </div>
      
      {showPoweredBy && (
        <div className="footer-branding">
          <p 
            className="text-xs"
            style={{ 
              color: theme.colors.text.muted,
              fontSize: theme.typography.fontSize.xs,
            }}
          >
            Powered by RecruiterAI
          </p>
        </div>
      )}
    </div>
  );
}

// Interview Content Area Component
interface InterviewContentAreaProps {
  children: React.ReactNode;
  padding?: 'none' | 'sm' | 'md' | 'lg';
  centerContent?: boolean;
  maxWidth?: 'sm' | 'md' | 'lg' | 'xl' | 'full';
  className?: string;
}

export function InterviewContentArea({
  children,
  padding = 'md',
  centerContent = false,
  maxWidth = 'full',
  className = ''
}: InterviewContentAreaProps) {
  const theme = useInterviewTheme();

  const paddingClasses = {
    none: '',
    sm: 'p-4',
    md: 'p-6',
    lg: 'p-8',
  };

  const maxWidthClasses = {
    sm: 'max-w-sm',
    md: 'max-w-md',
    lg: 'max-w-lg',
    xl: 'max-w-xl',
    full: 'max-w-full',
  };

  return (
    <div 
      className={cn(
        'interview-content-area',
        paddingClasses[padding],
        {
          'flex items-center justify-center': centerContent,
          'mx-auto': maxWidth !== 'full',
        },
        maxWidthClasses[maxWidth],
        className
      )}
    >
      {children}
    </div>
  );
}

// Interview Grid Layout Component
interface InterviewGridProps {
  children: React.ReactNode;
  columns?: 1 | 2 | 3 | 4;
  gap?: 'sm' | 'md' | 'lg';
  className?: string;
}

export function InterviewGrid({
  children,
  columns = 2,
  gap = 'md',
  className = ''
}: InterviewGridProps) {
  const gridClasses = cn(
    'interview-grid grid',
    {
      'grid-cols-1': columns === 1,
      'grid-cols-2': columns === 2,
      'grid-cols-3': columns === 3,
      'grid-cols-4': columns === 4,
      'gap-2': gap === 'sm',
      'gap-4': gap === 'md',
      'gap-6': gap === 'lg',
    },
    className
  );

  return (
    <div className={gridClasses}>
      {children}
    </div>
  );
}

// Interview Section Component
interface InterviewSectionProps {
  title?: string;
  description?: string;
  children: React.ReactNode;
  className?: string;
  headerActions?: React.ReactNode;
}

export function InterviewSection({
  title,
  description,
  children,
  className = '',
  headerActions
}: InterviewSectionProps) {
  const theme = useInterviewTheme();

  return (
    <section className={cn('interview-section', className)}>
      {(title || description || headerActions) && (
        <div className="section-header mb-4 flex items-start justify-between">
          <div className="header-text">
            {title && (
              <h3 
                className="text-lg font-medium mb-1"
                style={{ 
                  color: theme.colors.text.primary,
                  fontSize: theme.typography.fontSize.lg,
                  fontWeight: theme.typography.fontWeight.medium,
                }}
              >
                {title}
              </h3>
            )}
            {description && (
              <p 
                className="text-sm"
                style={{ 
                  color: theme.colors.text.secondary,
                  fontSize: theme.typography.fontSize.sm,
                }}
              >
                {description}
              </p>
            )}
          </div>
          
          {headerActions && (
            <div className="header-actions">
              {headerActions}
            </div>
          )}
        </div>
      )}
      
      <div className="section-content">
        {children}
      </div>
    </section>
  );
}
