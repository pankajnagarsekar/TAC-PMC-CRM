// GanttTimelineHeader — sticky header with day/week tick SVG
// Uses Reanimated animated style for synchronized horizontal scroll with the Gantt body.

import React from 'react';
import Animated, { useAnimatedStyle } from 'react-native-reanimated';
import type { SharedValue } from 'react-native-reanimated';
import { Svg, Line, Text as SvgText } from 'react-native-svg';
import { format, addDays } from 'date-fns';
import { DAY_WIDTH_MAX, HEADER_HEIGHT } from './scheduler-constants';
import { useTheme } from '../../contexts/ThemeContext';

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
  }));

  // Render tick marks every 7 days for clarity at all zoom levels
  const ticks: { dayIndex: number; label: string }[] = [];
  for (let i = 0; i < timeline.dayCount; i += 7) {
    const date = addDays(timeline.start, i);
    // Tick x position scales with dayWidth
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
        <Svg height={HEADER_HEIGHT}>
          {ticks.map(({ dayIndex, label }) => (
            <React.Fragment key={dayIndex}>
              <Line
                x1={dayIndex * dayWidth.value}
                y1={0}
                x2={dayIndex * dayWidth.value}
                y2={HEADER_HEIGHT}
                stroke={colors.border}
                strokeWidth={1}
              />
              <SvgText
                x={dayIndex * dayWidth.value + 2}
                y={HEADER_HEIGHT - 8}
                fill={colors.textSecondary}
                fontSize={10}
              >
                {label}
              </SvgText>
            </React.Fragment>
          ))}
        </Svg>
      </Animated.View>
    </Animated.View>
  );
}

export default GanttTimelineHeader;
