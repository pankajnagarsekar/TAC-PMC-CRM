// GanttTimelineHeader — sticky header with day/week tick SVG
// Uses Reanimated animated style for synchronized horizontal scroll with the Gantt body.

import React from 'react';
import Animated, { useAnimatedStyle } from 'react-native-reanimated';
import type { SharedValue } from 'react-native-reanimated';
import { Svg, Line, Text as SvgText } from 'react-native-svg';
import { format, addDays } from 'date-fns';
import { DAY_WIDTH_MAX, HEADER_HEIGHT } from './scheduler-constants';

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

export function GanttTimelineHeader({ timeline, scrollX }: GanttTimelineHeaderProps) {
  // SVG width is fixed at max possible width (dayCount * DAY_WIDTH_MAX) so we never
  // need to re-layout on zoom — bars shift, header shifts together.
  const svgWidth = timeline.dayCount * DAY_WIDTH_MAX;

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ translateX: scrollX.value }],
  }));

  // Render tick marks every 7 days for clarity at all zoom levels
  const ticks: { x: number; label: string }[] = [];
  for (let i = 0; i < timeline.dayCount; i += 7) {
    const date = addDays(timeline.start, i);
    const x = i * DAY_WIDTH_MAX;
    ticks.push({ x, label: format(date, 'dd MMM') });
  }

  return (
    <Animated.View
      style={[
        {
          height: HEADER_HEIGHT,
          backgroundColor: '#1e293b',
          borderBottomWidth: 1,
          borderBottomColor: '#334155',
        },
        animatedStyle,
      ]}
    >
      <Svg width={svgWidth} height={HEADER_HEIGHT}>
        {ticks.map(({ x, label }) => (
          <React.Fragment key={x}>
            <Line
              x1={x}
              y1={0}
              x2={x}
              y2={HEADER_HEIGHT}
              stroke="#475569"
              strokeWidth={1}
            />
            <SvgText
              x={x + 2}
              y={HEADER_HEIGHT - 8}
              fill="#94a3b8"
              fontSize={10}
            >
              {label}
            </SvgText>
          </React.Fragment>
        ))}
      </Svg>
    </Animated.View>
  );
}

export default GanttTimelineHeader;
