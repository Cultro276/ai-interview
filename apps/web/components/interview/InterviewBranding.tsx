"use client";

import React from 'react';
import Image from 'next/image';
import { useInterviewTheme } from './InterviewDesignSystem';
import { cn } from '@/components/ui/utils';

// Company branding integration
interface InterviewBrandingProps {
  companyLogo?: string;
  companyName?: string;
  jobTitle?: string;
  interviewType?: string;
  candidateName?: string;
  showBranding?: boolean;
  className?: string;
  variant?: 'header' | 'card' | 'minimal';
}

export function InterviewBranding({
  companyLogo,
  companyName,
  jobTitle,
  interviewType = "Sesli Görüşme",
  candidateName,
  showBranding = true,
  className = '',
  variant = 'header'
}: InterviewBrandingProps) {
  const theme = useInterviewTheme();

  if (!showBranding) return null;

  const brandingClasses = cn(
    'interview-branding',
    {
      'flex items-center space-x-4 p-4': variant === 'header',
      'text-center p-6 bg-white rounded-lg shadow-sm border': variant === 'card',
      'flex items-center space-x-2': variant === 'minimal',
    },
    className
  );

  return (
    <div className={brandingClasses}>
      {/* Company Logo */}
      {companyLogo && (
        <div className="brand-logo flex-shrink-0">
          {variant === 'card' ? (
            <div className="mx-auto mb-4">
              <Image
                src={companyLogo}
                alt={companyName || 'Company Logo'}
                width={80}
                height={80}
                className="object-contain"
              />
            </div>
          ) : (
            <Image
              src={companyLogo}
              alt={companyName || 'Company Logo'}
              width={variant === 'minimal' ? 32 : 48}
              height={variant === 'minimal' ? 32 : 48}
              className="object-contain"
            />
          )}
        </div>
      )}

      {/* Fallback Logo */}
      {!companyLogo && companyName && (
        <div 
          className={cn(
            "brand-logo-fallback flex-shrink-0 rounded-lg flex items-center justify-center text-white font-bold",
            {
              'w-12 h-12 text-lg': variant === 'header',
              'w-20 h-20 text-2xl mx-auto mb-4': variant === 'card',
              'w-8 h-8 text-sm': variant === 'minimal',
            }
          )}
          style={{ backgroundColor: theme.colors.primary }}
        >
          {companyName.charAt(0).toUpperCase()}
        </div>
      )}

      {/* Brand Information */}
      <div className={cn(
        "brand-info",
        {
          'flex-1': variant === 'header',
          'text-center': variant === 'card',
        }
      )}>
        {companyName && (
          <h1 
            className={cn(
              "company-name font-semibold",
              {
                'text-xl': variant === 'header',
                'text-2xl mb-2': variant === 'card',
                'text-lg': variant === 'minimal',
              }
            )}
            style={{ 
              color: theme.colors.text.primary,
              fontWeight: theme.typography.fontWeight.semibold,
            }}
          >
            {companyName}
          </h1>
        )}

        {jobTitle && (
          <p 
            className={cn(
              "job-title",
              {
                'text-base text-gray-600': variant === 'header',
                'text-lg text-gray-600 mb-1': variant === 'card',
                'text-sm text-gray-600': variant === 'minimal',
              }
            )}
            style={{ 
              color: theme.colors.text.secondary,
              fontSize: variant === 'card' ? theme.typography.fontSize.lg : theme.typography.fontSize.md,
            }}
          >
            {jobTitle}
          </p>
        )}

        {interviewType && (
          <p 
            className={cn(
              "interview-type",
              {
                'text-sm text-gray-500': variant === 'header',
                'text-base text-gray-500': variant === 'card',
                'text-xs text-gray-500': variant === 'minimal',
              }
            )}
            style={{ 
              color: theme.colors.text.muted,
              fontSize: variant === 'card' ? theme.typography.fontSize.md : theme.typography.fontSize.sm,
            }}
          >
            {interviewType}
          </p>
        )}

        {candidateName && variant === 'card' && (
          <div 
            className="candidate-welcome mt-4 p-3 rounded-lg"
            style={{ 
              backgroundColor: `${theme.colors.primary}10`,
              borderColor: `${theme.colors.primary}30`,
            }}
          >
            <p 
              className="text-sm"
              style={{ color: theme.colors.text.primary }}
            >
              Hoş geldiniz, <strong>{candidateName}</strong>
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

// Company Logo Component
interface CompanyLogoProps {
  src?: string;
  name?: string;
  size?: 'sm' | 'md' | 'lg';
  fallbackIcon?: string;
  className?: string;
}

export function CompanyLogo({
  src,
  name,
  size = 'md',
  fallbackIcon = '',
  className = ''
}: CompanyLogoProps) {
  const theme = useInterviewTheme();
  
  const sizeClasses = {
    sm: 'w-8 h-8',
    md: 'w-12 h-12',
    lg: 'w-16 h-16',
  };

  const textSizes = {
    sm: theme.typography.fontSize.sm,
    md: theme.typography.fontSize.md,
    lg: theme.typography.fontSize.lg,
  };

  if (src) {
    return (
      <Image
        src={src}
        alt={name || 'Company Logo'}
        width={size === 'sm' ? 32 : size === 'md' ? 48 : 64}
        height={size === 'sm' ? 32 : size === 'md' ? 48 : 64}
        className={cn('object-contain', className)}
      />
    );
  }

  return (
    <div 
      className={cn(
        'company-logo-fallback rounded-lg flex items-center justify-center text-white font-bold',
        sizeClasses[size],
        className
      )}
      style={{ 
        backgroundColor: theme.colors.primary,
        fontSize: textSizes[size],
      }}
    >
      {fallbackIcon || (name ? name.charAt(0).toUpperCase() : 'C')}
    </div>
  );
}

// Interview Title Section
interface InterviewTitleProps {
  title: string;
  subtitle?: string;
  status?: 'waiting' | 'active' | 'completed';
  className?: string;
}

export function InterviewTitle({
  title,
  subtitle,
  status = 'waiting',
  className = ''
}: InterviewTitleProps) {
  const theme = useInterviewTheme();

  const statusColors = {
    waiting: theme.colors.text.muted,
    active: theme.colors.interview.listening,
    completed: theme.colors.status.success,
  };

  const statusLabels = {
    waiting: 'Bekliyor',
    active: 'Devam Ediyor',
    completed: 'Tamamlandı',
  };

  return (
    <div className={cn('interview-title', className)}>
      <div className="flex items-center space-x-3">
        <h1 
          className="text-2xl font-bold"
          style={{ 
            color: theme.colors.text.primary,
            fontSize: theme.typography.fontSize['2xl'],
            fontWeight: theme.typography.fontWeight.bold,
          }}
        >
          {title}
        </h1>
        
        <div 
          className="status-indicator px-2 py-1 rounded-full text-xs font-medium"
          style={{ 
            backgroundColor: `${statusColors[status]}20`,
            color: statusColors[status],
            fontSize: theme.typography.fontSize.xs,
          }}
        >
          {statusLabels[status]}
        </div>
      </div>
      
      {subtitle && (
        <p 
          className="mt-1 text-lg"
          style={{ 
            color: theme.colors.text.secondary,
            fontSize: theme.typography.fontSize.lg,
          }}
        >
          {subtitle}
        </p>
      )}
    </div>
  );
}

// Professional Welcome Card
interface WelcomeCardProps {
  candidateName: string;
  companyName?: string;
  jobTitle?: string;
  interviewerName?: string;
  estimatedDuration?: number; // in minutes
  className?: string;
}

export function WelcomeCard({
  candidateName,
  companyName,
  jobTitle,
  interviewerName,
  estimatedDuration,
  className = ''
}: WelcomeCardProps) {
  const theme = useInterviewTheme();

  return (
    <div 
      className={cn(
        'welcome-card p-6 rounded-xl border',
        className
      )}
      style={{
        backgroundColor: theme.colors.surface,
        borderColor: `${theme.colors.text.muted}20`,
        boxShadow: theme.shadows.md,
      }}
    >
      <div className="welcome-content text-center">
        <h2 
          className="text-xl font-semibold mb-2"
          style={{ 
            color: theme.colors.text.primary,
            fontSize: theme.typography.fontSize.xl,
            fontWeight: theme.typography.fontWeight.semibold,
          }}
        >
          Hoş Geldiniz, {candidateName}!
        </h2>
        
        {companyName && jobTitle && (
          <p 
            className="text-base mb-4"
            style={{ 
              color: theme.colors.text.secondary,
              fontSize: theme.typography.fontSize.md,
            }}
          >
            <strong>{companyName}</strong> - {jobTitle} pozisyonu için görüşmeye katıldığınız için teşekkür ederiz.
          </p>
        )}

        <div 
          className="interview-details space-y-2 p-4 rounded-lg"
          style={{ 
            backgroundColor: `${theme.colors.primary}05`,
            border: `1px solid ${theme.colors.primary}20`,
          }}
        >
          {interviewerName && (
            <div className="flex items-center justify-center space-x-2">
              <span 
                className="text-sm"
                style={{ color: theme.colors.text.muted }}
              >
                Görüşmeci:
              </span>
              <span 
                className="text-sm font-medium"
                style={{ color: theme.colors.text.primary }}
              >
                {interviewerName}
              </span>
            </div>
          )}
          
          {estimatedDuration && (
            <div className="flex items-center justify-center space-x-2">
              <span 
                className="text-sm"
                style={{ color: theme.colors.text.muted }}
              >
                Tahmini Süre:
              </span>
              <span 
                className="text-sm font-medium"
                style={{ color: theme.colors.text.primary }}
              >
                {estimatedDuration} dakika
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// Interview Type Badge
interface InterviewTypeBadgeProps {
  type: 'technical' | 'behavioral' | 'cultural' | 'general';
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export function InterviewTypeBadge({
  type,
  size = 'md',
  className = ''
}: InterviewTypeBadgeProps) {
  const theme = useInterviewTheme();

  const typeConfig = {
    technical: {
      label: 'Teknik',
      icon: '⚙️',
      color: theme.colors.status.info,
    },
    behavioral: {
      label: 'Davranışsal',
      icon: '🧠',
      color: theme.colors.status.warning,
    },
    cultural: {
      label: 'Kültürel',
      icon: '🤝',
      color: theme.colors.status.success,
    },
    general: {
      label: 'Genel',
      icon: '💼',
      color: theme.colors.text.muted,
    },
  };

  const sizeClasses = {
    sm: 'px-2 py-1 text-xs',
    md: 'px-3 py-1 text-sm',
    lg: 'px-4 py-2 text-base',
  };

  const config = typeConfig[type];

  return (
    <span 
      className={cn(
        'interview-type-badge inline-flex items-center space-x-1 rounded-full font-medium',
        sizeClasses[size],
        className
      )}
      style={{
        backgroundColor: `${config.color}15`,
        color: config.color,
        border: `1px solid ${config.color}30`,
      }}
    >
      <span>{config.icon}</span>
      <span>{config.label}</span>
    </span>
  );
}
