import React from 'react';
import { DragDropContext, Droppable, Draggable, DropResult } from '@hello-pangea/dnd';
import { useDashboardLayoutStore } from '@/store/useDashboardLayoutStore';
import { DashboardWidget } from './DashboardWidget';

// ──────────────────────────────────────────────────────────────────────────
// Dashboard Drag-and-Drop Grid
// Renders Zone 3 Operations Grid with full DnD capabilities (desktop only)
// ──────────────────────────────────────────────────────────────────────────

export interface WidgetDef {
  title: string;
  subtitle?: string;
  icon: React.ReactNode;
  content: React.ReactNode;
  headerAction?: React.ReactNode;
  minHeight?: string;
  maxHeight?: string;
}

interface DashboardDndGridProps {
  projectId: string;
  widgets: Record<string, WidgetDef>;
}

const subscribe = (callback: () => void) => {
  if (typeof window === 'undefined') return () => {};
  window.addEventListener('resize', callback);
  return () => window.removeEventListener('resize', callback);
};

const getSnapshot = () => {
  if (typeof window === 'undefined') return false;
  return window.innerWidth >= 1024;
};

const getServerSnapshot = () => false;

export function DashboardDndGrid({ projectId, widgets }: DashboardDndGridProps) {
  const { layouts, reorderWidgets, loadProjectLayout, _hasHydrated } = useDashboardLayoutStore();
  const isDesktop = React.useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  React.useEffect(() => {
    if (projectId) {
      loadProjectLayout(projectId);
    }
  }, [projectId, loadProjectLayout]);

  const key = projectId || 'global';
  const layout = layouts[key] || [];

  // Renders static layout for SSR, mobile/tablet, or during hydration
  const renderStaticLayout = () => {
    return (
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-[var(--dashboard-gap)]">
        {layout.map((config) => {
          const w = widgets[config.id];
          if (!w) return null;
          return (
            <div
              key={config.id}
              className={config.colSpan === 2 ? "col-span-1 lg:col-span-2" : "col-span-1"}
            >
              <DashboardWidget
                id={config.id}
                title={w.title}
                subtitle={w.subtitle}
                icon={w.icon}
                colSpan={config.colSpan}
                minHeight={w.minHeight}
                maxHeight={w.maxHeight}
                headerAction={w.headerAction}
              >
                {w.content}
              </DashboardWidget>
            </div>
          );
        })}
      </div>
    );
  };

  if (!_hasHydrated || layout.length === 0) {
    return renderStaticLayout();
  }

  // Mobile/Tablet views do not support DnD interaction per §5
  if (!isDesktop) {
    return renderStaticLayout();
  }

  const onDragEnd = (result: DropResult) => {
    if (!result.destination) return;
    if (result.destination.index === result.source.index) return;
    reorderWidgets(projectId, result.source.index, result.destination.index);
  };

  return (
    <DragDropContext onDragEnd={onDragEnd}>
      <Droppable droppableId="dashboard-grid" direction="vertical">
        {(provided) => (
          <div
            ref={provided.innerRef}
            {...provided.droppableProps}
            className="grid grid-cols-1 lg:grid-cols-2 gap-[var(--dashboard-gap)] relative"
          >
            {layout.map((config, index) => {
              const w = widgets[config.id];
              if (!w) return null;

              return (
                <Draggable key={config.id} draggableId={config.id} index={index}>
                  {(draggableProvided, snapshot) => (
                    <div
                      ref={draggableProvided.innerRef}
                      {...draggableProvided.draggableProps}
                      className={config.colSpan === 2 ? "col-span-1 lg:col-span-2" : "col-span-1"}
                    >
                      <DashboardWidget
                        id={config.id}
                        title={w.title}
                        subtitle={w.subtitle}
                        icon={w.icon}
                        colSpan={config.colSpan}
                        minHeight={w.minHeight}
                        maxHeight={w.maxHeight}
                        headerAction={w.headerAction}
                        dragHandleProps={draggableProvided.dragHandleProps}
                        isDragging={snapshot.isDragging}
                      >
                        {w.content}
                      </DashboardWidget>
                    </div>
                  )}
                </Draggable>
              );
            })}
            {provided.placeholder}
          </div>
        )}
      </Droppable>
    </DragDropContext>
  );
}
