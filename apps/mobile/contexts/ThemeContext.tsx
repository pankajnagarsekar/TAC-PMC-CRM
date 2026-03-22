import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useColorScheme as useDeviceColorScheme } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Colors as BaseColors, Spacing as BaseSpacing, FontSizes as BaseFontSizes, BorderRadius, Shadows } from '../constants/theme';

const STORAGE_KEY = 'app_appearance_settings';

export interface AppearanceSettings {
  theme: 'light' | 'dark' | 'system';
  fontSize: 'small' | 'medium' | 'large';
  compactMode: boolean;
  showAmounts: boolean;
  colorScheme: string;
}

export const defaultSettings: AppearanceSettings = {
  theme: 'light',
  fontSize: 'medium',
  compactMode: false,
  showAmounts: true,
  colorScheme: 'blue',
};

// Color palettes based on appearance.tsx options
const COLOR_SCHEME_PALETTES: Record<string, { primary: string, primaryDark: string, primaryLight: string }> = {
  blue: { primary: '#2563eb', primaryDark: '#1d4ed8', primaryLight: '#3b82f6' },
  green: { primary: '#059669', primaryDark: '#047857', primaryLight: '#10b981' },
  purple: { primary: '#7c3aed', primaryDark: '#6d28d9', primaryLight: '#8b5cf6' },
  orange: { primary: '#ea580c', primaryDark: '#c2410c', primaryLight: '#f97316' },
  red: { primary: '#dc2626', primaryDark: '#b91c1c', primaryLight: '#ef4444' },
};

interface ThemeContextType {
  settings: AppearanceSettings;
  updateSettings: (newSettings: Partial<AppearanceSettings>) => Promise<void>;
  colors: typeof BaseColors;
  spacing: typeof BaseSpacing;
  fontSizes: typeof BaseFontSizes;
  borderRadius: typeof BorderRadius;
  shadows: typeof Shadows;
  isDark: boolean;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const deviceColorScheme = useDeviceColorScheme();
  const [settings, setSettings] = useState<AppearanceSettings>(defaultSettings);
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const stored = await AsyncStorage.getItem(STORAGE_KEY);
      if (stored) {
        setSettings({ ...defaultSettings, ...JSON.parse(stored) });
      }
    } catch (error) {
      console.error('Failed to load theme settings:', error);
    } finally {
      setIsLoaded(true);
    }
  };

  const updateSettings = async (newSettings: Partial<AppearanceSettings>) => {
    try {
      const merged = { ...settings, ...newSettings };
      await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(merged));
      setSettings(merged);
    } catch (error) {
      console.error('Failed to save theme settings:', error);
    }
  };

  const toggleTheme = () => {
    const nextTheme = isDark ? 'light' : 'dark';
    updateSettings({ theme: nextTheme });
  };

  // Determine actual theme mode
  const isDark = settings.theme === 'system' ? deviceColorScheme === 'dark' : settings.theme === 'dark';

  // Construct dynamic Colors
  const colors = { ...BaseColors };

  if (isDark) {
    colors.background = '#0f1113';
    colors.surface = '#17191c';
    colors.primary = '#e9c176';
    colors.text = '#F8FAFC';
    colors.textSecondary = '#94a3b8';
    colors.textMuted = '#64748b';
    colors.textInverse = '#0F172A';
    colors.border = '#24272b';
    colors.divider = '#24272b';
    colors.headerBg = '#0f1113';
    colors.tabBarBg = '#0f1113';
    colors.cardBg = '#17191c';
    colors.inputBg = '#0f1113';
    colors.inputBorder = '#24272b';
    colors.placeholder = '#4b5563';
  } else {
    colors.background = '#f8f9fb';
    colors.surface = '#FFFFFF';
    colors.primary = '#775a19';
    colors.text = '#191c1e';
    colors.textSecondary = '#52617c';
    colors.textMuted = '#94a3b8';
    colors.textInverse = '#FFFFFF';
    colors.border = '#eceef0';
    colors.divider = '#eceef0';
    colors.headerBg = '#f8f9fb';
    colors.tabBarBg = '#f8f9fb';
    colors.cardBg = '#FFFFFF';
    colors.inputBg = '#f8f9fb';
    colors.inputBorder = '#eceef0';
    colors.placeholder = '#94a3b8';
  }

  // Construct dynamic Spacing
  const spacing = { ...BaseSpacing };
  if (settings.compactMode) {
    spacing.xs = 2;
    spacing.sm = 4;
    spacing.md = 8;
    spacing.lg = 12;
    spacing.xl = 16;
    spacing.xxl = 24;
  }

  // Construct dynamic FontSizes
  const fontSizes = { ...BaseFontSizes };
  if (settings.fontSize === 'small') {
    Object.keys(fontSizes).forEach((key) => {
      fontSizes[key as keyof typeof BaseFontSizes] -= 2;
    });
  } else if (settings.fontSize === 'large') {
    Object.keys(fontSizes).forEach((key) => {
      fontSizes[key as keyof typeof BaseFontSizes] += 2;
    });
  }

  const value = {
    settings,
    updateSettings,
    colors,
    spacing,
    fontSizes,
    borderRadius: BorderRadius,
    shadows: Shadows,
    isDark,
    toggleTheme
  };

  if (!isLoaded) return null; // Wait for async storage

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
}
