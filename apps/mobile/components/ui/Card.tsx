// CARD COMPONENT
// Reusable card container

import React, { ReactNode } from 'react';
import { View, ViewStyle, StyleProp, TouchableOpacity, Platform } from 'react-native';
import { BlurView } from 'expo-blur';
import { useTheme } from '../../contexts/ThemeContext';

interface CardProps {
  children: ReactNode;
  style?: StyleProp<ViewStyle>;
  onPress?: () => void;
  variant?: 'default' | 'outlined' | 'elevated' | 'glass';
  padding?: 'none' | 'sm' | 'md' | 'lg';
}

export function Card({
  children,
  style,
  onPress,
  variant = 'default',
  padding = 'md',
}: CardProps) {
  const { colors, spacing, borderRadius, shadows, isDark } = useTheme();

  const getVariantStyle = () => {
    switch (variant) {
      case 'outlined':
        return {
          borderWidth: 1,
          borderColor: colors.border,
          backgroundColor: colors.surface,
        };
      case 'glass':
        return {
          // Strictly Professional: Highly opaque base for legibility
          backgroundColor: isDark ? 'rgba(30, 32, 35, 0.9)' : 'rgba(255, 255, 255, 0.95)',
          borderWidth: 1,
          borderColor: isDark ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.05)',
          ...shadows.sm,
        };
      case 'elevated':
        return {
          ...shadows.lg,
          backgroundColor: colors.surface,
        };
      default:
        return {
          ...shadows.md,
          backgroundColor: colors.surface,
        };
    }
  };

  const getPaddingStyle = () => {
    switch (padding) {
      case 'none':
        return { padding: 0 };
      case 'sm':
        return { padding: spacing.sm };
      case 'lg':
        return { padding: spacing.lg };
      default:
        return { padding: spacing.md };
    }
  };

  const Content = (
    <View style={[
      { borderRadius: borderRadius.lg, overflow: 'hidden' }, // Ensure content respects card radius
      getPaddingStyle(),
    ]}>
      {children}
    </View>
  );

  const cardContainerStyle = [
    {
      borderRadius: borderRadius.lg,
    },
    getVariantStyle(),
    style,
  ];

  if (onPress) {
    return (
      <TouchableOpacity
        style={cardContainerStyle as StyleProp<ViewStyle>}
        onPress={onPress}
        activeOpacity={0.7}
      >
        {variant === 'glass' ? (
          <BlurView intensity={isDark ? 20 : 30} tint={isDark ? "dark" : "light"} style={{ borderRadius: borderRadius.lg }}>
            {Content}
          </BlurView>
        ) : Content}
      </TouchableOpacity>
    );
  }

  return (
    <View style={cardContainerStyle as StyleProp<ViewStyle>}>
      {variant === 'glass' ? (
        <BlurView intensity={isDark ? 20 : 30} tint={isDark ? "dark" : "light"} style={{ borderRadius: borderRadius.lg }}>
          {Content}
        </BlurView>
      ) : Content}
    </View>
  );
}

export default Card;
