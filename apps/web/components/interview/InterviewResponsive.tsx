"use client";

import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import Image from 'next/image';
import { useInterviewTheme } from './InterviewDesignSystem';
import { cn } from '@/components/ui/utils';

// Mobile-first responsive design
type MobileLayout = 'stacked' | 'overlay' | 'minimal' | 'compact';
type TabletLayout = 'side-by-side' | 'grid' | 'focus' | 'hybrid';
type DesktopLayout = 'full' | 'split' | 'dashboard' | 'theater';
type AllLayouts = MobileLayout | TabletLayout | DesktopLayout;

interface ResponsiveConfig {
  breakpoints: {
    mobile: number;
    tablet: number;
    desktop: number;
    wide: number;
  };
  layouts: {
    mobile: MobileLayout;
    tablet: TabletLayout;
    desktop: DesktopLayout;
  };
  adaptiveFeatures: {
    autoLayout: boolean;
    touchOptimized: boolean;
    compactUI: boolean;
    responsiveText: boolean;
  };
}

interface InterviewResponsiveProps {
  config: ResponsiveConfig;
  children: React.ReactNode;
  onLayoutChange?: (layout: string, breakpoint: string) => void;
  className?: string;
}

export function InterviewResponsive({
  config,
  children,
  onLayoutChange,
  className = ''
}: InterviewResponsiveProps) {
  const theme = useInterviewTheme();
  const [currentBreakpoint, setCurrentBreakpoint] = useState<string>('desktop');
  const [currentLayout, setCurrentLayout] = useState<string>('full');
  const [screenSize, setScreenSize] = useState({ width: 0, height: 0 });
  const [orientation, setOrientation] = useState<'portrait' | 'landscape'>('landscape');
  const lastSizeRef = useRef<{ width: number; height: number }>({ width: 0, height: 0 });
  const lastOrientationRef = useRef<'portrait' | 'landscape'>('landscape');

  // Detect screen size and breakpoint
  const updateScreenInfo = useCallback(() => {
    if (typeof window === 'undefined') return;

    const width = window.innerWidth;
    const height = window.innerHeight;
    
    if (lastSizeRef.current.width !== width || lastSizeRef.current.height !== height) {
      lastSizeRef.current = { width, height };
      setScreenSize({ width, height });
    }
    const newOrientation = height > width ? 'portrait' : 'landscape';
    if (lastOrientationRef.current !== newOrientation) {
      lastOrientationRef.current = newOrientation;
      setOrientation(newOrientation);
    }

    let newBreakpoint = 'desktop';
    let newLayout: AllLayouts = config.layouts.desktop;

    if (width < config.breakpoints.mobile) {
      newBreakpoint = 'mobile';
      newLayout = config.layouts.mobile;
    } else if (width < config.breakpoints.tablet) {
      newBreakpoint = 'tablet';
      newLayout = config.layouts.tablet;
    } else if (width >= config.breakpoints.wide) {
      newBreakpoint = 'wide';
      newLayout = config.layouts.desktop; // Use desktop layout for wide screens
    }

    if (newBreakpoint !== currentBreakpoint || newLayout !== currentLayout) {
      setCurrentBreakpoint(newBreakpoint);
      setCurrentLayout(newLayout);
      onLayoutChange?.(newLayout, newBreakpoint);
    }
  }, [config, onLayoutChange, currentBreakpoint, currentLayout]);

  useEffect(() => {
    updateScreenInfo();
    
    const handleResize = () => {
      updateScreenInfo();
    };

    const handleOrientationChange = () => {
      // Add a small delay to ensure dimensions are updated
      setTimeout(updateScreenInfo, 100);
    };

    window.addEventListener('resize', handleResize);
    window.addEventListener('orientationchange', handleOrientationChange);

    return () => {
      window.removeEventListener('resize', handleResize);
      window.removeEventListener('orientationchange', handleOrientationChange);
    };
  }, [updateScreenInfo]);

  const getResponsiveClasses = () => {
    const baseClasses = 'interview-responsive w-full min-h-screen';
    
    const breakpointClasses = {
      mobile: 'mobile-layout',
      tablet: 'tablet-layout',
      desktop: 'desktop-layout',
      wide: 'wide-layout',
    };

    const layoutClasses = {
      // Mobile layouts
      stacked: 'flex flex-col space-y-2',
      overlay: 'relative',
      minimal: 'flex flex-col space-y-1',
      compact: 'grid grid-cols-1 gap-2',
      
      // Tablet layouts
      'side-by-side': 'grid grid-cols-2 gap-4',
      grid: 'grid grid-cols-2 md:grid-cols-3 gap-4',
      focus: 'flex flex-col lg:flex-row gap-4',
      hybrid: 'flex flex-col xl:grid xl:grid-cols-3 gap-4',
      
      // Desktop layouts
      full: 'grid grid-cols-1 lg:grid-cols-4 gap-6',
      split: 'grid grid-cols-1 lg:grid-cols-2 gap-6',
      dashboard: 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6',
      theater: 'flex flex-col space-y-6',
    };

    const orientationClasses = {
      portrait: 'orientation-portrait',
      landscape: 'orientation-landscape',
    };

    const adaptiveClasses = [];
    
    if (config.adaptiveFeatures.touchOptimized && (currentBreakpoint === 'mobile' || currentBreakpoint === 'tablet')) {
      adaptiveClasses.push('touch-optimized');
    }
    
    if (config.adaptiveFeatures.compactUI && currentBreakpoint === 'mobile') {
      adaptiveClasses.push('compact-ui');
    }
    
    if (config.adaptiveFeatures.responsiveText) {
      adaptiveClasses.push('responsive-text');
    }

    return cn(
      baseClasses,
      breakpointClasses[currentBreakpoint as keyof typeof breakpointClasses],
      layoutClasses[currentLayout as keyof typeof layoutClasses],
      orientationClasses[orientation],
      ...adaptiveClasses,
      className
    );
  };

  const getContainerStyles = () => {
    const styles: React.CSSProperties = {
      backgroundColor: theme.colors.background,
      color: theme.colors.text.primary,
      fontFamily: theme.typography.fontFamily,
    };

    // Adaptive spacing based on screen size
    if (currentBreakpoint === 'mobile') {
      styles.padding = theme.spacing.sm;
    } else if (currentBreakpoint === 'tablet') {
      styles.padding = theme.spacing.md;
    } else {
      styles.padding = theme.spacing.lg;
    }

    // Adaptive font sizes
    if (config.adaptiveFeatures.responsiveText) {
      if (currentBreakpoint === 'mobile') {
        styles.fontSize = theme.typography.fontSize.sm;
      } else if (currentBreakpoint === 'tablet') {
        styles.fontSize = theme.typography.fontSize.md;
      } else {
        styles.fontSize = theme.typography.fontSize.md;
      }
    }

    return styles;
  };

  return (
    <div 
      className={getResponsiveClasses()}
      style={getContainerStyles()}
      data-breakpoint={currentBreakpoint}
      data-layout={currentLayout}
      data-orientation={orientation}
    >
      {/* Responsive Debug Info (only in development) */}
      {process.env.NODE_ENV === 'development' && (
        <ResponsiveDebugInfo
          breakpoint={currentBreakpoint}
          layout={currentLayout}
          screenSize={screenSize}
          orientation={orientation}
        />
      )}
      
      {children}
    </div>
  );
}

// Responsive Debug Info Component
interface ResponsiveDebugInfoProps {
  breakpoint: string;
  layout: string;
  screenSize: { width: number; height: number };
  orientation: string;
}

function ResponsiveDebugInfo({
  breakpoint,
  layout,
  screenSize,
  orientation
}: ResponsiveDebugInfoProps) {
  const [isVisible, setIsVisible] = useState(false);

  return (
    <div className="fixed bottom-2 left-2 z-50">
      <button
        onClick={() => setIsVisible(!isVisible)}
        className="bg-black bg-opacity-70 text-white text-xs px-2 py-1 rounded"
      >
        📱 Debug
      </button>
      
      {isVisible && (
        <div className="absolute bottom-8 left-0 bg-black bg-opacity-90 text-white text-xs p-3 rounded min-w-48">
          <div className="space-y-1">
            <div><strong>Breakpoint:</strong> {breakpoint}</div>
            <div><strong>Layout:</strong> {layout}</div>
            <div><strong>Screen:</strong> {screenSize.width}×{screenSize.height}</div>
            <div><strong>Orientation:</strong> {orientation}</div>
          </div>
        </div>
      )}
    </div>
  );
}

// Custom hook for responsive behavior
export function useResponsive(customBreakpoints?: Partial<ResponsiveConfig['breakpoints']>) {
  const [breakpoint, setBreakpoint] = useState<string>('desktop');
  const [screenSize, setScreenSize] = useState({ width: 0, height: 0 });
  const [isMobile, setIsMobile] = useState(false);
  const [isTablet, setIsTablet] = useState(false);
  const [isDesktop, setIsDesktop] = useState(true);
  const lastSizeRef = useRef<{ width: number; height: number }>({ width: 0, height: 0 });

  const defaultBreakpoints = useMemo(() => ({
    mobile: 768,
    tablet: 1024,
    desktop: 1280,
    wide: 1920,
  }), []);

  const breakpoints = useMemo(() => ({
    ...defaultBreakpoints,
    ...(customBreakpoints || {}),
  }), [defaultBreakpoints, customBreakpoints]);

  const updateBreakpoint = useCallback(() => {
    if (typeof window === 'undefined') return;

    const width = window.innerWidth;
    const height = window.innerHeight;
    
    if (lastSizeRef.current.width !== width || lastSizeRef.current.height !== height) {
      lastSizeRef.current = { width, height };
      setScreenSize({ width, height });
    }

    let newBreakpoint = 'desktop';
    
    if (width < breakpoints.mobile) {
      newBreakpoint = 'mobile';
    } else if (width < breakpoints.tablet) {
      newBreakpoint = 'tablet';
    } else if (width >= breakpoints.wide) {
      newBreakpoint = 'wide';
    }

    setBreakpoint(newBreakpoint);
    setIsMobile(newBreakpoint === 'mobile');
    setIsTablet(newBreakpoint === 'tablet');
    setIsDesktop(newBreakpoint === 'desktop' || newBreakpoint === 'wide');
  }, [breakpoints]);

  useEffect(() => {
    updateBreakpoint();
    const handleResize = () => updateBreakpoint();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [breakpoints, updateBreakpoint]);

  return {
    breakpoint,
    screenSize,
    isMobile,
    isTablet,
    isDesktop,
    isWide: breakpoint === 'wide',
  };
}

// Responsive Grid Component
interface ResponsiveGridProps {
  children: React.ReactNode;
  columns?: {
    mobile?: number;
    tablet?: number;
    desktop?: number;
  };
  gap?: 'sm' | 'md' | 'lg';
  className?: string;
}

export function ResponsiveGrid({
  children,
  columns = { mobile: 1, tablet: 2, desktop: 3 },
  gap = 'md',
  className = ''
}: ResponsiveGridProps) {
  const { isMobile, isTablet } = useResponsive();

  const getGridClasses = () => {
    const baseClasses = 'responsive-grid grid';
    
    const gapClasses = {
      sm: 'gap-2',
      md: 'gap-4',
      lg: 'gap-6',
    };

    let colClasses = '';
    
    if (isMobile) {
      colClasses = `grid-cols-${columns.mobile || 1}`;
    } else if (isTablet) {
      colClasses = `grid-cols-${columns.tablet || 2}`;
    } else {
      colClasses = `grid-cols-${columns.desktop || 3}`;
    }

    return cn(baseClasses, colClasses, gapClasses[gap], className);
  };

  return (
    <div className={getGridClasses()}>
      {children}
    </div>
  );
}

// Responsive Container Component
interface ResponsiveContainerProps {
  children: React.ReactNode;
  maxWidth?: 'sm' | 'md' | 'lg' | 'xl' | 'full';
  padding?: 'none' | 'sm' | 'md' | 'lg';
  center?: boolean;
  className?: string;
}

export function ResponsiveContainer({
  children,
  maxWidth = 'lg',
  padding = 'md',
  center = true,
  className = ''
}: ResponsiveContainerProps) {
  const maxWidthClasses = {
    sm: 'max-w-sm',
    md: 'max-w-md',
    lg: 'max-w-lg',
    xl: 'max-w-xl',
    full: 'max-w-full',
  };

  const paddingClasses = {
    none: '',
    sm: 'px-2 py-2',
    md: 'px-4 py-4',
    lg: 'px-6 py-6',
  };

  return (
    <div 
      className={cn(
        'responsive-container w-full',
        maxWidthClasses[maxWidth],
        paddingClasses[padding],
        {
          'mx-auto': center,
        },
        className
      )}
    >
      {children}
    </div>
  );
}

// Responsive Image Component
interface ResponsiveImageProps {
  src: string;
  alt: string;
  sizes?: {
    mobile?: { width: number; height: number };
    tablet?: { width: number; height: number };
    desktop?: { width: number; height: number };
  };
  className?: string;
}

export function ResponsiveImage({
  src,
  alt,
  sizes,
  className = ''
}: ResponsiveImageProps) {
  const { isMobile, isTablet } = useResponsive();

  const getImageSize = () => {
    if (!sizes) return {};

    if (isMobile && sizes.mobile) {
      return { width: sizes.mobile.width, height: sizes.mobile.height };
    }
    
    if (isTablet && sizes.tablet) {
      return { width: sizes.tablet.width, height: sizes.tablet.height };
    }
    
    if (sizes.desktop) {
      return { width: sizes.desktop.width, height: sizes.desktop.height };
    }

    return {};
  };

  const size = getImageSize() as { width?: number; height?: number };
  return (
    <Image
      src={src}
      alt={alt}
      width={size.width || 40}
      height={size.height || 40}
      className={cn('responsive-image', className)}
    />
  );
}

// Responsive Text Component
interface ResponsiveTextProps {
  children: React.ReactNode;
  size?: {
    mobile?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
    tablet?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
    desktop?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  };
  weight?: 'normal' | 'medium' | 'semibold' | 'bold';
  className?: string;
  as?: 'p' | 'span' | 'h1' | 'h2' | 'h3' | 'h4' | 'h5' | 'h6';
}

export function ResponsiveText({
  children,
  size = { mobile: 'sm', tablet: 'md', desktop: 'md' },
  weight = 'normal',
  className = '',
  as: Component = 'p'
}: ResponsiveTextProps) {
  const { isMobile, isTablet } = useResponsive();
  const theme = useInterviewTheme();

  const getTextClasses = () => {
    const sizeClasses = {
      xs: 'text-xs',
      sm: 'text-sm',
      md: 'text-base',
      lg: 'text-lg',
      xl: 'text-xl',
    };

    const weightClasses = {
      normal: 'font-normal',
      medium: 'font-medium',
      semibold: 'font-semibold',
      bold: 'font-bold',
    };

    let currentSize = size.desktop || 'md';
    
    if (isMobile) {
      currentSize = size.mobile || 'sm';
    } else if (isTablet) {
      currentSize = size.tablet || 'md';
    }

    return cn(
      'responsive-text',
      sizeClasses[currentSize],
      weightClasses[weight],
      className
    );
  };

  return (
    <Component 
      className={getTextClasses()}
      style={{ color: theme.colors.text.primary }}
    >
      {children}
    </Component>
  );
}
