import { AnalyticsChartType, AnalyticsFilters, AnalyticsKPI, AnalyticsInsight } from "@/types/analytics.types";
import { ScheduleTask } from "@/types/schedule.types";
import { computeMilestoneData, computeResourceLoad } from "./analyticsComputeEngine";

/**
 * Generate 3 plain-language observations based on active chart, metrics, and tasks data.
 */
export function generateInsights(
  chartType: AnalyticsChartType,
  metrics: AnalyticsKPI,
  filters: AnalyticsFilters,
  tasks: ScheduleTask[],
  projectKPIs?: AnalyticsKPI | null
): AnalyticsInsight[] {
  const insights: AnalyticsInsight[] = [];

  const {
    overallProgress,
    plannedVsActualVariance,
    totalTasks,
    delayedTasks,
    criticalTasks,
    spi,
    cpi
  } = metrics;

  // 1. Core General Performance Insights (always add one global overview)
  if (spi !== null && spi < 0.90) {
    insights.push({
      id: "general_spi_warning",
      title: "Schedule Performance Alert",
      description: `The schedule performance index (SPI) of ${spi.toFixed(2)} indicates work is progressing at only ${Math.round(spi * 100)}% of the planned velocity.`,
      severity: "critical"
    });
  } else if (cpi !== null && cpi < 0.95) {
    insights.push({
      id: "general_cpi_warning",
      title: "Cost Performance Alert",
      description: `The cost performance index (CPI) is ${cpi.toFixed(2)}, showing that actual commitments are exceeding earned progress. Optimize vendor work orders.`,
      severity: "warning"
    });
  } else if (overallProgress > 0 && plannedVsActualVariance <= 0) {
    insights.push({
      id: "general_healthy",
      title: "Delivery on Track",
      description: `Project is running on or ahead of baseline schedule with a safe progress variance of ${Math.abs(plannedVsActualVariance)} days.`,
      severity: "info"
    });
  }

  // 2. Chart Specific Diagnostic Insights
  switch (chartType) {
    case "s_curve":
    case "earned_value":
      if (spi !== null && cpi !== null) {
        if (spi < 1.0 && cpi < 1.0) {
          insights.push({
            id: "evm_overrun_delay",
            title: "Double Threat: Overrun & Delay",
            description: "The project is currently both behind schedule and over budget relative to earned value progress.",
            severity: "critical"
          });
        } else if (spi >= 1.0 && cpi >= 1.0) {
          insights.push({
            id: "evm_optimal",
            title: "Optimal Economic Efficiency",
            description: "Earned progress is pacing ahead of spend and plan. The cost efficiency ratio is in the green zone.",
            severity: "info"
          });
        }
      }
      break;

    case "task_status":
      if (delayedTasks > 0) {
        const ratio = Math.round((delayedTasks / (totalTasks || 1)) * 100);
        insights.push({
          id: "status_delayed_ratio",
          title: "High Slippage Volume",
          description: `${delayedTasks} out of ${totalTasks} tasks (${ratio}%) are delayed past their scheduled finish. Action required in Grid.`,
          severity: ratio > 25 ? "critical" : "warning"
        });
      }
      break;

    case "milestone_trend":
      const milestones = computeMilestoneData(tasks, filters);
      const delayedMilestones = milestones.filter(m => m.status === 'delayed');
      if (delayedMilestones.length > 0) {
        insights.push({
          id: "milestone_slip_alert",
          title: "Milestone Slippages",
          description: `${delayedMilestones.length} major delivery milestones have slipped by more than 7 days from their baseline targets.`,
          severity: "critical"
        });
      }
      break;

    case "critical_tasks":
      const overdueCritical = tasks.filter(t => t.is_critical && t.scheduled_finish && new Date(t.scheduled_finish) < new Date() && (t.percent_complete ?? 0) < 100).length;
      if (overdueCritical > 0) {
        insights.push({
          id: "critical_overdue_alert",
          title: "Critical Path Blocked",
          description: `${overdueCritical} critical path tasks are overdue. Any further delay to these items directly pushes the final handover date.`,
          severity: "critical"
        });
      } else if (criticalTasks > 0) {
        insights.push({
          id: "critical_path_active",
          title: "CPM Network Dynamic",
          description: `There are ${criticalTasks} tasks currently controlling project completion. Focus resources on these sequences.`,
          severity: "info"
        });
      }
      break;

    case "resource_load":
      const resourceLoad = computeResourceLoad(tasks, filters);
      const overloaded = resourceLoad.filter(r => r.overdue > 14);
      if (overloaded.length > 0) {
        insights.push({
          id: "resource_overload",
          title: "Assignee Overload",
          description: `${overloaded[0].name} has over 14 days of overdue task backlog. Consider load balancing assignments.`,
          severity: "warning"
        });
      }
      break;

    case "completion_forecast":
      if (plannedVsActualVariance > 14) {
        insights.push({
          id: "forecast_severe_slippage",
          title: "Severe Delivery Slippage",
          description: `Estimated completion has slipped by ${plannedVsActualVariance} days. We recommend initializing a revised baseline schedule.`,
          severity: "critical"
        });
      } else if (plannedVsActualVariance > 0) {
        insights.push({
          id: "forecast_minor_slippage",
          title: "Handover Target At Risk",
          description: `Handover finish forecast is running ${plannedVsActualVariance} days late. Increase weekly delivery velocity.`,
          severity: "warning"
        });
      }
      break;
  }

  // Fallback to fill up to 3 helpful observations if list is short
  const kpisForProgress = projectKPIs || metrics;
  const pTotalTasks = kpisForProgress.totalTasks;
  const pCompletedTasks = kpisForProgress.completedTasks;
  if (insights.length < 3 && pTotalTasks > 0) {
    const completeRatio = Math.round((pCompletedTasks / pTotalTasks) * 100);
    insights.push({
      id: "general_completion_ratio",
      title: "Delivery Progress",
      description: `Project is ${completeRatio}% complete by task count. ${pCompletedTasks} tasks closed, ${pTotalTasks - pCompletedTasks} remaining.`,
      severity: "info"
    });
  }

  return insights.slice(0, 3);
}
