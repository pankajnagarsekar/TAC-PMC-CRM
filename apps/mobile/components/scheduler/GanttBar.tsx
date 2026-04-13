// GanttBar — one row-level SVG bar per FlashList row
// Uses Reanimated animated props for zero-JS-thread bar repositioning on pan/pinch.

import React from 'react';
import Animated, { useAnimatedProps } from 'react-native-reanimated';
import type { SharedValue } from 'react-native-reanimated';
import { Svg, Rect } from 'react-native-svg';
import { getBarLeft, getBarWidth } from './scheduler-utils';
import { ROW_HEIGHT, CRITICAL_COLOR, BAR_COLOR_DEFAULT, STATUS_COLORS } from './scheduler-constants';
import { useTheme } from '../../contexts/ThemeContext';
import type { ScheduleTask } from '../../types/api';

// Create an animated version of Svg Rect for Reanimated animatedProps
const AnimatedRect = Animated.createAnimatedComponent(Rect);

interface GanttBarProps {
  task: ScheduleTask;
  dayWidth: SharedValue<number>;
  timelineStart: Date;
}

function GanttBarComponent({ task, dayWidth, timelineStart }: GanttBarProps) {
  // useTheme available for future enhancements (e.g., theme-aware bar colors)
  useTheme();

  // useAnimatedProps worklet: only reads dayWidth.value and closure-captured plain-JS values.
  // NEVER mutate JS state inside this worklet.
  const animatedProps = useAnimatedProps(() => {
    'worklet';
    const x = getBarLeft(task, dayWidth.value, timelineStart);
    const w = Math.max(2, getBarWidth(task, dayWidth.value));
    return { x, width: w };
  });

  // Use critical color if critical, else use status color, else default
  let fill = BAR_COLOR_DEFAULT;
  if (task.is_critical) {
    fill = CRITICAL_COLOR;
  } else if (task.status && STATUS_COLORS[task.status]) {
    fill = STATUS_COLORS[task.status];
  }

  return (
    <Svg height={ROW_HEIGHT} width="100%">
      <AnimatedRect
        y={8}
        height={24}
        rx={4}
        fill={fill}
        animatedProps={animatedProps}
      />
    </Svg>
  );
}

// Memoize: re-render only if task_id changes (dayWidth is a shared value — no re-render needed)
export const GanttBar = React.memo(GanttBarComponent, (prev, next) => {
  return prev.task.task_id === next.task.task_id;
});

export default GanttBar;
