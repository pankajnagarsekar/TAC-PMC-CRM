// GanttBar — one row-level SVG bar per FlashList row
// Uses Reanimated animated props for zero-JS-thread bar repositioning on pan/pinch.

import React from 'react';
import Animated, { useAnimatedProps } from 'react-native-reanimated';
import type { SharedValue } from 'react-native-reanimated';
import { Svg, Rect } from 'react-native-svg';
import { getBarLeft, getBarWidth } from './scheduler-utils';
import { ROW_HEIGHT, CRITICAL_COLOR, BAR_COLOR_DEFAULT } from './scheduler-constants';
import type { ScheduleTask } from '../../types/api';

// Create an animated version of Svg Rect for Reanimated animatedProps
const AnimatedRect = Animated.createAnimatedComponent(Rect);

interface GanttBarProps {
  task: ScheduleTask;
  dayWidth: SharedValue<number>;
  timelineStart: Date;
}

function GanttBarComponent({ task, dayWidth, timelineStart }: GanttBarProps) {
  // useAnimatedProps worklet: only reads dayWidth.value and closure-captured plain-JS values.
  // NEVER mutate JS state inside this worklet.
  const animatedProps = useAnimatedProps(() => {
    'worklet';
    const x = getBarLeft(task, dayWidth.value, timelineStart);
    const w = Math.max(2, getBarWidth(task, dayWidth.value));
    return { x, width: w };
  });

  const fill = task.is_critical ? CRITICAL_COLOR : BAR_COLOR_DEFAULT;

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
