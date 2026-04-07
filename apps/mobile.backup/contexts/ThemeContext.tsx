import React, { createContext, useContext, useState, useEffect, useMemo, ReactNode } from 'react';
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

  // CM-06: Memoize derived tokens so consumers don't re-render on unrelated state changes
  const colors = useMemo(() => {
    const c = { ...BaseColors };
    if (isDark) {
      c.background = '#0f1113';
      c.surface = '#17191c';
      c.primary = '#e9c176';
      c.text = '#F8FAFC';
      c.textSecondary = '#94a3b8';
      c.textMuted = '#64748b';
      c.textInverse = '#0F172A';
      c.border = '#24272b';
      c.divider = '#24272b';
      c.headerBg = '#0f1113';
      c.tabBarBg = '#0f1113';
      c.cardBg = '#17191c';
      c.inputBg = '#0f1113';
      c.inputBorder = '#24272b';
      c.placeholder = '#4b5563';
    } else {
      c.background = '#f8f9fb';
      c.surface = '#FFFFFF';
      c.primary = '#775a19';
      c.text = '#191c1e';
      c.textSecondary = '#52617c';
      c.textMuted = '#94a3b8';
      c.textInverse = '#FFFFFF';
      c.border = '#eceef0';
      c.divider = '#eceef0';
      c.headerBg = '#f8f9fb';
      c.tabBarBg = '#f8f9fb';
      c.cardBg = '#FFFFFF';
      c.inputBg = '#f8f9fb';
      c.inputBorder = '#eceef0';
      c.placeholder = '#94a3b8';
    }
    return c;
  }, [isDark]);

  const spacing = useMemo(() => {
    const s = { ...BaseSpacing };
    if (settings.compactMode) {
      s.xs = 2; s.sm = 4; s.md = 8; s.lg = 12; s.xl = 16; s.xxl = 24;
    }
    return s;
  }, [settings.compactMode]);

  const fontSizes = useMemo(() => {
    const f = { ...BaseFontSizes };
    if (settings.fontSize === 'small') {
      Object.keys(f).forEach((key) => { f[key as keyof typeof BaseFontSizes] -= 2; });
    } else if (settings.fontSize === 'large') {
      Object.keys(f).forEach((key) => { f[key as keyof typeof BaseFontSizes] += 2; });
    }
    return f;
  }, [settings.fontSize]);

  const value = useMemo(() => ({
    settings,
    updateSettings,
    colors,
    spacing,
    fontSizes,
    borderRadius: BorderRadius,
    shadows: Shadows,
    isDark,
    toggleTheme,
  }), [settings, colors, spacing, fontSizes, isDark, updateSettings, toggleTheme]);

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
