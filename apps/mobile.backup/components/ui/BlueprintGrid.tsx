import React from 'react';
import { View, StyleSheet, ImageBackground, Dimensions } from 'react-native';
import { useTheme } from '../../contexts/ThemeContext';

const { width, height } = Dimensions.get('window');

/**
 * A subtle architectural drafting grid background component.
 * Provides a 'Blueprint Atelier' technical floor for the UI.
 */
export function BlueprintGrid({ children }: { children: React.ReactNode }) {
    const { isDark } = useTheme();

    return (
        <View style={styles.container}>
            <ImageBackground
                // Using a placeholder or a very light pattern if the asset isn't ready
                // but ideally we'd use the generated asset.
                // For now, I'll use a style-based grid to ensure it works immediately.
                source={undefined}
                resizeMode="repeat"
                style={styles.gridImage}
            >
                {/* Procedural Grid Overlay: Strictly Subtle */}
                <View style={[styles.gridOverlay, { opacity: isDark ? 0.03 : 0.015 }]} pointerEvents="none">
                    {/* Vertical Lines */}
                    {Array.from({ length: Math.ceil(width / 20) }).map((_, i) => (
                        <View key={`v-${i}`} style={[styles.line, { left: i * 20, width: 1, height: '100%', backgroundColor: '#505f7a' }]} />
                    ))}
                    {/* Horizontal Lines */}
                    {Array.from({ length: Math.ceil(height / 20) }).map((_, i) => (
                        <View key={`h-${i}`} style={[styles.line, { top: i * 20, width: '100%', height: 1, backgroundColor: '#505f7a' }]} />
                    ))}
                </View>
                {children}
            </ImageBackground>
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
    },
    gridImage: {
        flex: 1,
    },
    gridOverlay: {
        ...StyleSheet.absoluteFillObject,
        flexDirection: 'row',
    },
    line: {
        position: 'absolute',
    }
});
