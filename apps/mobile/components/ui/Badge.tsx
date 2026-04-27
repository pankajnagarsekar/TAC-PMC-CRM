import React from 'react';
import { View, Text, StyleSheet, ViewStyle, TextStyle } from 'react-native';
import { useTheme } from '../../contexts/ThemeContext';

interface BadgeProps {
  label: string;
  color?: string;
  variant?: 'solid' | 'outline';
  style?: ViewStyle;
  textStyle?: TextStyle;
  accessibilityLabel?: string;
  accessibilityHint?: string;
}

export const Badge = ({
  label,
  color,
  variant = 'solid',
  style,
  textStyle,
  accessibilityLabel,
  accessibilityHint,
}: BadgeProps) => {
  const { colors, spacing, borderRadius } = useTheme();

  const badgeColor = color || colors.primary;

  const containerStyle: ViewStyle[] = [
    styles.container,
    {
      borderRadius: borderRadius.full,
      paddingHorizontal: spacing.sm,
      paddingVertical: 2, // Extra small vertical padding
    },
    variant === 'solid'
      ? { backgroundColor: badgeColor }
      : { backgroundColor: 'transparent', borderWidth: 1, borderColor: badgeColor },
    style as ViewStyle,
  ];

  const labelStyle: TextStyle[] = [
    styles.label,
    {
      fontSize: 10, // Very small for badge
      color: variant === 'solid' ? '#FFFFFF' : badgeColor,
    },
    textStyle as TextStyle,
  ];

  return (
    <View
      style={containerStyle}
      accessible={true}
      accessibilityRole="text"
      accessibilityLabel={accessibilityLabel || `Badge: ${label}`}
      accessibilityHint={accessibilityHint}
    >
      <Text style={labelStyle}>{label ? label.toUpperCase() : ''}</Text>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    alignSelf: 'flex-start',
    justifyContent: 'center',
    alignItems: 'center',
    minWidth: 40,
  },
  label: {
    fontWeight: '800',
    textAlign: 'center',
  },
});

export default Badge;
