// THEME CONSTANTS
// Professional blue/gray with safety orange accent

export const Colors = {
  // Primary - Deep Black / Dark Charcoal
  primary: '#171717',
  primaryDark: '#0A0A0A',
  primaryLight: '#262626',
  
  // Secondary - Cool Grey
  secondary: '#525252',
  secondaryDark: '#404040',
  secondaryLight: '#737373',
  
  // Accent - Silver / Slate (Professional contrast)
  accent: '#334155',
  accentDark: '#1E293B',
  accentLight: '#64748B',
  
  // Status Colors (Muted for elegance)
  success: '#10B981',
  successLight: '#D1FAE5',
  warning: '#F59E0B',
  warningLight: '#FEF3C7',
  error: '#EF4444',
  errorLight: '#FEE2E2',
  info: '#3B82F6',
  infoLight: '#DBEAFE',
  
  // Neutrals 
  white: '#FFFFFF',
  background: '#F8FAFC', // Slate 50 for a professional tint
  surface: '#FFFFFF',
  border: '#E2E8F0',
  divider: '#CBD5E1',
  
  // Text
  text: '#0F172A',
  textSecondary: '#475569',
  textMuted: '#94A3B8',
  textInverse: '#FFFFFF',
  
  // Specific UI
  headerBg: '#171717', // Dark header
  tabBarBg: '#FFFFFF',
  cardBg: '#FFFFFF',
  inputBg: '#F1F5F9',
  inputBorder: '#E2E8F0',
  placeholder: '#94A3B8',
};

export const Spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  xxl: 48,
};

export const FontSizes = {
  xs: 12,
  sm: 14,
  md: 16,
  lg: 18,
  xl: 20,
  xxl: 24,
  xxxl: 32,
};

export const BorderRadius = {
  sm: 4,
  md: 8,
  lg: 12,
  xl: 16,
  full: 9999,
};

export const Shadows = {
  sm: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 1,
  },
  md: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  lg: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.15,
    shadowRadius: 8,
    elevation: 5,
  },
};

export default {
  Colors,
  Spacing,
  FontSizes,
  BorderRadius,
  Shadows,
};
