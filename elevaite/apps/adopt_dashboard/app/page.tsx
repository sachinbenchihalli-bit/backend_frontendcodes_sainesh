"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AlertCircle, Loader2 } from "lucide-react";
// import { CampaignChart } from "@/components/CampaignChart"; // Commented out for now
import { CampaignTable } from "@/components/CampaignTable";
import { DateRangeFilter } from "@/components/DateRangeFilter";
import { BookmarkIcon, CampaignIcon } from "@/components/icons";
import InsightCard from "@/components/InsightCard";

import { useDashboardOverview } from "@/hooks/useApi";
import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { DateRange } from "@/types";
import "./page.scss";


export default function HomePage() {
  const [dateRange, setDateRange] = useState<DateRange | null>(null);
  const [isExporting, setIsExporting] = useState(false);
  const { data: overview, isLoading, error } = useDashboardOverview();
  const mainRef = useRef<HTMLElement>(null);
  const router = useRouter();

  // Navigation functions for Key Insights
  const navigateToInsertionOrders = (status?: string) => {
    const url = status ? `/insertion-orders?status=${status}` : '/insertion-orders';
    router.push(url);
  };

  const navigateToCampaigns = (status?: string) => {
    const url = status ? `/campaigns?status=${status}` : '/campaigns';
    router.push(url);
  };

  // Test API connection on component mount
  useEffect(() => {
    const testApi = async () => {
      try {
        // Use the configured API URL from environment
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const response = await fetch(`${apiUrl}/api/health`);
        await response.json();
      } catch (err) {
        console.log("Error occured at {", err, "}");
      }
    };
    testApi();
  }, []);

  // Reset scroll position when component mounts
  useEffect(() => {
    if (mainRef.current) {
      mainRef.current.scrollTop = 0;
    }
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
${overview ? `
Total Active Campaigns,${overview.total_campaigns_active}
Total Spend,$${overview.total_spend}
Total Impressions,${overview.total_impressions}
Total Clicks,${overview.total_clicks}
Average CTR,${overview.average_ctr.toFixed(2)}%
Average ROAS,${overview.average_roas.toFixed(1)}x
Success Rate,${overview.success_rate.toFixed(1)}%
` : 'No data available'}`;

      const blob = new Blob([csvContent], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `campaign-dashboard-export-${new Date().toISOString().split('T')[0]}.csv`;
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

  if (error) {
    return (
      <div className="adopt-dashboard-container">
        <div className="error">
          <AlertCircle className="h-8 w-8 mr-4" />
          <div>
            <h3 className="text-lg font-semibold mb-2">Failed to load dashboard data</h3>
            <p>Please try refreshing the page.</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <main
      ref={mainRef}
      className="adopt-dashboard-container"
      style={{
        height: '100%',
        width: '100%',
        overflow: 'auto'
      }}>
      {/* Title and Filters Section */}
      <div className="title-filters-section flex justify-between items-start">
        <div className="title-content">
          <h1>Command Agent Workflows</h1>
          <p>Monitor your insertion order, campaigns, and performance metrics</p>
        </div>
        <DateRangeFilter
          onDateRangeChange={handleDateRangeChange}
          onExport={handleExport}
          isExporting={isExporting}
        />
      </div>



      {/* Key Insights Section */}
      <div className="key-insights-section">
        <Card className="insights-card">
          <CardHeader className="pb-4">
            <CardTitle className="insights-title">Key Insights</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Total Insertion Orders */}
              <InsightCard
                icon={<BookmarkIcon className="w-5 h-5" />}
                title="Total Insertion Orders"
                value={overview?.total_insertion_orders || 0}
                description=""
                isLoading={isLoading}
                iconBgColor="bg-blue-100"
                iconColor="text-blue-600"
                descriptionColor="text-blue-600"
                isClickable={true}
                onClick={() => navigateToInsertionOrders()}
              />

              {/* Insertion Orders Pending Approval */}
              <InsightCard
                icon={
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
                  </svg>
                }
                title="Insertion Orders Pending Approval"
                value={overview?.io_pending_approval || 0}
                description="Awaiting approval"
                isLoading={isLoading}
                iconBgColor="bg-yellow-100"
                iconColor="text-yellow-600"
                descriptionColor="text-yellow-600"
                isClickable={true}
                onClick={() => navigateToInsertionOrders('pending_approval')}
              />

              {/* Approved Insertion Orders */}
              <InsightCard
                icon={
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                }
                title="Approved Insertion Orders"
                value={overview?.io_approved || 0}
                description="Approval Granted"
                isLoading={isLoading}
                iconBgColor="bg-green-100"
                iconColor="text-green-600"
                descriptionColor="text-green-600"
                isClickable={true}
                onClick={() => navigateToInsertionOrders('approved')}
              />

              {/* Rejected Insertion Orders */}
              <InsightCard
                icon={
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                  </svg>
                }
                title="Rejected Insertion Orders"
                value={overview?.io_rejected || 0}
                description="Require revision"
                isLoading={isLoading}
                iconBgColor="bg-red-100"
                iconColor="text-red-600"
                descriptionColor="text-red-600"
                isClickable={true}
                onClick={() => navigateToInsertionOrders('rejected')}
              />

              {/* Active Campaigns */}
              <InsightCard
                icon={<CampaignIcon className="w-5 h-5" />}
                title="Active Campaigns"
                value={overview?.total_campaigns_active || 0}
                description=""
                isLoading={isLoading}
                iconBgColor="bg-green-100"
                iconColor="text-green-600"
                descriptionColor="text-green-600"
                isClickable={true}
                onClick={() => navigateToCampaigns('active')}
              />

              {/* Work in Progress Campaigns */}
              <InsightCard
                icon={
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z" clipRule="evenodd" />
                  </svg>
                }
                title="Work in Progress Campaigns"
                value={overview?.campaigns_wip || 0}
                description="Currently being configured"
                isLoading={isLoading}
                iconBgColor="bg-orange-100"
                iconColor="text-orange-600"
                descriptionColor="text-orange-600"
                isClickable={true}
                onClick={() => navigateToCampaigns('work_in_progress')}
              />

              {/* Paused Campaigns */}
              <InsightCard
                icon={
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM7 8a1 1 0 012 0v4a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v4a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
                  </svg>
                }
                title="Paused Campaigns"
                value={overview?.campaigns_paused || 0}
                description="Temporarily halted"
                isLoading={isLoading}
                iconBgColor="bg-blue-100"
                iconColor="text-blue-600"
                descriptionColor="text-blue-600"
                isClickable={true}
                onClick={() => navigateToCampaigns('paused')}
              />

              {/* Completed Campaigns */}
              <InsightCard
                icon={
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                }
                title="Completed Campaigns"
                value={overview?.campaigns_completed || 0}
                description="Successfully finished"
                isLoading={isLoading}
                iconBgColor="bg-green-100"
                iconColor="text-green-600"
                descriptionColor="text-green-600"
                isClickable={true}
                onClick={() => navigateToCampaigns('completed')}
              />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Content */}
      <div className="main-content-section space-y-6">
        <div className="content-card">
          <CampaignTable defaultTab="insertion_orders" />
        </div>
        {/* Campaigns Overall Performance - Commented out for now
        <div className="content-card">
          <CampaignChart />
        </div>
        */}

      </div>
    </main>
  );
}