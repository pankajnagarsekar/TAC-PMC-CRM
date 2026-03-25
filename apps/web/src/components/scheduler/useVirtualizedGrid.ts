"use client";

import * as React from "react";

type Overscan = {
  before: number;
  after: number;
};

export type VirtualizedGridRange = {
  startIndex: number;
  endIndex: number;
  topSpacer: number;
  bottomSpacer: number;
  viewportHeight: number;
};

export type UseVirtualizedGridArgs = {
  itemCount: number;
  rowHeight: number;
  overscan?: Overscan;
  estimatedViewportHeight?: number;
};

const DEFAULT_OVERSCAN: Overscan = { before: 4, after: 4 };

export function useVirtualizedGrid<TElement extends HTMLElement = HTMLDivElement>({
  itemCount,
  rowHeight,
  overscan = DEFAULT_OVERSCAN,
  estimatedViewportHeight = 480,
}: UseVirtualizedGridArgs) {
  const viewportRef = React.useRef<TElement | null>(null);
  const [scrollTop, setScrollTop] = React.useState(0);
  const [viewportHeight, setViewportHeight] = React.useState(estimatedViewportHeight);

  React.useEffect(() => {
    const el = viewportRef.current;
    if (!el) return;

    const update = () => {
      setViewportHeight(el.clientHeight || estimatedViewportHeight);
    };

    update();

    if (typeof ResizeObserver === "undefined") {
      window.addEventListener("resize", update);
      return () => window.removeEventListener("resize", update);
    }

    const observer = new ResizeObserver(update);
    observer.observe(el);
    return () => observer.disconnect();
  }, [estimatedViewportHeight]);

  const onScroll = React.useCallback((event: React.UIEvent<TElement>) => {
    setScrollTop(event.currentTarget.scrollTop);
  }, []);

  const range: VirtualizedGridRange = React.useMemo(() => {
    const before = Math.max(0, overscan.before);
    const after = Math.max(0, overscan.after);
    const baseVisible = Math.ceil(viewportHeight / rowHeight);
    const visibleCount = baseVisible + before + after;

    const startIndex = Math.max(0, Math.floor(scrollTop / rowHeight) - before);
    const endIndex = Math.min(itemCount, startIndex + visibleCount);

    const topSpacer = startIndex * rowHeight;
    const bottomSpacer = Math.max(0, (itemCount - endIndex) * rowHeight);

    return {
      startIndex,
      endIndex,
      topSpacer,
      bottomSpacer,
      viewportHeight,
    };
  }, [itemCount, overscan.after, overscan.before, rowHeight, scrollTop, viewportHeight]);

  return {
    viewportRef,
    onScroll,
    ...range,
  };
}

