"use client";

import React, { memo, useEffect, useMemo } from "react";
import { useScheduleStore } from "@/store/useScheduleStore";
import type { DependencyType } from "@/types/schedule.types";

export type GanttDependencyEdge = {
  fromTaskId: string;
  toTaskId: string;
  type: DependencyType;
  lagDays?: number;
  isCritical?: boolean;
};

export type GanttDependencyNode = {
  taskId: string;
  rowIndex: number;
  left: number;
  width: number;
};

function anchorFor(type: DependencyType, side: "from" | "to") {
  if (side === "from") {
    return type === "FS" || type === "FF" ? "finish" : "start";
  }
  return type === "FS" || type === "SS" ? "start" : "finish";
}

function anchorX(node: GanttDependencyNode, anchor: "start" | "finish") {
  return anchor === "start" ? node.left : node.left + node.width;
}

/**
 * Renders MS Project-style orthogonal right-angle paths between task bars.
 */
function buildOrthogonalPath(
  x1: number,
  y1: number,
  x2: number,
  y2: number,
  fromAnchor: "start" | "finish",
  toAnchor: "start" | "finish"
) {
  const buffer = 16;
  const points: [number, number][] = [[x1, y1]];

  if (fromAnchor === "finish" && toAnchor === "start") {
    // FS dependency
    const midX = x1 + buffer;
    if (x2 >= x1 + 2 * buffer) {
      points.push([midX, y1]);
      points.push([midX, y2]);
    } else {
      const midY = y1 + (y2 - y1) / 2;
      points.push([midX, y1]);
      points.push([midX, midY]);
      points.push([x2 - buffer, midY]);
      points.push([x2 - buffer, y2]);
    }
    points.push([x2, y2]);
  } else if (fromAnchor === "start" && toAnchor === "start") {
    // SS dependency
    const minX = Math.min(x1, x2) - buffer;
    points.push([x1 - buffer, y1]);
    points.push([minX, y1]);
    points.push([minX, y2]);
    points.push([x2, y2]);
  } else if (fromAnchor === "finish" && toAnchor === "finish") {
    // FF dependency
    const maxX = Math.max(x1, x2) + buffer;
    points.push([x1 + buffer, y1]);
    points.push([maxX, y1]);
    points.push([maxX, y2]);
    points.push([x2, y2]);
  } else {
    // SF dependency
    const midX = x1 - buffer;
    if (x2 <= x1 - 2 * buffer) {
      points.push([midX, y1]);
      points.push([midX, y2]);
    } else {
      const midY = y1 + (y2 - y1) / 2;
      points.push([midX, y1]);
      points.push([midX, midY]);
      points.push([x2 + buffer, midY]);
      points.push([x2 + buffer, y2]);
    }
    points.push([x2, y2]);
  }

  return points.map((p, idx) => `${idx === 0 ? "M" : "L"} ${p[0]} ${p[1]}`).join(" ");
}

function getStrokeDashArray(type: DependencyType, isCycle: boolean) {
  if (isCycle) return "4 4";
  switch (type) {
    case "SS": return "6 3";
    case "FF": return "2 3";
    case "SF": return "10 3 2 3";
    case "FS":
    default: return "none";
  }
}

const checkIsCycle = (
  fromId: string,
  toId: string,
  dependencyGraph: Record<string, { predecessors: string[]; successors: string[] }>
): boolean => {
  const visited = new Set<string>();
  const queue = [toId];
  while (queue.length > 0) {
    const curr = queue.shift()!;
    if (curr === fromId) return true;
    const succs = dependencyGraph[curr]?.successors || [];
    succs.forEach((s) => {
      if (!visited.has(s)) {
        visited.add(s);
        queue.push(s);
      }
    });
  }
  return false;
};

export const GanttDependencyOverlay = memo(function GanttDependencyOverlay({
  nodes,
  edges,
  rowHeight,
  width,
  height,
}: {
  nodes: Map<string, GanttDependencyNode>;
  edges: GanttDependencyEdge[];
  rowHeight: number;
  width: number;
  height: number;
}) {
  const selectedTasks = useScheduleStore((state) => state.selectedTasks);
  const highlightedDependencyChain = useScheduleStore((state) => state.highlightedDependencyChain);
  const setHighlightedDependencyChain = useScheduleStore((state) => state.setHighlightedDependencyChain);
  const getDependencyChain = useScheduleStore((state) => state.getDependencyChain);
  const dependencyGraph = useScheduleStore((state) => state.dependencyGraph);

  // Auto-highlight selected task's predecessors and successors
  const firstSelected = [...selectedTasks][0];
  useEffect(() => {
    if (firstSelected) {
      const chain = getDependencyChain(firstSelected, "both");
      const highlightSet = new Set(chain);
      highlightSet.add(firstSelected);
      setHighlightedDependencyChain(highlightSet);
    } else {
      setHighlightedDependencyChain(new Set());
    }
  }, [firstSelected, getDependencyChain, setHighlightedDependencyChain]);

  const handleMouseEnterPath = (fromId: string, toId: string) => {
    const chainFrom = getDependencyChain(fromId, "predecessors");
    const chainTo = getDependencyChain(toId, "successors");
    const highlightSet = new Set([...chainFrom, ...chainTo, fromId, toId]);
    setHighlightedDependencyChain(highlightSet);
  };

  const handleMouseLeavePath = () => {
    if (firstSelected) {
      const chain = getDependencyChain(firstSelected, "both");
      const highlightSet = new Set(chain);
      highlightSet.add(firstSelected);
      setHighlightedDependencyChain(highlightSet);
    } else {
      setHighlightedDependencyChain(new Set());
    }
  };

  const paths = useMemo(() => {
    return edges.flatMap((edge) => {
      const fromNode = nodes.get(edge.fromTaskId);
      const toNode = nodes.get(edge.toTaskId);
      if (!fromNode || !toNode) return [];

      const fromAnchor = anchorFor(edge.type, "from");
      const toAnchor = anchorFor(edge.type, "to");

      const x1 = anchorX(fromNode, fromAnchor);
      const x2 = anchorX(toNode, toAnchor);
      const y1 = fromNode.rowIndex * rowHeight + rowHeight / 2;
      const y2 = toNode.rowIndex * rowHeight + rowHeight / 2;

      const isCycle = checkIsCycle(edge.fromTaskId, edge.toTaskId, dependencyGraph);
      const isHighlighted = highlightedDependencyChain.has(edge.fromTaskId) && highlightedDependencyChain.has(edge.toTaskId);

      return [
        {
          key: `${edge.fromTaskId}-${edge.toTaskId}-${edge.type}-${edge.lagDays ?? 0}`,
          d: buildOrthogonalPath(x1, y1, x2, y2, fromAnchor, toAnchor),
          type: edge.type,
          isCritical: edge.isCritical ?? false,
          isCycle,
          isHighlighted,
          fromTaskId: edge.fromTaskId,
          toTaskId: edge.toTaskId,
        },
      ];
    });
  }, [edges, nodes, rowHeight, dependencyGraph, highlightedDependencyChain]);

  if (edges.length === 0) return null;

  return (
    <svg
      aria-hidden="true"
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className="block"
      style={{ pointerEvents: "none" }}
    >
      <defs>
        <marker
          id="gantt-dep-arrow"
          markerWidth="8"
          markerHeight="8"
          refX="6"
          refY="3"
          orient="auto"
        >
          <path d="M0,0 L6,3 L0,6 Z" fill="currentColor" />
        </marker>
        <marker
          id="gantt-dep-arrow-highlight"
          markerWidth="8"
          markerHeight="8"
          refX="6"
          refY="3"
          orient="auto"
        >
          <path d="M0,0 L6,3 L0,6 Z" fill="currentColor" />
        </marker>
        <marker
          id="gantt-dep-arrow-cycle"
          markerWidth="8"
          markerHeight="8"
          refX="6"
          refY="3"
          orient="auto"
        >
          <path d="M0,0 L6,3 L0,6 Z" fill="currentColor" />
        </marker>
      </defs>

      {paths.map((path) => {
        let strokeColor = "text-slate-400/30 dark:text-white/10";
        let markerId = "gantt-dep-arrow";
        let strokeWidth = 1.5;

        if (path.isCycle) {
          strokeColor = "text-rose-500 animate-pulse";
          markerId = "gantt-dep-arrow-cycle";
          strokeWidth = 2;
        } else if (path.isHighlighted) {
          strokeColor = "text-sky-500 dark:text-sky-400 drop-shadow-[0_0_3px_rgba(14,165,233,0.5)]";
          markerId = "gantt-dep-arrow-highlight";
          strokeWidth = 2.5;
        } else if (path.isCritical) {
          strokeColor = "text-rose-600 dark:text-rose-400 drop-shadow-[0_0_2px_rgba(225,29,72,0.4)]";
          strokeWidth = 2;
        }

        return (
          <path
            key={path.key}
            d={path.d}
            fill="none"
            stroke="currentColor"
            strokeWidth={strokeWidth}
            strokeDasharray={getStrokeDashArray(path.type, path.isCycle)}
            markerEnd={`url(#${markerId})`}
            className={`${strokeColor} cursor-pointer transition-all duration-200`}
            style={{ pointerEvents: "stroke" }}
            onMouseEnter={() => handleMouseEnterPath(path.fromTaskId, path.toTaskId)}
            onMouseLeave={handleMouseLeavePath}
          />
        );
      })}
    </svg>
  );
});
