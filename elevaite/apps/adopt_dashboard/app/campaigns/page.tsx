"use client";

import { CampaignTable } from "@/components/CampaignTable";
import { DateRangeFilter } from "@/components/DateRangeFilter";

import { useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { DateRange } from "@/types";
import "../page.scss";

interface CampaignMetrics {
  active_campaigns: {
    count: number;
    change_percent: number;
    trend: string;
  };
  work_in_progress_campaigns: {
    count: number;
    change_this_week: number;
    trend: string;
  };
  paused_campaigns: {
    count: number;
    change_this_week: number;
    trend: string;
  };
  total_campaigns: {
    count: number;
    change_this_month: number;
    trend: string;
  };
}

export default function CampaignsPage() {
  const [dateRange, setDateRange] = useState<DateRange | null>(null);
  const [isExporting, setIsExporting] = useState(false);
  const [metrics, setMetrics] = useState<CampaignMetrics | null>(null);
  const [isLoadingMetrics, setIsLoadingMetrics] = useState(true);
  const searchParams = useSearchParams();

  // Get status filter from URL parameters
  const statusFromUrl = searchParams.get('status') as 'all' | 'active' | 'work_in_progress' | 'paused' | 'completed' | null;
  const initialStatusFilter = statusFromUrl || 'all';

  // Fetch campaign metrics on component mount
  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        setIsLoadingMetrics(true);
        // Always use API proxy for all environments
        const BACKEND_URL = 'http://localhost:8000';
        const response = await fetch(`${BACKEND_URL}/api/campaigns/metrics`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
          credentials: 'include'
        });

        if (response.ok) {
          const result = await response.json();
          if (result.success) {
            setMetrics(result.data);
          }
        }
      } catch (err) {
        console.error("Error fetching campaign metrics:", err);
      } finally {
        setIsLoadingMetrics(false);
      }
    };

    fetchMetrics();
  }, []);

  // Reset scroll position when component mounts
  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  const handleDateRangeChange = (range: DateRange | null) => {
    setDateRange(range);
    // In a real app, this would trigger a refetch of data with the new date range
  };

  const handleExport = async () => {
    setIsExporting(true);
    try {
      // Simulate export process
      await new Promise(resolve => setTimeout(resolve, 2000));

      // In a real app, this would generate and download a CSV/Excel file
      const csvContent = `Campaign Name,Status,Spend,ROAS,CTR,Impressions,Clicks,Conversions
Campaign Export Data - ${new Date().toISOString().split('T')[0]}`;

      const blob = new Blob([csvContent], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `campaigns-export-${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);

      alert('Data exported successfully!');
    } catch (error) {
      alert('Export failed. Please try again.');
    } finally {
      setIsExporting(false);
    }
  };



  return (
    <main className="adopt-dashboard-container" style={{
      height: '100%',
      width: '100%',
      overflow: 'auto'
    }}>
      {/* Title and Filters Section */}
      <div className="title-filters-section flex justify-between items-start">
        <div className="title-content">
          <h1>Campaigns</h1>
          <p>Monitor and create your campaigns</p>
        </div>
        <div className="flex items-center space-x-3">
          <DateRangeFilter
            onDateRangeChange={handleDateRangeChange}
            onExport={handleExport}
            isExporting={isExporting}
          />
        </div>
      </div>






      {/* Campaign Metrics Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 mb-6">
        {/* Active Campaigns */}
        <div className="bg-white rounded-lg p-4 border border-gray-200">
          <div className="flex items-start space-x-3">
            {/* Icon positioned to the left */}
            <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center flex-shrink-0 mt-1">
              <svg className="w-5 h-5 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
            </div>

            {/* Content to the right */}
            <div className="flex-1 min-w-0">
              <div className="text-md text-gray-600 font-medium mb-2">
                Active Campaigns
              </div>
              {isLoadingMetrics ? (
                <div className="space-y-2">
                  <div className="h-8 bg-gray-200 rounded w-12 animate-pulse"></div>
                  <div className="h-4 bg-gray-200 rounded w-16 animate-pulse"></div>
                </div>
              ) : (
                <>
                  <div className="text-4xl font-medium text-gray-900 mb-1">
                    {metrics?.active_campaigns.count || 0}
                  </div>
                  <div className={`text-xs font-medium ${
                    metrics?.active_campaigns.trend === 'up' ? 'text-green-600' :
                    metrics?.active_campaigns.trend === 'down' ? 'text-red-600' : 'text-gray-600'
                  }`}>
                    {metrics?.active_campaigns.change_percent !== undefined && metrics.active_campaigns.change_percent !== 0 ? (
                      `${metrics.active_campaigns.change_percent > 0 ? '+' : ''}${metrics.active_campaigns.change_percent}% ${
                        metrics.active_campaigns.trend === 'up' ? '↗' : metrics.active_campaigns.trend === 'down' ? '↘' : ''
                      }`
                    ) : 'No change'}
                  </div>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Work in Progress Campaigns */}
        <div className="bg-white rounded-lg p-4 border border-gray-200">
          <div className="flex items-start space-x-3">
            {/* Icon positioned to the left */}
            <div className="w-8 h-8 bg-yellow-100 rounded-full flex items-center justify-center flex-shrink-0 mt-1">
              <svg className="w-5 h-5 text-yellow-600" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM7 9a1 1 0 000 2h6a1 1 0 100-2H7z" clipRule="evenodd" />
              </svg>
            </div>

            {/* Content to the right */}
            <div className="flex-1 min-w-0">
              <div className="text-md text-gray-600 font-medium mb-2">
                Work in Progress
              </div>
              {isLoadingMetrics ? (
                <div className="space-y-2">
                  <div className="h-8 bg-gray-200 rounded w-12 animate-pulse"></div>
                  <div className="h-4 bg-gray-200 rounded w-20 animate-pulse"></div>
                </div>
              ) : (
                <>
                  <div className="text-4xl font-medium text-gray-900 mb-1">
                    {metrics?.work_in_progress_campaigns.count || 0}
                  </div>
                  <div className={`text-xs font-medium ${
                    (metrics?.work_in_progress_campaigns.change_this_week || 0) > 0 ? 'text-blue-600' :
                    (metrics?.work_in_progress_campaigns.change_this_week || 0) < 0 ? 'text-green-600' : 'text-gray-600'
                  }`}>
                    {metrics?.work_in_progress_campaigns.change_this_week !== undefined && metrics.work_in_progress_campaigns.change_this_week !== 0 ? (
                      `${metrics.work_in_progress_campaigns.change_this_week > 0 ? '+' : ''}${metrics.work_in_progress_campaigns.change_this_week} this week`
                    ) : 'No change this week'}
                  </div>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Paused Campaigns */}
        <div className="bg-white rounded-lg p-4 border border-gray-200">
          <div className="flex items-start space-x-3">
            {/* Icon positioned to the left */}
            <div className="w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center flex-shrink-0 mt-1">
              <svg className="w-5 h-5 text-gray-600" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM7 8a1 1 0 012 0v4a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v4a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
            </div>

            {/* Content to the right */}
            <div className="flex-1 min-w-0">
              <div className="text-md text-gray-600 font-medium mb-2">
                Paused Campaigns
              </div>
              {isLoadingMetrics ? (
                <div className="space-y-2">
                  <div className="h-8 bg-gray-200 rounded w-12 animate-pulse"></div>
                  <div className="h-4 bg-gray-200 rounded w-20 animate-pulse"></div>
                </div>
              ) : (
                <>
                  <div className="text-4xl font-medium text-gray-900 mb-1">
                    {metrics?.paused_campaigns.count || 0}
                  </div>
                  <div className={`text-xs font-medium ${
                    metrics?.paused_campaigns.change_this_week !== undefined && metrics.paused_campaigns.change_this_week > 0 ? 'text-gray-600' :
                    metrics?.paused_campaigns.change_this_week !== undefined && metrics.paused_campaigns.change_this_week < 0 ? 'text-green-600' : 'text-gray-600'
                  }`}>
                    {metrics?.paused_campaigns.change_this_week !== undefined && metrics.paused_campaigns.change_this_week !== 0 ? (
                      `${metrics.paused_campaigns.change_this_week > 0 ? '+' : ''}${metrics.paused_campaigns.change_this_week} this week`
                    ) : 'No change this week'}
                  </div>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Total Campaigns */}
        <div className="bg-white rounded-lg p-4 border border-gray-200">
          <div className="flex items-start space-x-3">
            {/* Icon positioned to the left */}
            <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0 mt-1">
              <svg className="w-5 h-5 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M4 4a2 2 0 012-2h8a2 2 0 012 2v2h2a2 2 0 012 2v10a2 2 0 01-2 2H8a2 2 0 01-2-2v-2H4a2 2 0 01-2-2V4zm2 0v8h2V8a2 2 0 012-2h6V4H6zm2 6v8h10V8H8z" clipRule="evenodd" />
              </svg>
            </div>

            {/* Content to the right */}
            <div className="flex-1 min-w-0">
              <div className="text-md text-gray-600 font-medium mb-2">
                Total Campaigns
              </div>
              {isLoadingMetrics ? (
                <div className="space-y-2">
                  <div className="h-8 bg-gray-200 rounded w-12 animate-pulse"></div>
                  <div className="h-4 bg-gray-200 rounded w-20 animate-pulse"></div>
                </div>
              ) : (
                <>
                  <div className="text-4xl font-medium text-gray-900 mb-1">
                    {metrics?.total_campaigns.count || 0}
                  </div>
                  <div className="text-xs text-blue-600 font-medium">
                    {metrics?.total_campaigns.change_this_month !== undefined && metrics.total_campaigns.change_this_month > 0 ? (
                      `+${metrics.total_campaigns.change_this_month} this month`
                    ) : 'No new campaigns this month'}
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="main-content-section space-y-6">
        <CampaignTable
          defaultTab="campaigns"
          showTabs={false}
          showStatusTabs={true}
          initialStatusFilter={initialStatusFilter}
        />
      </div>
    </main>
  );
}
