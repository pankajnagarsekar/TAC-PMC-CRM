// GanttBar — one row-level SVG bar per FlashList row
// Uses Reanimated animated props for zero-JS-thread bar repositioning on pan/pinch.

import React, { useMemo } from 'react';
import { View } from 'react-native';
import Animated, { useAnimatedProps } from 'react-native-reanimated';
import type { SharedValue } from 'react-native-reanimated';
import { Svg, Rect, Text, Line } from 'react-native-svg';
import { getBarLeft, getBarWidth } from './scheduler-utils';
import { 
  ROW_HEIGHT, 
  CRITICAL_COLOR, 
  BAR_COLOR_DEFAULT, 
  STATUS_COLORS,
  GRID_LINE_COLOR,
  LABEL_COLOR 
} from './scheduler-constants';
import { useTheme } from '../../contexts/ThemeContext';
import type { ScheduleTask } from '../../types/api';

const AnimatedRect = Animated.createAnimatedComponent(Rect);
const AnimatedText = Animated.createAnimatedComponent(Text);
const AnimatedLine = Animated.createAnimatedComponent(Line);

interface GanttBarProps {
  task: ScheduleTask;
  dayWidth: SharedValue<number>;
  timelineStart: Date;
  dayCount: number;
}

function GanttBarComponent({ task, dayWidth, timelineStart, dayCount }: GanttBarProps) {
  const { colors } = useTheme();

  // Bar dimensions and position
  const animatedRectProps = useAnimatedProps(() => {
    'worklet';
    const x = getBarLeft(task, dayWidth.value, timelineStart);
    const w = Math.max(2, getBarWidth(task, dayWidth.value));
    return { x, width: w };
  });

  // Label position (right of the bar)
  const animatedTextProps = useAnimatedProps(() => {
    'worklet';
    const x = getBarLeft(task, dayWidth.value, timelineStart);
    const w = Math.max(2, getBarWidth(task, dayWidth.value));
    // Fade out text if too zoomed out (labels would overlap/clutter)
    const opacity = dayWidth.value > 15 ? 1 : 0;
    return { x: x + w + 12, opacity };
  });

  // Vertical grid lines (every 7 days)
  const gridTicks = useMemo(() => {
    const ticks = [];
    for (let i = 0; i <= dayCount; i += 7) {
      ticks.push(i);
    }
    return ticks;
  }, [dayCount]);

  // Use critical color if critical, else use status color, else default
  let fill = BAR_COLOR_DEFAULT;
  if (task.is_critical) {
    fill = CRITICAL_COLOR;
  } else if (task.status && STATUS_COLORS[task.status]) {
    fill = STATUS_COLORS[task.status];
  }

  return (
    <View style={{ height: ROW_HEIGHT, borderBottomWidth: 1, borderBottomColor: 'rgba(255,255,255,0.03)' }}>
      <Svg height={ROW_HEIGHT} width="100%">
        {/* Vertical Grid Lines */}
        {gridTicks.map((tick) => (
            <GridLine key={tick} dayIndex={tick} dayWidth={dayWidth} height={ROW_HEIGHT} />
        ))}

        <AnimatedRect
          y={12}
          height={24}
          rx={6}
          fill={fill}
          animatedProps={animatedRectProps}
        />
        
        <AnimatedText
          y={28}
          fill={colors.text || LABEL_COLOR}
          fontSize={12}
          fontWeight="600"
          letterSpacing={0.5}
          animatedProps={animatedTextProps}
        >
          {task.task_name}
        </AnimatedText>
      </Svg>
    </View>
  );
}

/**
 * Isolated GridLine component to minimize re-renders and isolate animation logic
 */
function GridLine({ dayIndex, dayWidth, height }: { dayIndex: number; dayWidth: SharedValue<number>; height: number }) {
    const animatedProps = useAnimatedProps(() => {
        'worklet';
        const x = dayIndex * dayWidth.value;
        return { x1: x, x2: x };
    });

    return (
        <AnimatedLine
            y1={0}
            y2={height}
            stroke={GRID_LINE_COLOR}
            strokeWidth={1}
            animatedProps={animatedProps}
        />
    );
}

// Memoize: re-render only if task_id or dayCount changes
export const GanttBar = React.memo(GanttBarComponent, (prev, next) => {
  return prev.task.task_id === next.task.task_id && prev.dayCount === next.dayCount;
});

export default GanttBar;
