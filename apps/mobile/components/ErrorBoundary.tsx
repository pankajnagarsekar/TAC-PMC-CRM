// ERROR BOUNDARY COMPONENT
// Catches unhandled errors and prevents app crashes with white screen

import React, { Component, ReactNode, ErrorInfo } from 'react';
import { View, Text, StyleSheet, ScrollView, Pressable } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Colors, Spacing, FontSizes } from '../constants/theme';

interface Props {
  children: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  fallbackComponent?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

/**
 * ErrorBoundary catches JavaScript errors in component tree and displays fallback UI
 * Prevents entire app from crashing with white screen of death
 */
export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error('[ErrorBoundary] Caught error:', error);
    console.error('[ErrorBoundary] Error Info:', errorInfo.componentStack);

    this.setState({
      error,
      errorInfo,
    });

    // Call optional error handler (e.g., for error reporting service)
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }
  }

  resetError = (): void => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  render(): ReactNode {
    if (this.state.hasError) {
      // Custom fallback component if provided
      if (this.props.fallbackComponent) {
        return this.props.fallbackComponent;
      }

      // Default error UI
      return (
        <SafeAreaView style={styles.container}>
          <ScrollView contentContainerStyle={styles.scrollContent}>
            <View style={styles.errorContainer}>
              <Text style={styles.errorTitle}>Something went wrong</Text>
              <Text style={styles.errorMessage}>
                The app encountered an unexpected error. Please try again.
              </Text>

              {__DEV__ && this.state.error && (
                <>
                  <View style={styles.devSection}>
                    <Text style={styles.devLabel}>Error Details (Dev Only)</Text>
                    <Text style={styles.errorCode}>{this.state.error.toString()}</Text>
                    {this.state.errorInfo?.componentStack && (
                      <Text style={styles.stackTrace}>
                        {this.state.errorInfo.componentStack}
                      </Text>
                    )}
                  </View>
                </>
              )}

              <Pressable
                style={styles.resetButton}
                onPress={this.resetError}
                accessibilityRole="button"
                accessibilityLabel="Try again"
              >
                <Text style={styles.resetButtonText}>Try Again</Text>
              </Pressable>
            </View>
          </ScrollView>
        </SafeAreaView>
      );
    }

    return this.props.children;
  }
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.white,
  },
  scrollContent: {
    flexGrow: 1,
    justifyContent: 'center',
    padding: Spacing.lg,
  },
  errorContainer: {
    alignItems: 'center',
    gap: Spacing.md,
  },
  errorTitle: {
    fontSize: FontSizes.xl,
    fontWeight: '700',
    color: Colors.primary,
    marginBottom: Spacing.sm,
    textAlign: 'center',
  },
  errorMessage: {
    fontSize: FontSizes.md,
    color: Colors.secondary,
    textAlign: 'center',
    marginBottom: Spacing.md,
    lineHeight: 24,
  },
  devSection: {
    width: '100%',
    backgroundColor: Colors.background,
    borderRadius: 8,
    padding: Spacing.md,
    marginBottom: Spacing.md,
    borderLeftWidth: 4,
    borderLeftColor: Colors.error,
  },
  devLabel: {
    fontSize: FontSizes.sm,
    fontWeight: '700',
    color: Colors.error,
    marginBottom: Spacing.sm,
  },
  errorCode: {
    fontSize: FontSizes.xs,
    color: Colors.secondary,
    fontFamily: 'monospace',
    marginBottom: Spacing.sm,
  },
  stackTrace: {
    fontSize: FontSizes.xs,
    color: Colors.secondary,
    fontFamily: 'monospace',
    lineHeight: 16,
  },
  resetButton: {
    paddingHorizontal: Spacing.xl,
    paddingVertical: Spacing.md,
    backgroundColor: Colors.primary,
    borderRadius: 8,
    minWidth: 200,
  },
  resetButtonText: {
    color: Colors.white,
    fontWeight: '600',
    textAlign: 'center',
    fontSize: FontSizes.md,
  },
});

export default ErrorBoundary;
