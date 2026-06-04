import { ScheduleTask } from "@/types/schedule.types";
import { AnalyticsFilters, AnalyticsKPI } from "@/types/analytics.types";

/**
 * Filter tasks based on the AnalyticsFilters criteria.
 */
export function getFilteredTasks(tasks: ScheduleTask[], filters: AnalyticsFilters): ScheduleTask[] {
  let filtered = [...tasks];

  // 1. Critical Only
  if (filters.criticalOnly) {
    filtered = filtered.filter(t => t.is_critical);
  }

  // 2. Milestones Only
  if (filters.milestonesOnly) {
    filtered = filtered.filter(t => t.is_milestone);
  }

  // 3. Status Filter
  if (filters.statusFilter && filters.statusFilter.length > 0) {
    filtered = filtered.filter(t => t.task_status && filters.statusFilter!.includes(t.task_status));
  }

  // 4. Assignee Filter
  if (filters.assigneeFilter && filters.assigneeFilter.length > 0) {
    filtered = filtered.filter(t => {
      const isDetailsMatched = t.assignee_details?.some(d => filters.assigneeFilter!.includes(d.name));
      const isIdsMatched = t.assignee_ids?.some(id => filters.assigneeFilter!.includes(id));
      const isResourcesMatched = t.assigned_resources?.some(r => filters.assigneeFilter!.includes(r));
      
      const singleAssignee = (t.assignee || t.owner || t.responsible || t.assigned_to_name) as string | undefined;
      const isSingleMatched = typeof singleAssignee === "string" && filters.assigneeFilter!.includes(singleAssignee.trim());
      
      return !!isDetailsMatched || !!isIdsMatched || !!isResourcesMatched || !!isSingleMatched;
    });
  }

  // 5. Department Filter (derived from WBS first segment mapped to root task names)
  if (filters.departmentFilter && filters.departmentFilter.length > 0) {
    const rootTaskMap = new Map<string, string>();
    tasks.forEach(t => {
      if (t.wbs_code && !t.wbs_code.includes('.')) {
        rootTaskMap.set(t.wbs_code, t.task_name || (t.name as string | undefined) || t.task_id);
      }
    });

    filtered = filtered.filter(t => {
      const rootCode = t.wbs_code?.split('.')[0];
      if (!rootCode) return filters.departmentFilter!.includes('Misc');

      let deptName = rootCode === 'C' ? 'Construction' :
                     rootCode === 'P' ? 'Contracting' :
                     rootCode === 'D' ? 'Design/Engineering' :
                     rootCode === 'S' ? 'Site Ops' :
                     rootCode === 'I' ? 'Interiors' : '';
      if (!deptName) {
        deptName = rootTaskMap.get(rootCode) || rootCode;
      }
      return filters.departmentFilter!.includes(deptName);
    });
  }

  // 6. Vendor Filter (derived from assigned_resources or similar)
  if (filters.vendorFilter && filters.vendorFilter.length > 0) {
    filtered = filtered.filter(t => 
      t.assigned_resources?.some(r => filters.vendorFilter!.includes(r))
    );
  }

  // 7. Date Range filter
  const today = new Date();
  let startLimit: Date | null = null;
  let endLimit: Date | null = null;

  if (filters.dateRange === 'this_month') {
    startLimit = new Date(today.getFullYear(), today.getMonth(), 1);
    endLimit = new Date(today.getFullYear(), today.getMonth() + 1, 0, 23, 59, 59, 999);
  } else if (filters.dateRange === 'next_30') {
    startLimit = new Date(today);
    endLimit = new Date(today.getTime() + 30 * 24 * 60 * 60 * 1000);
  } else if (filters.dateRange === 'quarter') {
    const quarter = Math.floor(today.getMonth() / 3);
    startLimit = new Date(today.getFullYear(), quarter * 3, 1);
    endLimit = new Date(today.getFullYear(), (quarter + 1) * 3, 0, 23, 59, 59, 999);
  } else if (filters.dateRange === 'custom') {
    if (filters.customDateStart) startLimit = new Date(filters.customDateStart);
    if (filters.customDateEnd) endLimit = new Date(filters.customDateEnd);
  }

  if (startLimit || endLimit) {
    filtered = filtered.filter(t => {
      const taskStart = t.scheduled_start ? new Date(t.scheduled_start) : null;
      const taskFinish = t.scheduled_finish ? new Date(t.scheduled_finish) : null;
      
      if (!taskStart && !taskFinish) return false;
      
      let inRange = true;
      if (startLimit) {
        if (taskFinish && taskFinish < startLimit) inRange = false;
        else if (!taskFinish && taskStart && taskStart < startLimit) inRange = false;
      }
      if (endLimit) {
        if (taskStart && taskStart > endLimit) inRange = false;
        else if (!taskStart && taskFinish && taskFinish > endLimit) inRange = false;
      }
      return inRange;
    });
  }

  return filtered;
}

/**
 * Compute KPIs summary from filtered tasks and financials.
 */
export function computeKPIs(
  tasks: ScheduleTask[],
  filters: AnalyticsFilters,
  financials?: { original_budget?: number; committed_value?: number }[]
): AnalyticsKPI {
  const filtered = getFilteredTasks(tasks, filters);
  const today = new Date();

  // Basic counts
  const totalTasks = filtered.length;
  const completedTasks = filtered.filter(
    (t) => t.task_status === "completed" || t.task_status === "closed" || (t.percent_complete ?? 0) === 100
  ).length;

  const delayedTasks = filtered.filter((t) => {
    const finish = t.scheduled_finish ? new Date(t.scheduled_finish) : null;
    return (
      finish &&
      finish < today &&
      (t.percent_complete ?? 0) < 100 &&
      t.task_status !== "completed" &&
      t.task_status !== "closed"
    );
  }).length;

  const criticalTasks = filtered.filter((t) => t.is_critical).length;

  // Overall Progress (weighted average by weightage_percent, or baseline_cost, or fallback to simple average)
  let overallProgress = 0;
  const totalWeight = filtered.reduce((sum, t) => sum + (t.weightage_percent ?? 0), 0);
  if (totalWeight > 0) {
    overallProgress = Math.round(
      filtered.reduce((sum, t) => sum + (t.weightage_percent ?? 0) * (t.percent_complete ?? 0), 0) / totalWeight
    );
  } else {
    const totalCost = filtered.reduce((sum, t) => sum + (t.baseline_cost ?? 0), 0);
    if (totalCost > 0) {
      overallProgress = Math.round(
        filtered.reduce((sum, t) => sum + (t.baseline_cost ?? 0) * (t.percent_complete ?? 0), 0) / totalCost
      );
    } else {
      overallProgress = totalTasks > 0
        ? Math.round(filtered.reduce((sum, t) => sum + (t.percent_complete ?? 0), 0) / totalTasks)
        : 0;
    }
  }

  // Slippage (Planned vs Actual/Scheduled Finish date difference for the project)
  let plannedVsActualVariance = 0;
  let maxScheduledFinish: Date | null = null;
  let maxBaselineFinish: Date | null = null;

  for (const t of filtered) {
    if (t.scheduled_finish) {
      const d = new Date(t.scheduled_finish);
      if (!maxScheduledFinish || d > maxScheduledFinish) maxScheduledFinish = d;
    }
    if (t.baseline_finish) {
      const d = new Date(t.baseline_finish);
      if (!maxBaselineFinish || d > maxBaselineFinish) maxBaselineFinish = d;
    }
  }

  if (maxScheduledFinish && maxBaselineFinish) {
    plannedVsActualVariance = Math.round(
      (maxScheduledFinish.getTime() - maxBaselineFinish.getTime()) / (1000 * 60 * 60 * 24)
    );
  }

  // Budget Used %
  let budgetUsedPercent: number | null = null;
  if (financials && financials.length > 0) {
    const totalOriginalBudget = financials.reduce((sum, f) => sum + (f.original_budget ?? 0), 0);
    const totalCommittedValue = financials.reduce((sum, f) => sum + (f.committed_value ?? 0), 0);
    if (totalOriginalBudget > 0) {
      budgetUsedPercent = Math.round((totalCommittedValue / totalOriginalBudget) * 100);
    }
  } else {
    const totalCost = filtered.reduce((sum, t) => sum + (t.baseline_cost ?? 0), 0);
    const totalActualCost = filtered.reduce((sum, t) => sum + (t.wo_value ?? t.payment_value ?? 0), 0);
    if (totalCost > 0) {
      budgetUsedPercent = Math.round((totalActualCost / totalCost) * 100);
    }
  }

  // Forecast Finish Date
  let forecastFinishDate: string | null = null;
  let earliestStart: Date | null = null;
  for (const t of filtered) {
    const start = t.scheduled_start ? new Date(t.scheduled_start) : null;
    if (start && (!earliestStart || start < earliestStart)) {
      earliestStart = start;
    }
  }

  if (earliestStart && maxScheduledFinish) {
    const elapsedMs = today.getTime() - earliestStart.getTime();
    if (elapsedMs > 0 && overallProgress > 0 && overallProgress < 100) {
      const projectedTotalMs = elapsedMs / (overallProgress / 100);
      const forecastedFinish = new Date(earliestStart.getTime() + projectedTotalMs);
      forecastFinishDate = forecastedFinish.toISOString().split("T")[0];
    } else {
      forecastFinishDate = maxScheduledFinish.toISOString().split("T")[0];
    }
  }

  // EVM computation (SPI, CPI)
  let totalPV = 0;
  let totalEV = 0;
  let totalAC = 0;

  filtered.forEach((t) => {
    // Treat cost as 1 if missing for counting-based EVM fallback
    const cost = t.baseline_cost ?? 1;
    const progress = (t.percent_complete ?? 0) / 100;
    
    totalEV += cost * progress;
    totalAC += t.payment_value ?? t.wo_value ?? 0;

    const bStart = t.baseline_start ? new Date(t.baseline_start) : (t.scheduled_start ? new Date(t.scheduled_start) : null);
    const bFinish = t.baseline_finish ? new Date(t.baseline_finish) : (t.scheduled_finish ? new Date(t.scheduled_finish) : null);

    if (bStart && bFinish) {
      if (today >= bFinish) {
        totalPV += cost;
      } else if (today > bStart) {
        const totalDuration = bFinish.getTime() - bStart.getTime();
        const elapsed = today.getTime() - bStart.getTime();
        if (totalDuration > 0) {
          totalPV += cost * (elapsed / totalDuration);
        }
      }
    }
  });

  const spi = totalPV > 0 ? Number((totalEV / totalPV).toFixed(2)) : null;
  const cpi = totalAC > 0 ? Number((totalEV / totalAC).toFixed(2)) : null;

  return {
    overallProgress,
    plannedVsActualVariance,
    totalTasks,
    completedTasks,
    delayedTasks,
    criticalTasks,
    budgetUsedPercent,
    forecastFinishDate,
    spi,
    cpi,
  };
}

/**
 * Generate monthly interval dates for chart axes.
 */
function getMonthlyIntervals(start: Date, end: Date): Date[] {
  const dates: Date[] = [];
  const current = new Date(start.getFullYear(), start.getMonth(), 1);
  while (current <= end) {
    dates.push(new Date(current));
    current.setMonth(current.getMonth() + 1);
  }
  return dates;
}

/**
 * Compute S-Curve line chart data (PV, EV, and AC).
 */
export function computeSCurveData(tasks: ScheduleTask[], filters: AnalyticsFilters, _financials?: unknown[]) {
  const filtered = getFilteredTasks(tasks, filters);
  if (filtered.length === 0) return [];

  // Determine date bounds
  let minDate = new Date();
  let maxDate = new Date();
  let initialized = false;

  filtered.forEach(t => {
    const dates = [
      t.baseline_start, t.baseline_finish,
      t.scheduled_start, t.scheduled_finish
    ].map(d => d ? new Date(d) : null).filter(Boolean) as Date[];

    dates.forEach(d => {
      if (!initialized) {
        minDate = new Date(d);
        maxDate = new Date(d);
        initialized = true;
      } else {
        if (d < minDate) minDate = new Date(d);
        if (d > maxDate) maxDate = new Date(d);
      }
    });
  });

  // Generate monthly intervals
  const intervals = getMonthlyIntervals(minDate, maxDate);
  const data = intervals.map((date) => {
    let pv = 0;
    let ev = 0;
    let ac = 0;

    filtered.forEach((t) => {
      const cost = t.baseline_cost ?? 1;
      const progress = (t.percent_complete ?? 0) / 100;
      
      const bStart = t.baseline_start ? new Date(t.baseline_start) : (t.scheduled_start ? new Date(t.scheduled_start) : null);
      const bFinish = t.baseline_finish ? new Date(t.baseline_finish) : (t.scheduled_finish ? new Date(t.scheduled_finish) : null);

      // Earned Value (EV) is calculated up to today or task completion
      // For charting over time, we distribute EV based on completed percentage
      if (t.actual_start) {
        const actStart = new Date(t.actual_start);
        const actFinish = t.actual_finish ? new Date(t.actual_finish) : new Date();
        
        if (date >= actFinish) {
          ev += cost * progress;
        } else if (date > actStart) {
          const actDur = actFinish.getTime() - actStart.getTime();
          const elapsed = date.getTime() - actStart.getTime();
          if (actDur > 0) {
            ev += cost * progress * (elapsed / actDur);
          }
        }
      } else if (bStart) {
        if (date >= date) { // Today or completed
          ev += cost * progress;
        }
      }

      // Planned Value (PV)
      if (bStart && bFinish) {
        if (date >= bFinish) {
          pv += cost;
        } else if (date > bStart) {
          const totalDuration = bFinish.getTime() - bStart.getTime();
          const elapsed = date.getTime() - bStart.getTime();
          if (totalDuration > 0) {
            pv += cost * (elapsed / totalDuration);
          }
        }
      }

      // Actual Cost (AC)
      const taskAC = t.payment_value ?? t.wo_value ?? 0;
      if (taskAC > 0 && t.actual_start) {
        const actStart = new Date(t.actual_start);
        if (date >= actStart) {
          ac += taskAC;
        }
      }
    });

    return {
      date: date.toLocaleDateString("en-US", { month: "short", year: "2-digit" }),
      "Planned Value (PV)": Math.round(pv),
      "Earned Value (EV)": Math.round(ev),
      "Actual Cost (AC)": Math.round(ac)
    };
  });

  return data;
}

/**
 * Donut chart data for task statuses.
 */
export function computeTaskStatusDistribution(tasks: ScheduleTask[], filters: AnalyticsFilters) {
  const filtered = getFilteredTasks(tasks, filters);
  const statusCounts: Record<string, number> = {
    "Not Started": 0,
    "In Progress": 0,
    "Delayed": 0,
    "Completed": 0,
    "On Hold": 0,
    "Cancelled": 0
  };

  const today = new Date();

  filtered.forEach(t => {
    const rawStatus = t.task_status as string | undefined;
    let status = rawStatus?.toLowerCase()?.trim() || "";
    
    // Fallback if status is missing or empty
    if (!status) {
      if ((t.percent_complete ?? 0) === 100) {
        status = 'completed';
      } else if ((t.percent_complete ?? 0) > 0) {
        status = 'in_progress';
      } else {
        status = 'not_started';
      }
    }

    const isCompleted = status === 'completed' || status === 'closed' || (t.percent_complete ?? 0) === 100;
    const isDelayed = !isCompleted && t.scheduled_finish && new Date(t.scheduled_finish) < today;

    if (status === 'cancelled') {
      statusCounts["Cancelled"]++;
    } else if (isCompleted) {
      statusCounts["Completed"]++;
    } else if (isDelayed) {
      statusCounts["Delayed"]++;
    } else if (status === 'in_progress') {
      statusCounts["In Progress"]++;
    } else if (status === 'on_hold' || status === 'on hold') {
      statusCounts["On Hold"]++;
    } else if (status === 'draft' || status === 'not_started' || status === 'not started') {
      statusCounts["Not Started"]++;
    } else {
      statusCounts["On Hold"]++;
    }
  });

  const colors: Record<string, string> = {
    "Not Started": "#a1a1aa", // Gray
    "In Progress": "#f59e0b", // Amber
    "Delayed": "#ef4444",     // Red
    "Completed": "#10b981",   // Green
    "On Hold": "#6366f1",     // Indigo
    "Cancelled": "#f43f5e"    // Pink/Rose
  };

  return Object.entries(statusCounts)
    .map(([name, value]) => ({
      name,
      value,
      color: colors[name]
    }));
}

/**
 * Milestone timeline and status.
 */
export function computeMilestoneData(tasks: ScheduleTask[], filters: AnalyticsFilters) {
  const filtered = getFilteredTasks(tasks, filters).filter(t => t.is_milestone);

  return filtered.map(t => {
    const baseline = t.baseline_finish ? new Date(t.baseline_finish) : null;
    const current = t.scheduled_finish ? new Date(t.scheduled_finish) : null;
    let delayDays = 0;
    let status: 'on-time' | 'at-risk' | 'delayed' = 'on-time';

    if (baseline && current) {
      delayDays = Math.max(0, Math.round((current.getTime() - baseline.getTime()) / (1000 * 60 * 60 * 24)));
    }

    if (t.task_status === 'completed' || t.task_status === 'closed' || (t.percent_complete ?? 0) === 100) {
      status = 'on-time';
    } else if (delayDays > 7) {
      status = 'delayed';
    } else if (delayDays > 0) {
      status = 'at-risk';
    }

    return {
      task_id: t.task_id,
      name: t.task_name,
      baseline: t.baseline_finish || t.scheduled_finish || "N/A",
      current: t.scheduled_finish || "N/A",
      delayDays,
      status
    };
  });
}

/**
 * Variance chart data (Baseline Finish vs Scheduled Finish).
 */
export function computeScheduleVariance(tasks: ScheduleTask[], filters: AnalyticsFilters) {
  const filtered = getFilteredTasks(tasks, filters);
  
  // Aggregate by View Level (phase/department/WBS code)
  const varianceMap: Record<string, { name: string; variance: number; count: number }> = {};
  
  const rootTaskMap = new Map<string, string>();
  tasks.forEach(t => {
    if (t.wbs_code && !t.wbs_code.includes('.')) {
      rootTaskMap.set(t.wbs_code, t.task_name || (t.name as string | undefined) || t.task_id);
    }
  });

  filtered.forEach(t => {
    let groupKey = 'Project';
    
    if (filters.viewLevel === 'phase') {
      const rootCode = t.wbs_code?.split('.')[0];
      if (!rootCode) {
        groupKey = 'Misc';
      } else {
        groupKey = rootCode === 'C' ? 'Construction' :
                   rootCode === 'P' ? 'Contracting' :
                   rootCode === 'D' ? 'Design/Engineering' :
                   rootCode === 'S' ? 'Site Ops' :
                   rootCode === 'I' ? 'Interiors' : '';
        if (!groupKey) {
          groupKey = rootTaskMap.get(rootCode) || rootCode;
        }
      }
    } else if (filters.viewLevel === 'wbs') {
      groupKey = t.wbs_code || 'Root';
    } else if (filters.viewLevel === 'task_group') {
      groupKey = t.parent_id ? (tasks.find(pt => pt.task_id === t.parent_id)?.task_name || 'Group') : 'Direct';
    }

    const baseline = t.baseline_finish ? new Date(t.baseline_finish) : null;
    const current = t.scheduled_finish ? new Date(t.scheduled_finish) : null;

    let varDays = 0;
    if (baseline && current) {
      // Positive = slippage (behind), Negative = ahead
      varDays = Math.round((current.getTime() - baseline.getTime()) / (1000 * 60 * 60 * 24));
    }

    if (!varianceMap[groupKey]) {
      varianceMap[groupKey] = { name: groupKey, variance: 0, count: 0 };
    }
    varianceMap[groupKey].variance += varDays;
    varianceMap[groupKey].count++;
  });

  return Object.values(varianceMap).map(g => ({
    name: g.name,
    // Average variance per task in the group
    variance: g.count > 0 ? Math.round(g.variance / g.count) : 0
  }));
}

/**
 * Resource / Assignee load calculations.
 */
export function computeResourceLoad(tasks: ScheduleTask[], filters: AnalyticsFilters) {
  const filtered = getFilteredTasks(tasks, filters);
  const resourceMap: Record<string, { name: string; planned: number; completed: number; overdue: number }> = {};

  const today = new Date();

  filtered.forEach(t => {
    const assignees = t.assignee_details || [];
    const resourceNames = assignees.map(a => a.name).filter(Boolean);
    if (resourceNames.length === 0 && Array.isArray(t.assigned_resources)) {
      t.assigned_resources.forEach(r => {
        if (r) resourceNames.push(r);
      });
    }
    if (resourceNames.length === 0) {
      const singleAssignee = (t.assignee || t.owner || t.responsible || t.assigned_to_name) as string | undefined;
      if (typeof singleAssignee === "string" && singleAssignee.trim()) {
        resourceNames.push(singleAssignee.trim());
      }
    }
    if (resourceNames.length === 0) {
      resourceNames.push('Unassigned');
    }

    const isCompleted = t.task_status === 'completed' || t.task_status === 'closed' || (t.percent_complete ?? 0) === 100;
    const isOverdue = !isCompleted && t.scheduled_finish && new Date(t.scheduled_finish) < today;

    // Workload duration metric (days)
    const duration = t.scheduled_duration ?? 1;

    resourceNames.forEach(name => {
      if (!resourceMap[name]) {
        resourceMap[name] = { name, planned: 0, completed: 0, overdue: 0 };
      }
      resourceMap[name].planned += duration;
      if (isCompleted) {
        resourceMap[name].completed += duration;
      }
      if (isOverdue) {
        resourceMap[name].overdue += duration;
      }
    });
  });

  return Object.values(resourceMap);
}

/**
 * Historical/Projected Delay Trend chart.
 */
export function computeDelayTrend(tasks: ScheduleTask[], filters: AnalyticsFilters) {
  const filtered = getFilteredTasks(tasks, filters);
  if (filtered.length === 0) return [];

  let minDate = new Date();
  let maxDate = new Date();
  let initialized = false;

  filtered.forEach(t => {
    if (t.scheduled_finish) {
      const d = new Date(t.scheduled_finish);
      if (!initialized) {
        minDate = d;
        maxDate = d;
        initialized = true;
      } else {
        if (d < minDate) minDate = d;
        if (d > maxDate) maxDate = d;
      }
    }
  });

  const intervals = getMonthlyIntervals(minDate, maxDate);
  const today = new Date();

  return intervals.map(date => {
    let delayedCount = 0;
    let totalDelayDays = 0;

    filtered.forEach(t => {
      const finish = t.scheduled_finish ? new Date(t.scheduled_finish) : null;
      const baseline = t.baseline_finish ? new Date(t.baseline_finish) : null;

      if (finish && finish <= date) {
        const isCompleted = t.task_status === 'completed' || t.task_status === 'closed' || (t.percent_complete ?? 0) === 100;
        const isDelayedAtInterval = !isCompleted && finish < today;

        if (isDelayedAtInterval) {
          delayedCount++;
          if (baseline) {
            const delay = Math.max(0, Math.round((finish.getTime() - baseline.getTime()) / (1000 * 60 * 60 * 24)));
            totalDelayDays += delay;
          }
        }
      }
    });

    return {
      month: date.toLocaleDateString("en-US", { month: "short", year: "2-digit" }),
      "Delayed Tasks": delayedCount,
      "Avg Delay (Days)": delayedCount > 0 ? Math.round(totalDelayDays / delayedCount) : 0
    };
  });
}

/**
 * Completion forecast timelines.
 */
export function computeCompletionForecast(tasks: ScheduleTask[], filters: AnalyticsFilters) {
  const filtered = getFilteredTasks(tasks, filters);
  
  let maxBaselineFinish: Date | null = null;
  let maxScheduledFinish: Date | null = null;
  let earliestStart: Date | null = null;

  for (const t of filtered) {
    if (t.scheduled_start) {
      const d = new Date(t.scheduled_start);
      if (!earliestStart || d < earliestStart) earliestStart = d;
    }
    if (t.scheduled_finish) {
      const d = new Date(t.scheduled_finish);
      if (!maxScheduledFinish || d > maxScheduledFinish) maxScheduledFinish = d;
    }
    if (t.baseline_finish) {
      const d = new Date(t.baseline_finish);
      if (!maxBaselineFinish || d > maxBaselineFinish) maxBaselineFinish = d;
    }
  }

  const kpis = computeKPIs(tasks, filters);
  
  return {
    baselineFinish: maxBaselineFinish ? maxBaselineFinish.toISOString().split("T")[0] : null,
    targetFinish: maxScheduledFinish ? maxScheduledFinish.toISOString().split("T")[0] : null,
    forecastFinish: kpis.forecastFinishDate,
    overallProgress: kpis.overallProgress,
    slippageDays: kpis.plannedVsActualVariance
  };
}
