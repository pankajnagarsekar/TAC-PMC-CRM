// GanttTimelineHeader — sticky header with day/week tick SVG
// Uses Reanimated animated props for synchronized horizontal scroll and zoom.

import React from 'react';
import Animated, { useAnimatedStyle, useAnimatedProps } from 'react-native-reanimated';
import type { SharedValue } from 'react-native-reanimated';
import { Svg, Line, Text as SvgText } from 'react-native-svg';
import { format, addDays } from 'date-fns';
import { HEADER_HEIGHT } from './scheduler-constants';
import { useTheme } from '../../contexts/ThemeContext';

const AnimatedLine = Animated.createAnimatedComponent(Line);
const AnimatedSvgText = Animated.createAnimatedComponent(SvgText);

interface TimelineRange {
  start: Date;
  end: Date;
  dayCount: number;
}

interface GanttTimelineHeaderProps {
  timeline: TimelineRange;
  dayWidth: SharedValue<number>;
  scrollX: SharedValue<number>;
}

export function GanttTimelineHeader({ timeline, dayWidth, scrollX }: GanttTimelineHeaderProps) {
  const { colors } = useTheme();

  // Compute SVG width dynamically based on dayWidth (responsive to pinch zoom)
  const animatedWidthStyle = useAnimatedStyle(() => ({
    width: timeline.dayCount * dayWidth.value,
  }));

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ translateX: scrollX.value }],
    width: timeline.dayCount * dayWidth.value,
  }));

  // Render tick marks every 7 days for clarity at all zoom levels
  const ticks: { dayIndex: number; label: string }[] = [];
  for (let i = 0; i < timeline.dayCount; i += 7) {
    const date = addDays(timeline.start, i);
    ticks.push({ dayIndex: i, label: format(date, 'dd MMM') });
  }

  return (
    <Animated.View
      style={[
        {
          height: HEADER_HEIGHT,
          backgroundColor: colors.surface,
          borderBottomWidth: 1,
          borderBottomColor: colors.border,
        },
        animatedStyle,
      ]}
    >
      <Animated.View style={[{ height: HEADER_HEIGHT }, animatedWidthStyle]}>
        <Svg height={HEADER_HEIGHT} width="100%">
          {ticks.map(({ dayIndex, label }) => (
            <Tick 
                key={dayIndex} 
                dayIndex={dayIndex} 
                label={label} 
                dayWidth={dayWidth} 
                colors={colors} 
            />
          ))}
        </Svg>
      </Animated.View>
    </Animated.View>
  );
}

/**
 * Sub-component for a single tick to isolate animated props
 */
function Tick({ 
    dayIndex, 
    label, 
    dayWidth, 
    colors 
}: { 
    dayIndex: number; 
    label: string; 
    dayWidth: SharedValue<number>; 
    colors: any;
}) {
    const lineProps = useAnimatedProps(() => ({
        x1: dayIndex * dayWidth.value,
        x2: dayIndex * dayWidth.value,
    }));

    const textProps = useAnimatedProps(() => ({
        x: dayIndex * dayWidth.value + 2,
    }));

    return (
        <React.Fragment>
            <AnimatedLine
                y1={0}
                y2={HEADER_HEIGHT}
                stroke={colors.border}
                strokeWidth={1}
                animatedProps={lineProps}
            />
            <AnimatedSvgText
                y={HEADER_HEIGHT - 8}
                fill={colors.textSecondary}
                fontSize={10}
                animatedProps={textProps}
            >
                {label}
            </AnimatedSvgText>
        </React.Fragment>
    );
}

export default GanttTimelineHeader;
