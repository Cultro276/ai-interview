"use client";

import React, { useState, useEffect } from 'react';
import { useInterviewTheme } from './InterviewDesignSystem';
import { cn } from '@/components/ui/utils';

// Contextual help and guidance
interface HelpTip {
  id: string;
  title: string;
  content: string;
  icon: string;
  category: 'general' | 'technical' | 'interview' | 'troubleshooting' | 'accessibility';
  priority: 'low' | 'medium' | 'high';
  keywords: string[];
  relatedTips?: string[];
}

interface InterviewHelpProps {
  tips: HelpTip[];
  currentContext?: string;
  showTooltips?: boolean;
  onTipClick?: (tipId: string) => void;
  className?: string;
  variant?: 'sidebar' | 'modal' | 'inline' | 'floating';
}

export function InterviewHelp({
  tips,
  currentContext,
  showTooltips = true,
  onTipClick,
  className = '',
  variant = 'sidebar'
}: InterviewHelpProps) {
  const theme = useInterviewTheme();
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedTip, setExpandedTip] = useState<string | null>(null);

  // Filter tips based on context, category, and search
  const filteredTips = tips.filter(tip => {
    const matchesContext = !currentContext || tip.category === currentContext;
    const matchesCategory = selectedCategory === 'all' || tip.category === selectedCategory;
    const matchesSearch = !searchQuery || 
      tip.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      tip.content.toLowerCase().includes(searchQuery.toLowerCase()) ||
      tip.keywords.some(keyword => keyword.toLowerCase().includes(searchQuery.toLowerCase()));
    
    return matchesContext && matchesCategory && matchesSearch;
  });

  // Sort by priority and relevance
  const sortedTips = filteredTips.sort((a, b) => {
    const priorityOrder = { high: 3, medium: 2, low: 1 };
    return priorityOrder[b.priority] - priorityOrder[a.priority];
  });

  const categories = [
    { id: 'all', label: 'Tümü', icon: '📋' },
    { id: 'general', label: 'Genel', icon: '💡' },
    { id: 'technical', label: 'Teknik', icon: '⚙️' },
    { id: 'interview', label: 'Mülakat', icon: '🎤' },
    { id: 'troubleshooting', label: 'Sorun Giderme', icon: '🔧' },
    { id: 'accessibility', label: 'Erişilebilirlik', icon: '♿' },
  ];

  const helpClasses = cn(
    'interview-help',
    {
      'w-80 h-full flex flex-col': variant === 'sidebar',
      'max-w-2xl mx-auto': variant === 'modal',
      'w-full': variant === 'inline',
      'fixed bottom-4 right-4 w-96 max-h-96 bg-white rounded-lg shadow-xl border': variant === 'floating',
    },
    className
  );

  return (
    <div 
      className={helpClasses}
      style={{
        backgroundColor: theme.colors.surface,
        borderColor: `${theme.colors.text.muted}20`,
      }}
    >
      {/* Help Header */}
      <div 
        className="help-header p-4 border-b"
        style={{ borderColor: `${theme.colors.text.muted}20` }}
      >
        <h3 
          className="text-lg font-semibold mb-2"
          style={{ 
            color: theme.colors.text.primary,
            fontSize: theme.typography.fontSize.lg,
            fontWeight: theme.typography.fontWeight.semibold,
          }}
        >
          Yardım & Rehber
        </h3>

        {/* Search */}
        <div className="help-search relative">
          <input
            type="text"
            placeholder="Yardım ara..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full px-3 py-2 pl-10 text-sm rounded-md border focus:outline-none focus:ring-2 focus:ring-opacity-50"
            style={{
              backgroundColor: theme.colors.background,
              borderColor: `${theme.colors.text.muted}30`,
              color: theme.colors.text.primary,
            }}
          />
          <div 
            className="absolute left-3 top-1/2 transform -translate-y-1/2"
            style={{ color: theme.colors.text.muted }}
          >
            🔍
          </div>
        </div>
      </div>

      {/* Category Filter */}
      <div 
        className="help-categories p-4 border-b"
        style={{ borderColor: `${theme.colors.text.muted}20` }}
      >
        <div className="flex flex-wrap gap-2">
          {categories.map(category => (
            <button
              key={category.id}
              onClick={() => setSelectedCategory(category.id)}
              className={cn(
                "category-btn flex items-center space-x-1 px-3 py-1 text-xs rounded-full transition-all duration-200",
                {
                  'ring-2 ring-opacity-50': selectedCategory === category.id,
                }
              )}
              style={{
                backgroundColor: selectedCategory === category.id 
                  ? `${theme.colors.primary}20` 
                  : `${theme.colors.text.muted}10`,
                color: selectedCategory === category.id 
                  ? theme.colors.primary 
                  : theme.colors.text.secondary,
              }}
            >
              <span>{category.icon}</span>
              <span>{category.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Help Tips */}
      <div className="help-tips flex-1 overflow-auto p-4">
        {sortedTips.length === 0 ? (
          <div className="empty-state text-center py-8">
            <div className="text-4xl mb-2">🤷‍♂️</div>
            <p 
              className="text-sm"
              style={{ color: theme.colors.text.muted }}
            >
              {searchQuery ? 'Aramanızla eşleşen yardım bulunamadı.' : 'Bu kategori için yardım bulunamadı.'}
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {sortedTips.map(tip => (
              <HelpTipItem
                key={tip.id}
                tip={tip}
                isExpanded={expandedTip === tip.id}
                onToggle={(id) => setExpandedTip(expandedTip === id ? null : id)}
                onClick={() => onTipClick?.(tip.id)}
                showTooltips={showTooltips}
                theme={theme}
              />
            ))}
          </div>
        )}
      </div>

      {/* Help Footer */}
      {variant !== 'floating' && (
        <div 
          className="help-footer p-4 border-t"
          style={{ borderColor: `${theme.colors.text.muted}20` }}
        >
          <div className="flex items-center justify-between">
            <span 
              className="text-xs"
              style={{ color: theme.colors.text.muted }}
            >
              {sortedTips.length} yardım bulundu
            </span>
            <button
              className="text-xs underline"
              style={{ color: theme.colors.primary }}
            >
              Daha fazla yardım
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// Individual Help Tip Item
interface HelpTipItemProps {
  tip: HelpTip;
  isExpanded: boolean;
  onToggle: (id: string) => void;
  onClick?: () => void;
  showTooltips: boolean;
  theme: any;
}

function HelpTipItem({
  tip,
  isExpanded,
  onToggle,
  onClick,
  showTooltips,
  theme
}: HelpTipItemProps) {
  const getPriorityColor = (priority: HelpTip['priority']) => {
    switch (priority) {
      case 'high':
        return theme.colors.status.error;
      case 'medium':
        return theme.colors.status.warning;
      case 'low':
        return theme.colors.status.info;
      default:
        return theme.colors.text.muted;
    }
  };

  return (
    <div 
      className="help-tip border rounded-lg overflow-hidden transition-all duration-200"
      style={{
        backgroundColor: theme.colors.background,
        borderColor: `${theme.colors.text.muted}20`,
      }}
    >
      {/* Tip Header */}
      <div 
        className="tip-header p-3 cursor-pointer hover:bg-opacity-50"
        onClick={() => onToggle(tip.id)}
        style={{
          backgroundColor: `${getPriorityColor(tip.priority)}05`,
        }}
      >
        <div className="flex items-start justify-between">
          <div className="flex items-start space-x-3 flex-1">
            <div className="tip-icon text-lg flex-shrink-0">
              {tip.icon}
            </div>
            <div className="tip-info flex-1 min-w-0">
              <h4 
                className="tip-title text-sm font-medium"
                style={{ 
                  color: theme.colors.text.primary,
                  fontSize: theme.typography.fontSize.sm,
                  fontWeight: theme.typography.fontWeight.medium,
                }}
              >
                {tip.title}
              </h4>
              <div className="tip-meta flex items-center space-x-2 mt-1">
                <span 
                  className="priority-badge text-xs px-2 py-0.5 rounded-full"
                  style={{
                    backgroundColor: `${getPriorityColor(tip.priority)}20`,
                    color: getPriorityColor(tip.priority),
                  }}
                >
                  {tip.priority === 'high' ? 'Yüksek' : 
                   tip.priority === 'medium' ? 'Orta' : 'Düşük'}
                </span>
                <span 
                  className="category text-xs"
                  style={{ color: theme.colors.text.muted }}
                >
                  {tip.category}
                </span>
              </div>
            </div>
          </div>
          
          <button
            className="expand-btn text-sm transition-transform duration-200"
            style={{ 
              color: theme.colors.text.muted,
              transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)',
            }}
          >
            ▼
          </button>
        </div>
      </div>

      {/* Tip Content */}
      {isExpanded && (
        <div 
          className="tip-content p-3 border-t"
          style={{ borderColor: `${theme.colors.text.muted}20` }}
        >
          <p 
            className="tip-text text-sm leading-relaxed"
            style={{ 
              color: theme.colors.text.secondary,
              fontSize: theme.typography.fontSize.sm,
            }}
          >
            {tip.content}
          </p>

          {/* Keywords */}
          {tip.keywords.length > 0 && (
            <div className="tip-keywords mt-3">
              <div className="flex flex-wrap gap-1">
                {tip.keywords.map(keyword => (
                  <span
                    key={keyword}
                    className="keyword text-xs px-2 py-0.5 rounded"
                    style={{
                      backgroundColor: `${theme.colors.text.muted}10`,
                      color: theme.colors.text.muted,
                    }}
                  >
                    {keyword}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Action Button */}
          {onClick && (
            <div className="tip-actions mt-3">
              <button
                onClick={onClick}
                className="action-btn text-sm px-3 py-1 rounded transition-all duration-200 hover:opacity-80"
                style={{
                  backgroundColor: theme.colors.primary,
                  color: 'white',
                }}
              >
                Detayı Gör
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Quick Help Widget
interface QuickHelpProps {
  tips: HelpTip[];
  maxTips?: number;
  autoShow?: boolean;
  className?: string;
}

export function QuickHelp({
  tips,
  maxTips = 3,
  autoShow = true,
  className = ''
}: QuickHelpProps) {
  const theme = useInterviewTheme();
  const [isVisible, setIsVisible] = useState(autoShow);

  // Show only high priority tips
  const highPriorityTips = tips
    .filter(tip => tip.priority === 'high')
    .slice(0, maxTips);

  if (!isVisible || highPriorityTips.length === 0) {
    return null;
  }

  return (
    <div 
      className={cn(
        'quick-help fixed top-4 right-4 w-80 bg-white rounded-lg shadow-lg border z-50',
        className
      )}
      style={{
        backgroundColor: theme.colors.background,
        borderColor: `${theme.colors.status.warning}50`,
        boxShadow: theme.shadows.lg,
      }}
    >
      {/* Header */}
      <div 
        className="quick-help-header p-3 border-b flex items-center justify-between"
        style={{
          backgroundColor: `${theme.colors.status.warning}10`,
          borderColor: `${theme.colors.text.muted}20`,
        }}
      >
        <div className="flex items-center space-x-2">
          <span>💡</span>
          <h4 
            className="text-sm font-medium"
            style={{ 
              color: theme.colors.text.primary,
              fontWeight: theme.typography.fontWeight.medium,
            }}
          >
            Önemli İpuçları
          </h4>
        </div>
        
        <button
          onClick={() => setIsVisible(false)}
          className="text-sm transition-colors duration-200 hover:opacity-70"
          style={{ color: theme.colors.text.muted }}
        >
          ×
        </button>
      </div>

      {/* Tips */}
      <div className="quick-help-content p-3 space-y-2">
        {highPriorityTips.map(tip => (
          <div
            key={tip.id}
            className="quick-tip flex items-start space-x-2 p-2 rounded-md"
            style={{
              backgroundColor: `${theme.colors.primary}05`,
            }}
          >
            <span className="tip-icon text-sm">{tip.icon}</span>
            <div className="tip-content flex-1 min-w-0">
              <p 
                className="tip-title text-xs font-medium"
                style={{ 
                  color: theme.colors.text.primary,
                  fontSize: theme.typography.fontSize.xs,
                }}
              >
                {tip.title}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// Help Context Provider
interface HelpContextType {
  showHelp: (context?: string) => void;
  hideHelp: () => void;
  isHelpVisible: boolean;
  currentContext: string | null;
}

const HelpContext = React.createContext<HelpContextType | null>(null);

interface HelpProviderProps {
  children: React.ReactNode;
  tips: HelpTip[];
}

export function HelpProvider({ children, tips }: HelpProviderProps) {
  const [isHelpVisible, setIsHelpVisible] = useState(false);
  const [currentContext, setCurrentContext] = useState<string | null>(null);

  const showHelp = (context?: string) => {
    setCurrentContext(context || null);
    setIsHelpVisible(true);
  };

  const hideHelp = () => {
    setIsHelpVisible(false);
    setCurrentContext(null);
  };

  const value: HelpContextType = {
    showHelp,
    hideHelp,
    isHelpVisible,
    currentContext,
  };

  return (
    <HelpContext.Provider value={value}>
      {children}
      {isHelpVisible && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div className="max-w-2xl w-full mx-4">
            <InterviewHelp
              tips={tips}
              currentContext={currentContext || undefined}
              variant="modal"
            />
            <button
              onClick={hideHelp}
              className="mt-4 w-full py-2 bg-white rounded-md text-center"
            >
              Kapat
            </button>
          </div>
        </div>
      )}
    </HelpContext.Provider>
  );
}

export function useHelp() {
  const context = React.useContext(HelpContext);
  if (!context) {
    throw new Error('useHelp must be used within HelpProvider');
  }
  return context;
}
