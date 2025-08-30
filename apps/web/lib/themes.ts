// Advanced Theme System for RecruiterAI
// Multiple theme support with sophisticated color palettes

export interface ThemeConfig {
  name: string;
  displayName: string;
  colors: {
    brand: {
      primary: string;
      secondary: string;
      accent: string;
      gradient: string;
    };
    ui: {
      background: string;
      surface: string;
      border: string;
      text: {
        primary: string;
        secondary: string;
        muted: string;
      };
    };
    status: {
      success: string;
      warning: string;
      error: string;
      info: string;
    };
    charts: string[];
  };
  shadows: {
    sm: string;
    md: string;
    lg: string;
    xl: string;
  };
  animations: {
    duration: {
      fast: string;
      normal: string;
      slow: string;
    };
    easing: {
      smooth: string;
      bounce: string;
      sharp: string;
    };
  };
}

// 🎯 Professional Corporate Theme
export const corporateTheme: ThemeConfig = {
  name: 'corporate',
  displayName: 'Kurumsal',
  colors: {
    brand: {
      primary: '#1e40af', // Blue 700
      secondary: '#3b82f6', // Blue 500
      accent: '#8b5cf6', // Purple 500
      gradient: 'linear-gradient(135deg, #1e40af 0%, #3b82f6 50%, #8b5cf6 100%)',
    },
    ui: {
      background: '#ffffff',
      surface: '#f8fafc',
      border: '#e2e8f0',
      text: {
        primary: '#0f172a',
        secondary: '#475569',
        muted: '#64748b',
      },
    },
    status: {
      success: '#10b981',
      warning: '#f59e0b',
      error: '#ef4444',
      info: '#3b82f6',
    },
    charts: ['#1e40af', '#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444'],
  },
  shadows: {
    sm: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
    md: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
    lg: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
    xl: '0 20px 25px -5px rgba(0, 0, 0, 0.1)',
  },
  animations: {
    duration: {
      fast: '150ms',
      normal: '300ms',
      slow: '500ms',
    },
    easing: {
      smooth: 'cubic-bezier(0.4, 0, 0.2, 1)',
      bounce: 'cubic-bezier(0.68, -0.55, 0.265, 1.55)',
      sharp: 'cubic-bezier(0.4, 0, 1, 1)',
    },
  },
};

// 🌙 Modern Dark Theme
export const modernDarkTheme: ThemeConfig = {
  name: 'modern-dark',
  displayName: 'Modern Karanlık',
  colors: {
    brand: {
      primary: '#6366f1', // Indigo 500
      secondary: '#8b5cf6', // Purple 500
      accent: '#06b6d4', // Cyan 500
      gradient: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #06b6d4 100%)',
    },
    ui: {
      background: '#0f172a',
      surface: '#1e293b',
      border: '#334155',
      text: {
        primary: '#f1f5f9',
        secondary: '#cbd5e1',
        muted: '#94a3b8',
      },
    },
    status: {
      success: '#22c55e',
      warning: '#fbbf24',
      error: '#f87171',
      info: '#60a5fa',
    },
    charts: ['#6366f1', '#8b5cf6', '#06b6d4', '#22c55e', '#fbbf24', '#f87171'],
  },
  shadows: {
    sm: '0 1px 2px 0 rgba(0, 0, 0, 0.3)',
    md: '0 4px 6px -1px rgba(0, 0, 0, 0.4)',
    lg: '0 10px 15px -3px rgba(0, 0, 0, 0.4)',
    xl: '0 20px 25px -5px rgba(0, 0, 0, 0.4)',
  },
  animations: {
    duration: {
      fast: '150ms',
      normal: '300ms',
      slow: '500ms',
    },
    easing: {
      smooth: 'cubic-bezier(0.4, 0, 0.2, 1)',
      bounce: 'cubic-bezier(0.68, -0.55, 0.265, 1.55)',
      sharp: 'cubic-bezier(0.4, 0, 1, 1)',
    },
  },
};

// 🌿 Natural Green Theme
export const naturalTheme: ThemeConfig = {
  name: 'natural',
  displayName: 'Doğal',
  colors: {
    brand: {
      primary: '#059669', // Emerald 600
      secondary: '#10b981', // Emerald 500
      accent: '#3b82f6', // Blue 500
      gradient: 'linear-gradient(135deg, #059669 0%, #10b981 50%, #3b82f6 100%)',
    },
    ui: {
      background: '#fefffe',
      surface: '#f0fdf4',
      border: '#d1fae5',
      text: {
        primary: '#064e3b',
        secondary: '#047857',
        muted: '#6b7280',
      },
    },
    status: {
      success: '#10b981',
      warning: '#f59e0b',
      error: '#ef4444',
      info: '#3b82f6',
    },
    charts: ['#059669', '#10b981', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6'],
  },
  shadows: {
    sm: '0 1px 2px 0 rgba(5, 150, 105, 0.1)',
    md: '0 4px 6px -1px rgba(5, 150, 105, 0.15)',
    lg: '0 10px 15px -3px rgba(5, 150, 105, 0.15)',
    xl: '0 20px 25px -5px rgba(5, 150, 105, 0.15)',
  },
  animations: {
    duration: {
      fast: '150ms',
      normal: '300ms',
      slow: '500ms',
    },
    easing: {
      smooth: 'cubic-bezier(0.4, 0, 0.2, 1)',
      bounce: 'cubic-bezier(0.68, -0.55, 0.265, 1.55)',
      sharp: 'cubic-bezier(0.4, 0, 1, 1)',
    },
  },
};

// 🎨 Available Themes Registry
export const availableThemes: ThemeConfig[] = [
  corporateTheme,
  modernDarkTheme,
  naturalTheme,
];

// 🛠️ Theme Utilities
export const getThemeByName = (name: string): ThemeConfig => {
  return availableThemes.find(theme => theme.name === name) || corporateTheme;
};

export const applyThemeToDocument = (theme: ThemeConfig): void => {
  if (typeof document === 'undefined') return;

  const root = document.documentElement;
  
  // Apply CSS custom properties
  root.style.setProperty('--theme-primary', theme.colors.brand.primary);
  root.style.setProperty('--theme-secondary', theme.colors.brand.secondary);
  root.style.setProperty('--theme-accent', theme.colors.brand.accent);
  root.style.setProperty('--theme-gradient', theme.colors.brand.gradient);
  
  root.style.setProperty('--theme-bg', theme.colors.ui.background);
  root.style.setProperty('--theme-surface', theme.colors.ui.surface);
  root.style.setProperty('--theme-border', theme.colors.ui.border);
  
  root.style.setProperty('--theme-text-primary', theme.colors.ui.text.primary);
  root.style.setProperty('--theme-text-secondary', theme.colors.ui.text.secondary);
  root.style.setProperty('--theme-text-muted', theme.colors.ui.text.muted);
  
  // Apply theme class
  root.className = root.className.replace(/theme-\w+/g, '');
  root.classList.add(`theme-${theme.name}`);
};

// 🌐 Export default theme
export const defaultTheme = corporateTheme;
