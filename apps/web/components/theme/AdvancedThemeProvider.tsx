'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';
import { ThemeConfig, defaultTheme, getThemeByName, applyThemeToDocument, availableThemes } from '@/lib/themes';

interface ThemeContextType {
  currentTheme: ThemeConfig;
  setTheme: (themeName: string) => void;
  availableThemes: ThemeConfig[];
  toggleDarkMode: () => void;
  isDarkMode: boolean;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

interface AdvancedThemeProviderProps {
  children: React.ReactNode;
  initialTheme?: string;
}

export function AdvancedThemeProvider({ children, initialTheme }: AdvancedThemeProviderProps) {
  const [currentTheme, setCurrentTheme] = useState<ThemeConfig>(defaultTheme);
  const [isDarkMode, setIsDarkMode] = useState(false);

  // Load theme from localStorage on mount
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const savedTheme = localStorage.getItem('recruiter-ai-theme');
      const savedDarkMode = localStorage.getItem('recruiter-ai-dark-mode') === 'true';
      
      if (savedTheme) {
        const theme = getThemeByName(savedTheme);
        setCurrentTheme(theme);
        applyThemeToDocument(theme);
      } else if (initialTheme) {
        const theme = getThemeByName(initialTheme);
        setCurrentTheme(theme);
        applyThemeToDocument(theme);
      }
      
      setIsDarkMode(savedDarkMode);
      if (savedDarkMode) {
        document.documentElement.classList.add('dark');
      }
    }
  }, [initialTheme]);

  const setTheme = (themeName: string) => {
    const newTheme = getThemeByName(themeName);
    setCurrentTheme(newTheme);
    applyThemeToDocument(newTheme);
    
    if (typeof window !== 'undefined') {
      localStorage.setItem('recruiter-ai-theme', themeName);
    }
  };

  const toggleDarkMode = () => {
    const newDarkMode = !isDarkMode;
    setIsDarkMode(newDarkMode);
    
    if (typeof window !== 'undefined') {
      if (newDarkMode) {
        document.documentElement.classList.add('dark');
      } else {
        document.documentElement.classList.remove('dark');
      }
      localStorage.setItem('recruiter-ai-dark-mode', newDarkMode.toString());
    }
  };

  const contextValue: ThemeContextType = {
    currentTheme,
    setTheme,
    availableThemes,
    toggleDarkMode,
    isDarkMode,
  };

  return (
    <ThemeContext.Provider value={contextValue}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme(): ThemeContextType {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error('useTheme must be used within an AdvancedThemeProvider');
  }
  return context;
}

// 🎨 Theme Selector Component
export function ThemeSelector() {
  const { currentTheme, setTheme, availableThemes, toggleDarkMode, isDarkMode } = useTheme();

  return (
    <div className="flex items-center space-x-4">
      {/* Theme Dropdown */}
      <div className="relative">
        <select
          value={currentTheme.name}
          onChange={(e) => setTheme(e.target.value)}
          className="appearance-none bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg px-4 py-2 pr-8 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {availableThemes.map((theme) => (
            <option key={theme.name} value={theme.name}>
              {theme.displayName}
            </option>
          ))}
        </select>
        <div className="absolute inset-y-0 right-0 flex items-center px-2 pointer-events-none">
          <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </div>

      {/* Dark Mode Toggle */}
      <button
        onClick={toggleDarkMode}
        className="p-2 rounded-lg bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
        title={isDarkMode ? 'Açık moda geç' : 'Karanlık moda geç'}
      >
        {isDarkMode ? (
          <svg className="w-5 h-5 text-yellow-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
          </svg>
        ) : (
          <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
          </svg>
        )}
      </button>
    </div>
  );
}

// 🎨 Theme Preview Component
export function ThemePreview({ theme }: { theme: ThemeConfig }) {
  return (
    <div className="p-4 border rounded-lg space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold">{theme.displayName}</h3>
        <div className="flex space-x-1">
          {theme.colors.charts.slice(0, 4).map((color, index) => (
            <div
              key={index}
              className="w-4 h-4 rounded-full"
              style={{ backgroundColor: color }}
            />
          ))}
        </div>
      </div>
      
      <div className="grid grid-cols-3 gap-2 text-xs">
        <div className="text-center">
          <div 
            className="w-full h-8 rounded mb-1"
            style={{ backgroundColor: theme.colors.brand.primary }}
          />
          <span>Primary</span>
        </div>
        <div className="text-center">
          <div 
            className="w-full h-8 rounded mb-1"
            style={{ backgroundColor: theme.colors.brand.secondary }}
          />
          <span>Secondary</span>
        </div>
        <div className="text-center">
          <div 
            className="w-full h-8 rounded mb-1"
            style={{ backgroundColor: theme.colors.brand.accent }}
          />
          <span>Accent</span>
        </div>
      </div>
    </div>
  );
}
