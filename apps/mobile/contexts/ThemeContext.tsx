import React, { createContext, useContext, useState, useEffect, useMemo, ReactNode, useCallback } from 'react';
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

export interface ThemeContextType {
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

  const loadSettings = useCallback(async () => {
    try {
      const stored = await AsyncStorage.getItem(STORAGE_KEY);
      if (stored) {
        setSettings((prev) => ({ ...prev, ...JSON.parse(stored) }));
      }
    } catch (error) {
      console.error('Failed to load theme settings:', error);
    }
  }, []);

  useEffect(() => {
    loadSettings();
  }, [loadSettings]);

  const updateSettings = useCallback(async (newSettings: Partial<AppearanceSettings>) => {
    try {
      setSettings((prev) => {
        const merged = { ...prev, ...newSettings };
        AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(merged)).catch((e) =>
          console.error('Failed to save theme settings:', e)
        );
        return merged;
      });
    } catch (error) {
      console.error('Failed to update theme settings:', error);
    }
  }, []);

  // Determine actual theme mode
  const isDark = settings.theme === 'system' ? deviceColorScheme === 'dark' : settings.theme === 'dark';

  const toggleTheme = useCallback(() => {
    const nextTheme = isDark ? 'light' : 'dark';
    updateSettings({ theme: nextTheme });
  }, [isDark, updateSettings]);

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
  }), [settings, updateSettings, colors, spacing, fontSizes, isDark, toggleTheme]);

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
