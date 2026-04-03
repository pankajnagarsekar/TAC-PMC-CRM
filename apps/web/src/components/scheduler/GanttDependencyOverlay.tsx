"use client";

import React, { memo, useMemo } from "react";

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
  // Dependency types are expressed as predecessor relationship:
  // FS means predecessor Finish -> successor Start, etc.
  if (side === "from") {
    return type === "FS" || type === "FF" ? "finish" : "start";
  }
  return type === "FS" || type === "SS" ? "start" : "finish";
}

function anchorX(node: GanttDependencyNode, anchor: "start" | "finish") {
  return anchor === "start" ? node.left : node.left + node.width;
}

function buildElbowPath(x1: number, y1: number, x2: number, y2: number) {
  const pad = 10;
  const dir = x2 >= x1 ? 1 : -1;
  const viaX = x1 + dir * pad;
  return `M ${x1} ${y1} H ${viaX} V ${y2} H ${x2}`;
}

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

      return [
        {
          key: `${edge.fromTaskId}-${edge.toTaskId}-${edge.type}-${edge.lagDays ?? 0}`,
          d: buildElbowPath(x1, y1, x2, y2),
          isCritical: edge.isCritical ?? false,
        },
      ];
    });
  }, [edges, nodes, rowHeight]);

  if (edges.length === 0) return null;

  return (
    <svg
      aria-hidden="true"
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className="block"
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
      </defs>

      {paths.map((path) => (
        <path
          key={path.key}
          d={path.d}
          fill="none"
          stroke="currentColor"
          strokeWidth={1.25}
          markerEnd="url(#gantt-dep-arrow)"
          className={path.isCritical ? "text-rose-500/40 dark:text-rose-300/40" : "text-slate-400/40 dark:text-white/20"}
        />
      ))}
    </svg>
  );
});

