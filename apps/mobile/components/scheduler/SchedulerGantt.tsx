// SchedulerGantt — interactive Gantt with pan + pinch gestures
// Pan: horizontal scroll of the timeline (activeOffsetX prevents hijacking vertical scroll)
// Pinch: zoom day width between DAY_WIDTH_MIN and DAY_WIDTH_MAX
//
// CRITICAL gesture pattern (pitfall from research):
//   - activeOffsetX([-10, 10]) + failOffsetY([-10, 10]) prevent the pan gesture from
//     stealing vertical scroll when the user swipes vertically (pitfall 3 in research).
//   - GestureDetector wraps the OUTER container — NOT placed inside FlashList renderItem.
//
// SVG strategy (pitfall 2 from research):
//   - One SVG per FlashList row (GanttBar) — NOT one giant SVG for all tasks.
//   - Row-level virtualization keeps render count bounded regardless of task count.

import React, { useMemo } from 'react';
import { View } from 'react-native';
import Animated, { useSharedValue, useAnimatedStyle } from 'react-native-reanimated';
import { Gesture, GestureDetector } from 'react-native-gesture-handler';
import { FlashList } from '@shopify/flash-list';
import type { ScheduleTask } from '../../types/api';
import { buildTimelineRange } from './scheduler-utils';
import { DAY_WIDTH_INITIAL, DAY_WIDTH_MIN, DAY_WIDTH_MAX, ROW_HEIGHT } from './scheduler-constants';
import { GanttBar } from './GanttBar';
import { GanttTimelineHeader } from './GanttTimelineHeader';
import { useTheme } from '../../contexts/ThemeContext';

interface SchedulerGanttProps {
  tasks: ScheduleTask[];
  projectStart: string | null;
}

export function SchedulerGantt({ tasks }: SchedulerGanttProps) {
  const { colors } = useTheme();
  const scrollX = useSharedValue(0);
  // dayWidth clamped between DAY_WIDTH_MIN (8px) and DAY_WIDTH_MAX (80px) — see research pitfall 3
  const dayWidth = useSharedValue(DAY_WIDTH_INITIAL);

  const timeline = useMemo(() => buildTimelineRange(tasks), [tasks]);

  // Pan gesture: horizontal scroll.
  // activeOffsetX([-10, 10]) + failOffsetY([-10, 10]) MUST be set to avoid stealing vertical scroll.
  const pan = Gesture.Pan()
    .activeOffsetX([-10, 10])
    .failOffsetY([-10, 10])
    .onChange((e) => {
      'worklet';
      scrollX.value = scrollX.value + e.changeX;
    });

  // Pinch gesture: zoom day width (clamped between DAY_WIDTH_MIN and DAY_WIDTH_MAX)
  const pinch = Gesture.Pinch().onChange((e) => {
    'worklet';
    const next = dayWidth.value * e.scaleChange;
    dayWidth.value = Math.min(DAY_WIDTH_MAX, Math.max(DAY_WIDTH_MIN, next));
  });

  const composed = Gesture.Simultaneous(pan, pinch);

  const bodyAnimatedStyle = useAnimatedStyle(() => ({
    transform: [{ translateX: scrollX.value }],
    width: timeline.dayCount * dayWidth.value,
  }));

  return (
    <View style={{ flex: 1, backgroundColor: colors.background }}>
      {/* Sticky timeline header — scrolls in sync with body via scrollX */}
      <GanttTimelineHeader
        timeline={timeline}
        dayWidth={dayWidth}
        scrollX={scrollX}
      />

      {/* Body: GestureDetector wraps the full list (NOT inside renderItem) */}
      <GestureDetector gesture={composed}>
        <Animated.View style={[{ flex: 1 }, bodyAnimatedStyle]}>
          <FlashList
            data={tasks}
            keyExtractor={(item) => item.task_id}
            renderItem={({ item }) => (
              <GanttBar
                task={item}
                dayWidth={dayWidth}
                timelineStart={timeline.start}
                dayCount={timeline.dayCount}
              />
            )}
            // @ts-expect-error - estimatedItemSize is required by FlashList but types may be out of sync
            estimatedItemSize={ROW_HEIGHT}
          />
        </Animated.View>
      </GestureDetector>
    </View>
  );
}

export default SchedulerGantt;
