"use client";

import { CampaignTable } from "@/components/CampaignTable";
import { DateRangeFilter } from "@/components/DateRangeFilter";

import { useState, useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { DateRange } from "@/types";
import "../page.scss";

interface InsertionOrderMetrics {
  approved_orders: {
    count: number;
    change_percent: number;
    trend: string;
  };
  pending_approval_orders: {
    count: number;
    change_this_week: number;
    trend: string;
  };
  draft_orders: {
    count: number;
    change_this_week: number;
    trend: string;
  };
  rejected_orders: {
    count: number;
    change_this_week: number;
    trend: string;
  };
  total_orders: {
    count: number;
    change_this_month: number;
    trend: string;
  };
}

export default function InsertionOrdersPage() {
  const [dateRange, setDateRange] = useState<DateRange | null>(null);
  const [isExporting, setIsExporting] = useState(false);
  const [metrics, setMetrics] = useState<InsertionOrderMetrics | null>(null);
  const [isLoadingMetrics, setIsLoadingMetrics] = useState(true);
  const searchParams = useSearchParams();

  // Get status filter from URL parameters
  const statusFromUrl = searchParams.get('status') as 'all' | 'draft' | 'pending_approval' | 'approved' | 'rejected' | null;
  const initialStatusFilter = statusFromUrl || 'all';

  // Fetch insertion order metrics on component mount
  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        setIsLoadingMetrics(true);
        // Use the configured API URL from environment
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const response = await fetch(`${apiUrl}/api/insertion-orders-metrics`, {
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
        console.error("Error fetching insertion order metrics:", err);
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
      const csvContent = `Insertion Order Name,Status,Budget,Spent,Remaining,Days Left,Campaign Count
Insertion Order Export Data - ${new Date().toISOString().split('T')[0]}`;

      const blob = new Blob([csvContent], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `insertion-orders-export-${new Date().toISOString().split('T')[0]}.csv`;
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
          <h1>Insertion Orders</h1>
          <p>Monitor and manage your insertion orders</p>
        </div>
        <div className="flex items-center space-x-3">
          <DateRangeFilter
            onDateRangeChange={handleDateRangeChange}
            onExport={handleExport}
            isExporting={isExporting}
          />
        </div>
      </div>

      {/* Insertion Order Metrics Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 mb-6">
        {/* Approved Orders */}
        <div className="bg-white rounded-lg p-4 border border-gray-200">
          <div className="flex items-start space-x-3">
            {/* Icon positioned to the left */}
            <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center flex-shrink-0 mt-1">
              <svg className="w-5 h-5 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
              </svg>
            </div>

            {/* Content to the right */}
            <div className="flex-1 min-w-0">
              <div className="text-md text-gray-600 font-medium mb-2">
                Approved Orders
              </div>
              {isLoadingMetrics ? (
                <div className="space-y-2">
                  <div className="h-8 bg-gray-200 rounded w-12 animate-pulse"></div>
                  <div className="h-4 bg-gray-200 rounded w-16 animate-pulse"></div>
                </div>
              ) : (
                <>
                  <div className="text-4xl font-medium text-gray-900 mb-1">
                    {metrics?.approved_orders.count || 0}
                  </div>
                  <div className={`text-xs font-medium ${
                    metrics?.approved_orders.trend === 'up' ? 'text-green-600' :
                    metrics?.approved_orders.trend === 'down' ? 'text-red-600' : 'text-gray-600'
                  }`}>
                    {metrics?.approved_orders.change_percent !== undefined && metrics.approved_orders.change_percent !== 0 ? (
                      `${metrics.approved_orders.change_percent > 0 ? '+' : ''}${metrics.approved_orders.change_percent}% ${
                        metrics.approved_orders.trend === 'up' ? '↗' : metrics.approved_orders.trend === 'down' ? '↘' : ''
                      }`
                    ) : 'No change'}
                  </div>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Pending Approval Orders */}
        <div className="bg-white rounded-lg p-4 border border-gray-200">
          <div className="flex items-start space-x-3">
            {/* Icon positioned to the left */}
            <div className="w-8 h-8 bg-yellow-100 rounded-full flex items-center justify-center flex-shrink-0 mt-1">
              <svg className="w-5 h-5 text-yellow-600" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
              </svg>
            </div>

            {/* Content to the right */}
            <div className="flex-1 min-w-0">
              <div className="text-md text-gray-600 font-medium mb-2">
                Pending Approval
              </div>
              {isLoadingMetrics ? (
                <div className="space-y-2">
                  <div className="h-8 bg-gray-200 rounded w-12 animate-pulse"></div>
                  <div className="h-4 bg-gray-200 rounded w-20 animate-pulse"></div>
                </div>
              ) : (
                <>
                  <div className="text-4xl font-medium text-gray-900 mb-1">
                    {metrics?.pending_approval_orders.count || 0}
                  </div>
                  <div className={`text-xs font-medium ${
                    metrics?.pending_approval_orders.change_this_week !== undefined && metrics.pending_approval_orders.change_this_week > 0 ? 'text-yellow-600' :
                    metrics?.pending_approval_orders.change_this_week !== undefined && metrics.pending_approval_orders.change_this_week < 0 ? 'text-green-600' : 'text-gray-600'
                  }`}>
                    {metrics?.pending_approval_orders.change_this_week !== undefined && metrics.pending_approval_orders.change_this_week !== 0 ? (
                      `${metrics.pending_approval_orders.change_this_week > 0 ? '+' : ''}${metrics.pending_approval_orders.change_this_week} this week`
                    ) : 'No change this week'}
                  </div>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Draft Orders */}
        <div className="bg-white rounded-lg p-4 border border-gray-200">
          <div className="flex items-start space-x-3">
            {/* Icon positioned to the left */}
            <div className="w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center flex-shrink-0 mt-1">
              <svg className="w-5 h-5 text-gray-600" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z" clipRule="evenodd" />
              </svg>
            </div>

            {/* Content to the right */}
            <div className="flex-1 min-w-0">
              <div className="text-md text-gray-600 font-medium mb-2">
                Draft Orders
              </div>
              {isLoadingMetrics ? (
                <div className="space-y-2">
                  <div className="h-8 bg-gray-200 rounded w-12 animate-pulse"></div>
                  <div className="h-4 bg-gray-200 rounded w-20 animate-pulse"></div>
                </div>
              ) : (
                <>
                  <div className="text-4xl font-medium text-gray-900 mb-1">
                    {metrics?.draft_orders.count || 0}
                  </div>
                  <div className={`text-xs font-medium ${
                    metrics?.draft_orders.change_this_week !== undefined && metrics.draft_orders.change_this_week > 0 ? 'text-gray-600' :
                    metrics?.draft_orders.change_this_week !== undefined && metrics.draft_orders.change_this_week < 0 ? 'text-green-600' : 'text-gray-600'
                  }`}>
                    {metrics?.draft_orders.change_this_week !== undefined && metrics.draft_orders.change_this_week !== 0 ? (
                      `${metrics.draft_orders.change_this_week > 0 ? '+' : ''}${metrics.draft_orders.change_this_week} this week`
                    ) : 'No change this week'}
                  </div>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Rejected Orders */}
        <div className="bg-white rounded-lg p-4 border border-gray-200">
          <div className="flex items-start space-x-3">
            {/* Icon positioned to the left */}
            <div className="w-8 h-8 bg-red-100 rounded-full flex items-center justify-center flex-shrink-0 mt-1">
              <svg className="w-5 h-5 text-red-600" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
              </svg>
            </div>

            {/* Content to the right */}
            <div className="flex-1 min-w-0">
              <div className="text-md text-gray-600 font-medium mb-2">
                Rejected Orders
              </div>
              {isLoadingMetrics ? (
                <div className="space-y-2">
                  <div className="h-8 bg-gray-200 rounded w-12 animate-pulse"></div>
                  <div className="h-4 bg-gray-200 rounded w-20 animate-pulse"></div>
                </div>
              ) : (
                <>
                  <div className="text-4xl font-medium text-gray-900 mb-1">
                    {metrics?.rejected_orders.count || 0}
                  </div>
                  <div className={`text-xs font-medium ${
                    (metrics?.rejected_orders.change_this_week || 0) > 0 ? 'text-red-600' :
                    (metrics?.rejected_orders.change_this_week || 0) < 0 ? 'text-green-600' : 'text-gray-600'
                  }`}>
                    {metrics?.rejected_orders.change_this_week !== undefined && metrics.rejected_orders.change_this_week !== 0 ? (
                      `${metrics.rejected_orders.change_this_week > 0 ? '+' : ''}${metrics.rejected_orders.change_this_week} this week`
                    ) : 'No change this week'}
                  </div>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Total Orders */}
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
                Total Orders
              </div>
              {isLoadingMetrics ? (
                <div className="space-y-2">
                  <div className="h-8 bg-gray-200 rounded w-12 animate-pulse"></div>
                  <div className="h-4 bg-gray-200 rounded w-20 animate-pulse"></div>
                </div>
              ) : (
                <>
                  <div className="text-4xl font-medium text-gray-900 mb-1">
                    {metrics?.total_orders.count || 0}
                  </div>
                  <div className="text-xs text-blue-600 font-medium">
                    {metrics?.total_orders.change_this_month !== undefined && metrics.total_orders.change_this_month > 0 ? (
                      `+${metrics.total_orders.change_this_month} this month`
                    ) : 'No new orders this month'}
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
          defaultTab="insertion_orders"
          showTabs={false}
          showStatusTabs={true}
          initialStatusFilter={initialStatusFilter}
        />
      </div>
    </main>
  );
}
