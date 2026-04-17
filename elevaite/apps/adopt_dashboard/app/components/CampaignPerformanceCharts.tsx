"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { BarChart3, TrendingUp } from "lucide-react";
import { useChartTimePeriod } from "@/hooks/useChartTimePeriod";
import { useCampaignChartData } from "@/hooks/useApi";
import ChartDateRangeControls from "./ChartDateRangeControls";
import SpendBudgetChart from "./charts/SpendBudgetChart";
import ImpressionsChart from "./charts/ImpressionsChart";
import CTRChart from "./charts/CTRChart";

interface CampaignPerformanceChartsProps {
  campaignId: string;
  campaignName?: string;
  campaignStartDate?: string;
  campaignEndDate?: string;
  campaignBudget?: number;
  plannedDailyBudget?: Array<{ date: string; value: number }>;
  // Optional overrides to drive charts by a user-selected date range
  overrideStartDate?: string;
  overrideEndDate?: string;
}

export default function CampaignPerformanceCharts({
  campaignId,
  campaignName,
  campaignStartDate,
  campaignEndDate,
  campaignBudget,
  plannedDailyBudget,
  overrideStartDate,
  overrideEndDate,
}: CampaignPerformanceChartsProps) {
  const {
    timePeriod,
    dateRange,
    setTimePeriod,
    getTimePeriodLabel,
    getTimePeriodDescription,
    getDaysFromPeriod,
  } = useChartTimePeriod('monthly', campaignStartDate, campaignEndDate);

  const days = getDaysFromPeriod();

  const startForData = overrideStartDate ?? dateRange?.startDate;
  const endForData = overrideEndDate ?? dateRange?.endDate;

  const { data: chartData, isLoading, error } = useCampaignChartData(
    campaignId,
    days,
    startForData,
    endForData
  );

  // Removed drill down functionality for now

  if (error) {
    return (
      <Card className="bg-white shadow-sm border border-gray-200 mb-6">
        <CardContent className="p-6">
          <div className="text-center py-8">
            <p className="text-red-600">Failed to load chart data. Please try refreshing the page.</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-white shadow-sm border border-gray-200 mb-6">
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-orange-100 text-orange-700">
              <BarChart3 className="w-4 h-4" />
            </span>
            <div>
              <CardTitle className="text-lg font-semibold">Performance Analytics</CardTitle>
              <p className="text-sm text-gray-600 mt-1">{getTimePeriodDescription()}</p>
            </div>
          </div>
          
          {/* Date Range Controls */}
          <ChartDateRangeControls
            timePeriod={timePeriod}
            onTimePeriodChange={setTimePeriod}
            getTimePeriodLabel={getTimePeriodLabel}
            getTimePeriodDescription={getTimePeriodDescription}
            campaignStartDate={overrideStartDate ?? campaignStartDate}
            campaignEndDate={overrideEndDate ?? campaignEndDate}
          />
        </div>
      </CardHeader>
      
      <CardContent className="space-y-6">
        {/* Drill down functionality removed for now */}

        {/* Three Charts Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          
          {/* Spend vs Budget Chart */}
          <Card className="bg-white shadow-sm border border-gray-200">
            <CardContent className="p-6">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-medium text-gray-700 flex items-center gap-2">
                    <TrendingUp className="w-4 h-4" />
                    Spend vs Budget Allocation
                  </h3>
                </div>
                <div className="text-xs text-gray-500">Budget allocation and actual spend over time</div>
                <SpendBudgetChart
                  data={chartData}
                  isLoading={isLoading}
                  timePeriod={timePeriod}
                  campaignBudget={campaignBudget}
                  startDate={overrideStartDate ?? campaignStartDate}
                  endDate={overrideEndDate ?? campaignEndDate}
                />
              </div>
            </CardContent>
          </Card>

          {/* Spend vs Impressions Chart */}
          <Card className="bg-white shadow-sm border border-gray-200">
            <CardContent className="p-6">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-medium text-gray-700 flex items-center gap-2">
                    <BarChart3 className="w-4 h-4" />
                    Spend vs Delivered Impressions
                  </h3>
                </div>
                <div className="text-xs text-gray-500">Campaign spend vs delivered impressions over time</div>
                <ImpressionsChart
                  data={chartData}
                  isLoading={isLoading}
                  timePeriod={timePeriod}
                />
              </div>
            </CardContent>
          </Card>

          {/* CTR Chart */}
          <Card className="bg-white shadow-sm border border-gray-200 lg:col-span-2">
            <CardContent className="p-6">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-medium text-gray-700 flex items-center gap-2">
                    <TrendingUp className="w-4 h-4" />
                    CTR%
                  </h3>
                </div>
                <div className="text-xs text-gray-500">Click-through rate percentage over time</div>
                <CTRChart
                  data={chartData}
                  isLoading={isLoading}
                  timePeriod={timePeriod}
                />
              </div>
            </CardContent>
          </Card>

        </div>
      </CardContent>
    </Card>
  );
}
