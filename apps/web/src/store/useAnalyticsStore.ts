import { create } from "zustand";
import { AnalyticsChartType, AnalyticsFilters, AnalyticsKPI } from "@/types/analytics.types";
import { ScheduleTask } from "@/types/schedule.types";
import { computeKPIs } from "@/lib/analyticsComputeEngine";

export interface AnalyticsStoreState {
  selectedChart: AnalyticsChartType;
  setSelectedChart: (chart: AnalyticsChartType) => void;
  
  filters: AnalyticsFilters;
  setFilter: <K extends keyof AnalyticsFilters>(key: K, value: AnalyticsFilters[K]) => void;
  resetFilters: () => void;
  
  projectKPIs: AnalyticsKPI | null;
  computedMetrics: AnalyticsKPI | null;
  recomputeMetrics: (tasks: ScheduleTask[], financials?: any[]) => void;
  
  isMoreFiltersOpen: boolean;
  setMoreFiltersOpen: (open: boolean) => void;

  backendAnalytics: any | null;
  isLoading: boolean;
  fetchAnalytics: (projectId: string) => Promise<void>;
}

const defaultFilters: AnalyticsFilters = {
  dateRange: 'full_project',
  timeBucket: 'monthly',
  viewLevel: 'project',
  criticalOnly: false,
  milestonesOnly: false,
  costEnabled: false,
  comparePrevious: false,
  statusFilter: [],
  assigneeFilter: [],
  vendorFilter: [],
  departmentFilter: [],
};

export const useAnalyticsStore = create<AnalyticsStoreState>()((set, get) => ({
  selectedChart: 's_curve',
  setSelectedChart: (chart) => set({ selectedChart: chart, isMoreFiltersOpen: false }),
  
  filters: defaultFilters,
  setFilter: (key, value) => set((state) => ({
    filters: { ...state.filters, [key]: value }
  })),
  resetFilters: () => set({ filters: defaultFilters }),
  
  projectKPIs: null,
  computedMetrics: null,
  recomputeMetrics: (tasks, financials) => {
    const { filters } = get();
    // Compute project-level KPIs ignoring dateRange filter
    const projectFilters: AnalyticsFilters = { ...filters, dateRange: 'full_project' };
    const pKPIs = computeKPIs(tasks, projectFilters, financials);
    
    // Compute filtered KPIs
    const metrics = computeKPIs(tasks, filters, financials);
    set({ projectKPIs: pKPIs, computedMetrics: metrics });
  },
  
  isMoreFiltersOpen: false,
  setMoreFiltersOpen: (open) => set({ isMoreFiltersOpen: open }),

  backendAnalytics: null,
  isLoading: false,
  fetchAnalytics: async (_projectId) => {
    // Client-side analytics are self-sufficient.
    // Avoid non-existent backend endpoint call to prevent global axios interceptor toast errors.
    return;
  }
}));
