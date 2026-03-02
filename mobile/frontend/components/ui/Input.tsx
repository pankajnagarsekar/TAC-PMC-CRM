// INPUT COMPONENT
// Reusable text input with label and error states

import React, { useState } from 'react';
import {
  View,
  TextInput,
  Text,
  StyleSheet,
  TouchableOpacity,
  TextInputProps,
  ViewStyle,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../contexts/ThemeContext';

interface InputProps extends TextInputProps {
  label?: string;
  error?: string;
  hint?: string;
  leftIcon?: keyof typeof Ionicons.glyphMap;
  rightIcon?: keyof typeof Ionicons.glyphMap;
  onRightIconPress?: () => void;
  containerStyle?: ViewStyle;
}

export function Input({
  label,
  error,
  hint,
  leftIcon,
  rightIcon,
  onRightIconPress,
  containerStyle,
  secureTextEntry,
  style,
  ...props
}: InputProps) {
  const { colors: Colors, spacing: Spacing, fontSizes: FontSizes, borderRadius: BorderRadius } = useTheme();
  const [isFocused, setIsFocused] = useState(false);
  const [isSecure, setIsSecure] = useState(secureTextEntry);

  const dynamicStyles = getStyles(Colors, Spacing, FontSizes, BorderRadius);

  const inputContainerStyles = [
    dynamicStyles.inputContainer,
    isFocused && dynamicStyles.inputContainerFocused,
    error && dynamicStyles.inputContainerError,
  ];

  return (
    <View style={[dynamicStyles.container, containerStyle]}>
      {label && <Text style={dynamicStyles.label}>{label}</Text>}
      
      <View style={inputContainerStyles}>
        {leftIcon && (
          <Ionicons
            name={leftIcon}
            size={20}
            color={isFocused ? Colors.primary : Colors.textMuted}
            style={dynamicStyles.leftIcon}
          />
        )}
        
        <TextInput
          style={[
            dynamicStyles.input,
            leftIcon && dynamicStyles.inputWithLeftIcon,
            (rightIcon || secureTextEntry) && dynamicStyles.inputWithRightIcon,
            style,
          ]}
          placeholderTextColor={Colors.placeholder}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          secureTextEntry={isSecure}
          {...props}
        />
        
        {secureTextEntry ? (
          <TouchableOpacity
            onPress={() => setIsSecure(!isSecure)}
            style={dynamicStyles.rightIcon}
          >
            <Ionicons
              name={isSecure ? 'eye-outline' : 'eye-off-outline'}
              size={20}
              color={Colors.textMuted}
            />
          </TouchableOpacity>
        ) : rightIcon ? (
          <TouchableOpacity
            onPress={onRightIconPress}
            style={dynamicStyles.rightIcon}
            disabled={!onRightIconPress}
          >
            <Ionicons
              name={rightIcon}
              size={20}
              color={Colors.textMuted}
            />
          </TouchableOpacity>
        ) : null}
      </View>
      
      {error && <Text style={dynamicStyles.error}>{error}</Text>}
      {hint && !error && <Text style={dynamicStyles.hint}>{hint}</Text>}
    </View>
  );
}

const getStyles = (Colors: any, Spacing: any, FontSizes: any, BorderRadius: any) => StyleSheet.create({
  container: {
    marginBottom: Spacing.md,
  },
  label: {
    fontSize: FontSizes.sm,
    fontWeight: '600',
    color: Colors.text,
    marginBottom: Spacing.xs,
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.inputBg,
    borderWidth: 1,
    borderColor: Colors.inputBorder,
    borderRadius: BorderRadius.md,
    minHeight: 48,
  },
  inputContainerFocused: {
    borderColor: Colors.primary,
    backgroundColor: Colors.isDark ? Colors.surface : Colors.white,
  },
  inputContainerError: {
    borderColor: Colors.error,
  },
  input: {
    flex: 1,
    fontSize: FontSizes.md,
    color: Colors.text,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.sm,
  },
  inputWithLeftIcon: {
    paddingLeft: Spacing.xs,
  },
  inputWithRightIcon: {
    paddingRight: Spacing.xs,
  },
  leftIcon: {
    marginLeft: Spacing.md,
  },
  rightIcon: {
    padding: Spacing.sm,
    marginRight: Spacing.xs,
  },
  error: {
    fontSize: FontSizes.xs,
    color: Colors.error,
    marginTop: Spacing.xs,
  },
  hint: {
    fontSize: FontSizes.xs,
    color: Colors.textMuted,
    marginTop: Spacing.xs,
  },
});

export default Input;
