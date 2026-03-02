// CARD COMPONENT
// Reusable card container

import React, { ReactNode } from 'react';
import { View, ViewStyle, StyleProp, TouchableOpacity } from 'react-native';
import { useTheme } from '../../contexts/ThemeContext';

interface CardProps {
  children: ReactNode;
  style?: StyleProp<ViewStyle>;
  onPress?: () => void;
  variant?: 'default' | 'outlined' | 'elevated';
  padding?: 'none' | 'sm' | 'md' | 'lg';
}

export function Card({
  children,
  style,
  onPress,
  variant = 'default',
  padding = 'md',
}: CardProps) {
  const { colors, spacing, borderRadius, shadows } = useTheme();

  const getVariantStyle = () => {
    switch (variant) {
      case 'outlined':
        return {
          borderWidth: 1,
          borderColor: colors.border,
        };
      case 'elevated':
        return shadows.lg;
      default:
        return shadows.md;
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

  const cardStyles = [
    {
      backgroundColor: colors.cardBg,
      borderRadius: borderRadius.lg,
    },
    getVariantStyle(),
    getPaddingStyle(),
    style,
  ];

  if (onPress) {
    return (
      <TouchableOpacity
        style={cardStyles as StyleProp<ViewStyle>}
        onPress={onPress}
        activeOpacity={0.7}
      >
        {children}
      </TouchableOpacity>
    );
  }

  return <View style={cardStyles as StyleProp<ViewStyle>}>{children}</View>;
}

export default Card;
