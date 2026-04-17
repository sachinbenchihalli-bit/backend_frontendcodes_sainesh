import { useState, useCallback } from 'react';

export type TimePeriod = 'daily' | 'weekly' | 'monthly' | 'quarterly' | 'custom';

export interface DateRange {
  startDate: string;
  endDate: string;
}

export interface TimePeriodState {
  currentPeriod: TimePeriod;
  canDrillDown: boolean;
  canDrillUp: boolean;
  dateRange?: DateRange;
  isCustom: boolean;
}

export interface UseChartTimePeriodReturn {
  timePeriod: TimePeriod;
  timePeriodState: TimePeriodState;
  dateRange?: DateRange;
  drillDown: () => void;
  drillUp: () => void;
  setTimePeriod: (period: TimePeriod) => void;
  setCustomDateRange: (startDate: string, endDate: string) => void;
  resetToDefault: () => void;
  getTimePeriodLabel: () => string;
  getTimePeriodDescription: () => string;
  getDaysFromPeriod: () => number | undefined;
}

/**
 * Custom hook for managing chart time period with date range controls
 * Supports preset periods and custom date ranges
 */
export const useChartTimePeriod = (
  initialPeriod: TimePeriod = 'monthly',
  campaignStartDate?: string,
  campaignEndDate?: string
): UseChartTimePeriodReturn => {
  const [timePeriod, setTimePeriodState] = useState<TimePeriod>(initialPeriod);
  const [customDateRange, setCustomDateRangeState] = useState<DateRange | undefined>();

  const getDateRangeForPeriod = useCallback((period: TimePeriod): DateRange | undefined => {
    // For the new periods, the date range is driven by the campaign's start/end when available.
    if (period === 'custom') return customDateRange;

    if (campaignStartDate && campaignEndDate) {
      return { startDate: campaignStartDate, endDate: campaignEndDate };
    }

    // Fallback if campaign dates are missing: last 90 days ending today
    const today = new Date();
    const start = new Date(today.getTime() - 89 * 24 * 60 * 60 * 1000);
    return {
      startDate: start.toISOString().split('T')[0],
      endDate: today.toISOString().split('T')[0]
    };
  }, [customDateRange, campaignStartDate, campaignEndDate]);

  const getTimePeriodState = useCallback((period: TimePeriod): TimePeriodState => {
    const dateRange = getDateRangeForPeriod(period);

    return {
      currentPeriod: period,
      canDrillDown: false,
      canDrillUp: false,
      dateRange,
      isCustom: period === 'custom'
    };
  }, [getDateRangeForPeriod]);

  const drillDown = useCallback(() => {
    // No-op for the new period model
    setTimePeriodState(current => current);
  }, []);

  const drillUp = useCallback(() => {
    // No-op for the new period model
    setTimePeriodState(current => current);
  }, []);

  const setTimePeriod = useCallback((period: TimePeriod) => {
    setTimePeriodState(period);
    if (period !== 'custom') {
      setCustomDateRangeState(undefined);
    }
  }, []);

  const setCustomDateRange = useCallback((startDate: string, endDate: string) => {
    setCustomDateRangeState({ startDate, endDate });
    setTimePeriodState('custom');
  }, []);

  const resetToDefault = useCallback(() => {
    setTimePeriodState('monthly');
    setCustomDateRangeState(undefined);
  }, []);

  const getTimePeriodLabel = useCallback(() => {
    switch (timePeriod) {
      case 'daily': return 'Daily';
      case 'weekly': return 'Weekly';
      case 'monthly': return 'Monthly';
      case 'quarterly': return 'Quarterly';
      case 'custom': return 'Custom Range';
      default: return 'Monthly';
    }
  }, [timePeriod]);

  const getTimePeriodDescription = useCallback(() => {
    const dateRange = getDateRangeForPeriod(timePeriod);

    if (timePeriod === 'custom' && customDateRange) {
      return `${new Date(customDateRange.startDate).toLocaleDateString()} - ${new Date(customDateRange.endDate).toLocaleDateString()}`;
    }

    if (dateRange) {
      return `${new Date(dateRange.startDate).toLocaleDateString()} - ${new Date(dateRange.endDate).toLocaleDateString()}`;
    }

    return 'Performance data for selected period';
  }, [timePeriod, customDateRange, getDateRangeForPeriod, campaignStartDate, campaignEndDate]);

  const getDaysFromPeriod = useCallback(() => {
    // We use explicit start/end for fetching; days isn't needed except for custom ranges
    if (timePeriod === 'custom' && customDateRange) {
      const start = new Date(customDateRange.startDate);
      const end = new Date(customDateRange.endDate);
      return Math.ceil((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24)) + 1;
    }
    return undefined;
  }, [timePeriod, customDateRange]);

  return {
    timePeriod,
    timePeriodState: getTimePeriodState(timePeriod),
    dateRange: getDateRangeForPeriod(timePeriod),
    drillDown,
    drillUp,
    setTimePeriod,
    setCustomDateRange,
    resetToDefault,
    getTimePeriodLabel,
    getTimePeriodDescription,
    getDaysFromPeriod,
  };
};
