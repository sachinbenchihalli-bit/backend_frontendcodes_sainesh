import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import Link from "next/link";
import { Search, Loader2, AlertCircle, ChevronLeft, ChevronRight, RefreshCw, CheckCircle, AlertTriangle, MoreVertical } from "lucide-react";
import { useCampaigns, useCampaignFilters, useInsertionOrders } from "@/hooks/useApi";
import { useState, useMemo, useEffect } from "react";
import { Campaign, CampaignFilters, InsertionOrder, KevelFlightStatus } from "@/types";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuItem,
} from "@/components/ui/dropdown-menu";

import { api } from "@/services/api";

interface CampaignTableProps {
  defaultTab?: 'campaigns' | 'insertion_orders';
  showTabs?: boolean;
  showStatusTabs?: boolean;
  initialStatusFilter?: 'all' | 'active' | 'work_in_progress' | 'paused' | 'completed' | 'draft' | 'pending_approval' | 'approved' | 'rejected';
}

export const CampaignTable = ({ defaultTab = 'campaigns', showTabs = true, showStatusTabs = false, initialStatusFilter = 'all' }: CampaignTableProps) => {
  const [currentPage, setCurrentPage] = useState(1);
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'work_in_progress' | 'paused' | 'completed' | 'draft' | 'pending_approval' | 'approved' | 'rejected'>(initialStatusFilter);
  const [activeTab, setActiveTab] = useState<'campaigns' | 'insertion_orders'>(defaultTab);
  const [limit, setLimit] = useState(100);

  // Column visibility state for campaigns
  const [visibleColumns, setVisibleColumns] = useState({
    name: true,
    brand: true,
    start_date: true,
    end_date: true,
    budget: true,
    target_impressions: true,
    target_clicks: true,
    delivered_impressions: true,
    delivered_clicks: true,
    ctr: true,
    status: true,
    roas: false,
    conversions: false,
    spend: false,
    cpm: false,
    cpc: false,
    platform_channel: false,
    campaign_objective: false,
    audience_segment: false,
    creative_type: false,
    navigate_to_campaign: true,
  });

  // Function to toggle column visibility
  const toggleColumn = (columnKey: string) => {
    setVisibleColumns(prev => ({
      ...prev,
      [columnKey]: !prev[columnKey as keyof typeof prev]
    }));
  };

  // Kevel integration state
  const [kevelData, setKevelData] = useState<Map<string, KevelFlightStatus>>(new Map());
  const [kevelLoading, setKevelLoading] = useState(false);
  const [kevelError, setKevelError] = useState<string | null>(null);
  const [lastKevelSync, setLastKevelSync] = useState<Date | null>(null);

  // Reset pagination when limit or search changes
  useEffect(() => {
    setCurrentPage(1);
  }, [limit, searchTerm]);

  // Build filters object
  const filters: CampaignFilters = useMemo(() => {
    const result: CampaignFilters = {};

    if (searchTerm) {
      result.search = searchTerm;
    }

    if (statusFilter !== 'all') {
      // Map the simplified status filter to actual statuses
      // Different mappings for campaigns vs insertion orders
      const campaignStatusMapping: Record<string, string[]> = {
        'active': ['active', 'live', 'in_progress'],
        'work_in_progress': ['work_in_progress', 'pending_approval', 'shell_created'],
        'paused': ['paused'],
        'completed': ['completed']
      };

      const insertionOrderStatusMapping: Record<string, string[]> = {
        'draft': ['draft'],
        'pending_approval': ['pending_approval', 'pending', 'pending approval', 'awaiting_approval'],
        'approved': ['approved', 'active', 'live'],
        'rejected': ['rejected', 'declined', 'cancelled']
      };

      const statusMapping = activeTab === 'campaigns' ? campaignStatusMapping : insertionOrderStatusMapping;
      result.status = statusMapping[statusFilter] || [statusFilter];
    }

    return result;
  }, [searchTerm, statusFilter, activeTab]);

  const { data: campaignsData, isLoading: campaignsLoading, error: campaignsError } = useCampaigns(currentPage, limit, filters);
  const { data: insertionOrdersData, isLoading: insertionOrdersLoading, error: insertionOrdersError } = useInsertionOrders(currentPage, limit, filters);

  // Determine which data to use based on active tab
  const currentData = activeTab === 'campaigns' ? campaignsData : insertionOrdersData;
  const isLoading = activeTab === 'campaigns' ? campaignsLoading : insertionOrdersLoading;
  const error = activeTab === 'campaigns' ? campaignsError : insertionOrdersError;

  // Calculate total pages from current data mapping to limit (e.g. 1000)
  const totalEntriesForPagination = currentData?.limit || 0;
  const totalPages = totalEntriesForPagination > 0 ? Math.ceil(totalEntriesForPagination / limit) : 0;

  // FIX: useMemo for dynamic pages must be called unconditionally outside of JSX or if-statements
  const dynamicPageButtons = useMemo(() => {
    const pages = [];
    const maxVisible = 5;
    let startPage = Math.max(1, currentPage - Math.floor(maxVisible / 2));
    let endPage = startPage + maxVisible - 1;

    if (endPage > totalPages) {
      endPage = totalPages;
      startPage = Math.max(1, endPage - maxVisible + 1);
    }

    for (let i = startPage; i <= endPage; i++) {
      pages.push(
        <Button
          key={i}
          variant="outline"
          size="sm"
          onClick={() => setCurrentPage(i)}
          disabled={isLoading}
          className={`w-8 h-8 p-0 ${i === currentPage
            ? "border-orange-500 text-orange-500 bg-white hover:bg-orange-50"
            : "border-gray-300 text-gray-600 hover:border-gray-400 hover:bg-gray-100"
          }`}
        >
          {i}
        </Button>
      );
    }
    return pages;
  }, [currentPage, totalPages, isLoading]);

  // Reset pagination when switching tabs
  useEffect(() => {
    setCurrentPage(1);
  }, [activeTab]);

  // Fetch Kevel data for campaigns with kevel_id
  const fetchKevelData = async (campaigns: Campaign[]) => {
    if (activeTab !== 'campaigns') return; // Only fetch for campaigns tab

    setKevelLoading(true);
    setKevelError(null);

    try {
      const campaignsWithKevelId = campaigns.filter(campaign => campaign.kevel_id);

      if (campaignsWithKevelId.length === 0) {
        setKevelData(new Map());
        setKevelLoading(false);
        return;
      }

      console.log(`Fetching Kevel data for ${campaignsWithKevelId.length} campaigns...`);

      // Fetch Kevel data for each campaign with kevel_id
      const kevelPromises = campaignsWithKevelId.map(async (campaign) => {
        try {
          const response = await api.campaigns.getKevelCampaignStatus(campaign.kevel_id!, 30); // Last 30 days
          return {
            campaignId: campaign.id,
            kevelId: campaign.kevel_id!,
            data: response.data
          };
        } catch (error) {
          console.warn(`Failed to fetch Kevel data for campaign ${campaign.name} (${campaign.kevel_id}):`, error);
          return null;
        }
      });

      const kevelResults = await Promise.allSettled(kevelPromises);
      const newKevelData = new Map<string, KevelFlightStatus>();

      kevelResults.forEach((result) => {
        if (result.status === 'fulfilled' && result.value) {
          newKevelData.set(result.value.campaignId, result.value.data);
        }
      });

      setKevelData(newKevelData);
      setLastKevelSync(new Date());
      console.log(`Successfully fetched Kevel data for ${newKevelData.size} campaigns`);

    } catch (error) {
      console.error('Error fetching Kevel data:', error);
      setKevelError('Failed to fetch Kevel data');
    } finally {
      setKevelLoading(false);
    }
  };

  // Auto-fetch Kevel data when campaigns data changes
  useEffect(() => {
    if (campaignsData?.data && activeTab === 'campaigns') {
      console.log('Campaigns data received:', campaignsData.data);
      console.log('Campaigns with kevel_id:', campaignsData.data.filter(c => c.kevel_id));
      fetchKevelData(campaignsData.data);
    }
  }, [campaignsData?.data, activeTab]);

  // Manual refresh function with sync
  const handleRefreshKevelData = async () => {
    if (!campaignsData?.data) return;

    setKevelLoading(true);
    setKevelError(null);

    try {
      // First sync all campaigns with Kevel to update database
      const campaignsWithKevelId = campaignsData.data.filter(campaign => campaign.kevel_id);

      if (campaignsWithKevelId.length > 0) {
        console.log(`Syncing ${campaignsWithKevelId.length} campaigns with Kevel...`);

        // Sync each campaign with Kevel (this updates the database)
        const syncPromises = campaignsWithKevelId.map(async (campaign) => {
          try {
            const syncResult = await api.campaigns.syncCampaignWithKevel(campaign.id, 30);
            console.log(`Synced campaign ${campaign.name}:`, syncResult);
            return { campaignId: campaign.id, success: true, result: syncResult };
          } catch (error) {
            console.warn(`Failed to sync campaign ${campaign.name}:`, error);
            return { campaignId: campaign.id, success: false, error };
          }
        });

        const syncResults = await Promise.allSettled(syncPromises);
        const successfulSyncs = syncResults.filter(result =>
          result.status === 'fulfilled' && (result.value as any).success
        ).length;

        console.log(`Successfully synced ${successfulSyncs}/${campaignsWithKevelId.length} campaigns`);
      }

      // Then fetch updated Kevel data for display
      await fetchKevelData(campaignsData.data);

    } catch (error) {
      console.error('Error during Kevel sync and refresh:', error);
      setKevelError('Failed to sync with Kevel');
    } finally {
      setKevelLoading(false);
    }
  };

  // Helper functions
  const formatCurrency = (amount: number | null): string => {
    if (amount === null || amount === undefined) return 'N/A';
    if (amount >= 1000000) {
      return '$' + (amount / 1000000).toFixed(1) + 'M';
    } else if (amount >= 1000) {
      return '$' + (amount / 1000).toFixed(1) + 'k';
    }
    return '$' + amount.toLocaleString();
  };

  const formatPercentage = (value: number | null): string => {
    if (value === null || value === undefined) return 'N/A';
    return value.toFixed(2) + '%';
  };

  const formatRoas = (value: number | null): string => {
    if (value === null || value === undefined) return 'N/A';
    return value.toFixed(1) + 'x';
  };

  const formatDate = (dateString: string): string => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  };

  const getTargetClicks = (campaign: Campaign): number => {
    // Use booked_clicks from campaign_placements (target clicks)
    return campaign.booked_clicks || 0;
  };

  // Kevel comparison helpers
  const hasKevelData = (campaign: Campaign): boolean => {
    return !!campaign.kevel_id && kevelData.has(campaign.id);
  };

  const getKevelData = (campaign: Campaign): KevelFlightStatus | null => {
    return kevelData.get(campaign.id) || null;
  };

  const hasDiscrepancy = (campaign: Campaign): boolean => {
    const kevel = getKevelData(campaign);
    if (!kevel) return false;

    const impressionDiff = Math.abs(campaign.impressions_delivered - kevel.impressions);
    const clickDiff = Math.abs(campaign.clicks - kevel.clicks);

    // Consider significant if difference is > 5% or > 100 impressions/10 clicks
    const impressionThreshold = Math.max(campaign.impressions_delivered * 0.05, 100);
    const clickThreshold = Math.max(campaign.clicks * 0.05, 10);

    return impressionDiff > impressionThreshold || clickDiff > clickThreshold;
  };

  const renderKevelStatus = (campaign: Campaign): JSX.Element => {
    if (!campaign.kevel_id) {
      return (
        <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-gray-100 text-gray-500">
          No Kevel ID
        </span>
      );
    }

    if (kevelLoading) {
      return (
        <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-blue-100 text-blue-600">
          <Loader2 className="w-3 h-3 mr-1 animate-spin" />
          Syncing...
        </span>
      );
    }

    if (!hasKevelData(campaign)) {
      return (
        <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-red-100 text-red-600">
          <AlertTriangle className="w-3 h-3 mr-1" />
          Sync Failed
        </span>
      );
    }

    if (hasDiscrepancy(campaign)) {
      return (
        <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-yellow-100 text-yellow-700">
          <AlertTriangle className="w-3 h-3 mr-1" />
          Discrepancy
        </span>
      );
    }

    return (
      <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-green-100 text-green-700">
        <CheckCircle className="w-3 h-3 mr-1" />
        In Sync
      </span>
    );
  };

  const renderKevelComparison = (campaign: Campaign, field: 'impressions' | 'clicks'): JSX.Element => {
    const kevel = getKevelData(campaign);
    if (!kevel) return <span className="text-gray-400">-</span>;

    const localValue = field === 'impressions' ? campaign.impressions_delivered : campaign.clicks;
    const kevelValue = field === 'impressions' ? kevel.impressions : kevel.clicks;
    const diff = kevelValue - localValue;
    const diffPercent = localValue > 0 ? ((diff / localValue) * 100) : 0;

    return (
      <div className="flex flex-col">
        <span className="font-medium">{localValue.toLocaleString()}</span>
        <span className={`text-xs ${Math.abs(diffPercent) > 5 ? 'text-red-600' : 'text-gray-500'}`}>
          Kevel: {kevelValue.toLocaleString()}
          {diff !== 0 && (
            <span className={diff > 0 ? 'text-green-600' : 'text-red-600'}>
              {' '}({diff > 0 ? '+' : ''}{diff.toLocaleString()})
            </span>
          )}
        </span>
      </div>
    );
  };

  const renderSalesforceLink = (salesforceId: string | null | undefined): JSX.Element => {
    if (!salesforceId) {
      return (
        <span className="inline-block px-2 py-1 rounded text-xs font-semibold bg-gray-100 text-gray-500 border border-gray-200">
          No Link
        </span>
      );
    }

    const salesforceBaseUrl = process.env.NEXT_PUBLIC_SALESFORCE_BASE_URL || 'https://iopextechnologies3-dev-ed.develop.lightning.force.com';
    const salesforceUrl = `${salesforceBaseUrl}/lightning/r/Insertion_Order__c/${salesforceId}/view`;

    return (
      <a
        href={salesforceUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center px-2 py-1 rounded text-xs font-semibold bg-blue-100 text-blue-700 border border-blue-200 hover:bg-blue-200 transition-colors"
        title={`View in Salesforce: ${salesforceId}`}
      >
        <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M12.586 4.586a2 2 0 112.828 2.828l-3 3a2 2 0 01-2.828 0 1 1 0 00-1.414 1.414 4 4 0 005.656 0l3-3a4 4 0 00-5.656-5.656l-1.5 1.5a1 1 0 101.414 1.414l1.5-1.5z" clipRule="evenodd" />
          <path fillRule="evenodd" d="M7.414 15.414a2 2 0 01-2.828-2.828l3-3a2 2 0 012.828 0 1 1 0 001.414-1.414 4 4 0 00-5.656 0l-3 3a4 4 0 105.656 5.656l1.5-1.5a1 1 0 00-1.414-1.414l-1.5 1.5z" clipRule="evenodd" />
        </svg>
        View
      </a>
    );
  };

  const renderMediaPlanLink = (mediaPlanUrl: string | null | undefined): JSX.Element => {
    if (!mediaPlanUrl) {
      return (
        <span className="inline-block px-2 py-1 rounded text-xs font-semibold bg-gray-100 text-gray-500 border border-gray-200">
          No Link
        </span>
      );
    }

    return (
      <a
        href={mediaPlanUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center px-2 py-1 rounded text-xs font-semibold bg-green-100 text-green-700 border border-green-200 hover:bg-green-200 transition-colors"
        title="View Media Plan"
      >
        <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M12.586 4.586a2 2 0 112.828 2.828l-3 3a2 2 0 01-2.828 0 1 1 0 00-1.414 1.414 4 4 0 005.656 0l3-3a4 4 0 00-5.656-5.656l-1.5 1.5a1 1 0 101.414 1.414l1.5-1.5z" clipRule="evenodd" />
          <path fillRule="evenodd" d="M7.414 15.414a2 2 0 01-2.828-2.828l3-3a2 2 0 012.828 0 1 1 0 001.414-1.414 4 4 0 00-5.656 0l-3 3a4 4 0 105.656 5.656l1.5-1.5a1 1 0 00-1.414-1.414l-1.5 1.5z" clipRule="evenodd" />
        </svg>
        View
      </a>
    );
  };

  const renderKevelLink = (kevelId: string | null | undefined): JSX.Element => {
    if (!kevelId) {
      return (
        <span className="inline-block px-2 py-1 rounded text-xs font-semibold bg-gray-100 text-gray-500 border border-gray-200">
          No Kevel ID
        </span>
      );
    }

    // Campaign-level Kevel URL (this was working fine)
    const kevelUrl = `https://app.kevel.co/#!/11679/campaign/${kevelId}/flights/`;

    return (
      <a
        href={kevelUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center px-2 py-1 rounded text-xs font-semibold bg-purple-100 text-purple-700 border border-purple-200 hover:bg-purple-200 transition-colors"
        title={`View in Kevel: ${kevelId}`}
      >
        <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M12.586 4.586a2 2 0 112.828 2.828l-3 3a2 2 0 01-2.828 0 1 1 0 00-1.414 1.414 4 4 0 005.656 0l3-3a4 4 0 00-5.656-5.656l-1.5 1.5a1 1 0 101.414 1.414l1.5-1.5z" clipRule="evenodd" />
          <path fillRule="evenodd" d="M7.414 15.414a2 2 0 01-2.828-2.828l3-3a2 2 0 012.828 0 1 1 0 001.414-1.414 4 4 0 00-5.656 0l-3 3a4 4 0 105.656 5.656l1.5-1.5a1 1 0 00-1.414-1.414l-1.5 1.5z" clipRule="evenodd" />
        </svg>
        View Campaign
      </a>
    );
  };

  const getStatusColor = (status: string): string => {
    const normalizedStatus = status.toLowerCase();
    switch (normalizedStatus) {
      case 'live':
      case 'approved':
        return 'bg-green-100 text-green-700 border-green-200';
      case 'paused':
        return 'bg-red-100 text-red-700 border-red-200';
      case 'completed':
        return 'bg-blue-100 text-blue-700 border-blue-200';
      case 'draft':
      case 'created':
        return 'bg-gray-100 text-gray-700 border-gray-200';
      case 'pending_approval':
      case 'pending approval':
        return 'bg-yellow-100 text-yellow-700 border-yellow-200';
      case 'in_progress':
        return 'bg-green-100 text-green-700 border-green-200';
      case 'cancelled':
        return 'bg-red-100 text-red-700 border-red-200';
      case 'work_in_progress':
        return 'bg-yellow-100 text-yellow-700 border-yellow-200';
      case 'shell_created':
        return 'bg-gray-100 text-gray-700 border-gray-200';
      case 'rejected':
        return 'bg-red-100 text-red-700 border-red-200';
      default:
        return 'bg-gray-100 text-gray-700 border-gray-200';
    }
  };

  const formatStatusDisplay = (status: string): string => {
    const normalizedStatus = status.toLowerCase();
    switch (normalizedStatus) {
      case 'work_in_progress':
        return 'WIP';
      default:
        return status;
    }
  };

  const getIssueDetected = (campaign: Campaign): string => {
    if (campaign.roas < 2.0) {
      return 'Low ROAS performance';
    }
    if (campaign.ctr < 1) {
      return 'Low click-through rate';
    }
    if (campaign.spend / campaign.budget > 0.8) {
      return 'High budget utilization';
    }
    return 'Performance within targets';
  };

  const getSuggestedAction = (campaign: Campaign): string => {
    if (campaign.roas < 2.0) {
      return 'Optimize targeting and creatives';
    }
    if (campaign.ctr < 1) {
      return 'A/B test new creatives';
    }
    if (campaign.spend / campaign.budget > 0.8) {
      return 'Monitor budget pacing';
    }
    return 'Continue monitoring';
  };



  if (error) {
    return (
      <Card className="bg-white shadow-sm border border-gray-200">
        <CardContent className="p-6">
          <Alert>
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              Failed to load campaigns data. Please try refreshing the page.
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header Section - Outside the box */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          {!showStatusTabs && <h3 className="text-xl font-bold text-gray-900">Workflows</h3>}
          {activeTab === 'campaigns' && (
            <div className="flex items-center space-x-2 text-sm text-gray-600">
              {kevelLoading && (
                <span className="flex items-center">
                  <Loader2 className="w-4 h-4 mr-1 animate-spin" />
                  Syncing & Updating from Ad Servers...
                </span>
              )}
              {lastKevelSync && !kevelLoading && (
                <span>
                  Last sync: {lastKevelSync.toLocaleTimeString()}
                </span>
              )}
              {kevelError && (
                <span className="text-red-600 flex items-center">
                  <AlertTriangle className="w-4 h-4 mr-1" />
                  {kevelError}
                </span>
              )}
            </div>
          )}
        </div>
        {!showTabs && !showStatusTabs && (
          <div className="flex items-center space-x-3">
            {activeTab === 'campaigns' && (
              <Button
                onClick={handleRefreshKevelData}
                disabled={kevelLoading}
                variant="outline"
                size="sm"
                className="flex items-center space-x-2"
              >
                <RefreshCw className={`w-4 h-4 ${kevelLoading ? 'animate-spin' : ''}`} />
                <span>Sync & Update from Ad Server</span>
              </Button>
            )}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
              <Input
                placeholder="Search"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 w-64 border-gray-300 focus:border-orange-500 focus:ring-orange-500 rounded-full"
              />
            </div>
          </div>
        )}
      </div>

      {/* Tabs Section - Outside the box */}
      {showTabs && (
        <div className="flex items-center justify-between">
          <div className="flex space-x-1 bg-[#DEE3ED] p-1 rounded-lg w-fit">
            <Button
              variant="ghost"
              onClick={() => setActiveTab('insertion_orders')}
              className={`rounded-lg px-12 py-3 font-medium text-sm hover:bg-white hover:text-orange-600 hover:shadow-sm transition-all duration-150 ${
                activeTab === 'insertion_orders'
                  ? 'bg-white text-orange-600 shadow-sm'
                  : 'text-gray-600 bg-transparent'
              }`}
            >
              Insertion Orders
            </Button>
            <Button
              variant="ghost"
              onClick={() => setActiveTab('campaigns')}
              className={`rounded-lg px-12 py-3 font-medium text-sm hover:bg-white hover:text-orange-600 hover:shadow-sm transition-all duration-150 ${
                activeTab === 'campaigns'
                  ? 'bg-white text-orange-600 shadow-sm'
                  : 'text-gray-600 bg-transparent'
              }`}
            >
              Campaigns
            </Button>
          </div>
          <div className="flex items-center space-x-3">
            {activeTab === 'campaigns' && (
              <Button
                onClick={handleRefreshKevelData}
                disabled={kevelLoading}
                variant="outline"
                size="sm"
                className="flex items-center space-x-2"
              >
                <RefreshCw className={`w-4 h-4 ${kevelLoading ? 'animate-spin' : ''}`} />
                <span>Sync & Update from Ad Server</span>
              </Button>
            )}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
              <Input
                placeholder="Search"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 w-64 border-gray-300 focus:border-orange-500 focus:ring-orange-500 rounded-full"
              />
            </div>
          </div>
        </div>
      )}

      {/* Status Filter Tabs - Only show when showStatusTabs is true */}
      {showStatusTabs && (
        <div className="flex items-center justify-between">
          <div className="flex space-x-1 bg-[#DEE3ED] p-1 rounded-lg w-fit">
            <Button
              variant="ghost"
              onClick={() => setStatusFilter('all')}
              className={`rounded-lg px-12 py-3 font-medium text-sm hover:bg-white hover:text-orange-600 hover:shadow-sm transition-all duration-150 ${
                statusFilter === 'all'
                  ? 'bg-white text-orange-600 shadow-sm'
                  : 'text-gray-600 bg-transparent'
              }`}
            >
              All
            </Button>
            {activeTab === 'campaigns' ? (
              <>
                <Button
                  variant="ghost"
                  onClick={() => setStatusFilter('active')}
                  className={`rounded-lg px-12 py-3 font-medium text-sm hover:bg-white hover:text-orange-600 hover:shadow-sm transition-all duration-150 ${
                    statusFilter === 'active'
                      ? 'bg-white text-orange-600 shadow-sm'
                      : 'text-gray-600 bg-transparent'
                  }`}
                >
                  Active
                </Button>
                <Button
                  variant="ghost"
                  onClick={() => setStatusFilter('work_in_progress')}
                  className={`rounded-lg px-12 py-3 font-medium text-sm hover:bg-white hover:text-orange-600 hover:shadow-sm transition-all duration-150 ${
                    statusFilter === 'work_in_progress'
                      ? 'bg-white text-orange-600 shadow-sm'
                      : 'text-gray-600 bg-transparent'
                  }`}
                >
                  WIP
                </Button>
                <Button
                  variant="ghost"
                  onClick={() => setStatusFilter('paused')}
                  className={`rounded-lg px-12 py-3 font-medium text-sm hover:bg-white hover:text-orange-600 hover:shadow-sm transition-all duration-150 ${
                    statusFilter === 'paused'
                      ? 'bg-white text-orange-600 shadow-sm'
                      : 'text-gray-600 bg-transparent'
                  }`}
                >
                  Paused
                </Button>
                <Button
                  variant="ghost"
                  onClick={() => setStatusFilter('completed')}
                  className={`rounded-lg px-12 py-3 font-medium text-sm hover:bg-white hover:text-orange-600 hover:shadow-sm transition-all duration-150 ${
                    statusFilter === 'completed'
                      ? 'bg-white text-orange-600 shadow-sm'
                      : 'text-gray-600 bg-transparent'
                  }`}
                >
                  Completed
                </Button>
              </>
            ) : (
              <>
                <Button
                  variant="ghost"
                  onClick={() => setStatusFilter('draft')}
                  className={`rounded-lg px-12 py-3 font-medium text-sm hover:bg-white hover:text-orange-600 hover:shadow-sm transition-all duration-150 ${
                    statusFilter === 'draft'
                      ? 'bg-white text-orange-600 shadow-sm'
                      : 'text-gray-600 bg-transparent'
                  }`}
                >
                  Draft
                </Button>
                <Button
                  variant="ghost"
                  onClick={() => setStatusFilter('pending_approval')}
                  className={`rounded-lg px-12 py-3 font-medium text-sm hover:bg-white hover:text-orange-600 hover:shadow-sm transition-all duration-150 ${
                    statusFilter === 'pending_approval'
                      ? 'bg-white text-orange-600 shadow-sm'
                      : 'text-gray-600 bg-transparent'
                  }`}
                >
                  Pending Approval
                </Button>
                <Button
                  variant="ghost"
                  onClick={() => setStatusFilter('approved')}
                  className={`rounded-lg px-12 py-3 font-medium text-sm hover:bg-white hover:text-orange-600 hover:shadow-sm transition-all duration-150 ${
                    statusFilter === 'approved'
                      ? 'bg-white text-orange-600 shadow-sm'
                      : 'text-gray-600 bg-transparent'
                  }`}
                >
                  Approved
                </Button>
                <Button
                  variant="ghost"
                  onClick={() => setStatusFilter('rejected')}
                  className={`rounded-lg px-12 py-3 font-medium text-sm hover:bg-white hover:text-orange-600 hover:shadow-sm transition-all duration-150 ${
                    statusFilter === 'rejected'
                      ? 'bg-white text-orange-600 shadow-sm'
                      : 'text-gray-600 bg-transparent'
                  }`}
                >
                  Rejected
                </Button>
              </>
            )}
          </div>
          <div className="flex items-center space-x-3">
            {activeTab === 'campaigns' && (
              <Button
                onClick={handleRefreshKevelData}
                disabled={kevelLoading}
                variant="outline"
                size="sm"
                className="flex items-center space-x-2"
              >
                <RefreshCw className={`w-4 h-4 ${kevelLoading ? 'animate-spin' : ''}`} />
                <span>Sync & Update from Ad Server</span>
              </Button>
            )}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
              <Input
                placeholder="Search"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 w-64 border-gray-300 focus:border-orange-500 focus:ring-orange-500 rounded-full"
              />
            </div>
          </div>
        </div>
      )}

      {/* Table Container - White box */}
      <Card className="shadow-sm rounded-xl mt-6">
      <CardContent className="p-0">
        {isLoading ? (
          <div className="space-y-4 p-6">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="flex items-center space-x-4 py-4">
                <div className="h-4 bg-gray-200 rounded w-48 animate-pulse"></div>
                <div className="h-4 bg-gray-200 rounded w-24 animate-pulse"></div>
                <div className="h-4 bg-gray-200 rounded w-32 animate-pulse"></div>
                <div className="h-4 bg-gray-200 rounded w-20 animate-pulse"></div>
                <div className="h-4 bg-gray-200 rounded w-16 animate-pulse"></div>
                <div className="h-4 bg-gray-200 rounded w-16 animate-pulse"></div>
                <div className="h-6 bg-gray-200 rounded w-20 animate-pulse"></div>
                <div className="h-4 bg-gray-200 rounded w-32 animate-pulse"></div>
              </div>
            ))}
          </div>
        ) : (
          <div className="border border-gray-200 rounded-lg overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
              <thead>
                <tr className="bg-[#DEE3ED] border-b border-gray-200">
                  {visibleColumns.name && <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>}
                  {visibleColumns.brand && <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase tracking-wider">Brand</th>}
                  {activeTab === 'campaigns' && (
                    <>
                      {visibleColumns.start_date && <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase tracking-wider">Start Date</th>}
                      {visibleColumns.end_date && <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase tracking-wider">End Date</th>}
                      {visibleColumns.budget && <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase tracking-wider">Budget</th>}
                      {visibleColumns.target_impressions && <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase tracking-wider">Target Impressions</th>}
                      {visibleColumns.target_clicks && <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase tracking-wider">Target Clicks</th>}
                      {visibleColumns.delivered_impressions && <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase tracking-wider">Delivered Impressions</th>}
                      {visibleColumns.delivered_clicks && <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase tracking-wider">Delivered Clicks</th>}
                      {visibleColumns.ctr && <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase tracking-wider">CTR</th>}
                      {visibleColumns.roas && <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase tracking-wider">ROAS</th>}
                      {visibleColumns.conversions && <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase tracking-wider">Conversions</th>}
                      {visibleColumns.spend && <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase tracking-wider">Spend</th>}
                      {visibleColumns.cpm && <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase tracking-wider">CPM</th>}
                      {visibleColumns.cpc && <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase tracking-wider">CPC</th>}
                      {visibleColumns.platform_channel && <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase tracking-wider">Platform/Channel</th>}
                      {visibleColumns.campaign_objective && <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase tracking-wider">Campaign Objective</th>}
                      {visibleColumns.audience_segment && <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase tracking-wider">Audience Segment</th>}
                      {visibleColumns.creative_type && <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase tracking-wider">Creative Type</th>}
                      {visibleColumns.status && <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>}
                      {visibleColumns.navigate_to_campaign && <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase tracking-wider">Navigate to Campaign</th>}
                    </>
                  )}
                  {/* 3-dot menu for column selection */}
                  {activeTab === 'campaigns' && (
                    <th className="text-center py-3 px-4 text-xs font-medium text-gray-500 uppercase tracking-wider w-32">
                      <div className="flex items-center justify-center">
                        <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
                            <MoreVertical className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="w-56">
                          <DropdownMenuLabel>Show/Hide Columns</DropdownMenuLabel>
                          <DropdownMenuSeparator />
                          <div className="max-h-64 overflow-y-auto">
                            <DropdownMenuItem onClick={() => toggleColumn('name')} className="flex items-center space-x-2">
                              <Checkbox checked={visibleColumns.name} readOnly />
                              <span>Name</span>
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => toggleColumn('brand')} className="flex items-center space-x-2">
                              <Checkbox checked={visibleColumns.brand} readOnly />
                              <span>Brand</span>
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => toggleColumn('start_date')} className="flex items-center space-x-2">
                              <Checkbox checked={visibleColumns.start_date} readOnly />
                              <span>Start Date</span>
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => toggleColumn('end_date')} className="flex items-center space-x-2">
                              <Checkbox checked={visibleColumns.end_date} readOnly />
                              <span>End Date</span>
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => toggleColumn('budget')} className="flex items-center space-x-2">
                              <Checkbox checked={visibleColumns.budget} readOnly />
                              <span>Budget</span>
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => toggleColumn('target_impressions')} className="flex items-center space-x-2">
                              <Checkbox checked={visibleColumns.target_impressions} readOnly />
                              <span>Target Impressions</span>
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => toggleColumn('target_clicks')} className="flex items-center space-x-2">
                              <Checkbox checked={visibleColumns.target_clicks} readOnly />
                              <span>Target Clicks</span>
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => toggleColumn('delivered_impressions')} className="flex items-center space-x-2">
                              <Checkbox checked={visibleColumns.delivered_impressions} readOnly />
                              <span>Delivered Impressions</span>
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => toggleColumn('delivered_clicks')} className="flex items-center space-x-2">
                              <Checkbox checked={visibleColumns.delivered_clicks} readOnly />
                              <span>Delivered Clicks</span>
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => toggleColumn('ctr')} className="flex items-center space-x-2">
                              <Checkbox checked={visibleColumns.ctr} readOnly />
                              <span>CTR</span>
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => toggleColumn('roas')} className="flex items-center space-x-2">
                              <Checkbox checked={visibleColumns.roas} readOnly />
                              <span>ROAS</span>
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => toggleColumn('conversions')} className="flex items-center space-x-2">
                              <Checkbox checked={visibleColumns.conversions} readOnly />
                              <span>Conversions</span>
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => toggleColumn('spend')} className="flex items-center space-x-2">
                              <Checkbox checked={visibleColumns.spend} readOnly />
                              <span>Spend</span>
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => toggleColumn('cpm')} className="flex items-center space-x-2">
                              <Checkbox checked={visibleColumns.cpm} readOnly />
                              <span>CPM</span>
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => toggleColumn('cpc')} className="flex items-center space-x-2">
                              <Checkbox checked={visibleColumns.cpc} readOnly />
                              <span>CPC</span>
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => toggleColumn('platform_channel')} className="flex items-center space-x-2">
                              <Checkbox checked={visibleColumns.platform_channel} readOnly />
                              <span>Platform/Channel</span>
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => toggleColumn('campaign_objective')} className="flex items-center space-x-2">
                              <Checkbox checked={visibleColumns.campaign_objective} readOnly />
                              <span>Campaign Objective</span>
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => toggleColumn('audience_segment')} className="flex items-center space-x-2">
                              <Checkbox checked={visibleColumns.audience_segment} readOnly />
                              <span>Audience Segment</span>
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => toggleColumn('creative_type')} className="flex items-center space-x-2">
                              <Checkbox checked={visibleColumns.creative_type} readOnly />
                              <span>Creative Type</span>
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => toggleColumn('status')} className="flex items-center space-x-2">
                              <Checkbox checked={visibleColumns.status} readOnly />
                              <span>Status</span>
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => toggleColumn('navigate_to_campaign')} className="flex items-center space-x-2">
                              <Checkbox checked={visibleColumns.navigate_to_campaign} readOnly />
                              <span>Navigate to Campaign</span>
                            </DropdownMenuItem>
                          </div>
                        </DropdownMenuContent>
                        </DropdownMenu>
                      </div>
                    </th>
                  )}
                  {activeTab === 'insertion_orders' && (
                    <>
                      <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase tracking-wider">Impressions</th>
                      <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase tracking-wider">Clicks</th>
                      <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase tracking-wider">Spend</th>
                      <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase tracking-wider">ROAS</th>
                      <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase tracking-wider">CTR</th>
                      <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase tracking-wider">Media Plan</th>
                      <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase tracking-wider">Salesforce</th>
                      <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                    </>
                  )}
                </tr>
              </thead>
              <tbody>
                {/* FIX: Use data from API directly as it is already paginated server-side */}
                {currentData?.data?.map((item: Campaign | InsertionOrder) => (
                  <tr key={item.id} className="border-b border-gray-200 hover:bg-gray-50 transition-colors">
                    {visibleColumns.name && (
                      <td className="py-4 px-4 text-sm font-semibold text-gray-900 max-w-[300px]">
                        <div className="break-words whitespace-normal leading-relaxed">
                        {activeTab === 'campaigns' ? (
                          <Link
                            href={`/campaigns/${item.id}`}
                            className="text-blue-600 hover:text-blue-800 hover:underline transition-colors"
                          >
                            {item.name}
                          </Link>
                        ) : (
                          <Link
                            href={`/insertion-orders/${item.id}`}
                            className="text-blue-600 hover:text-blue-800 hover:underline transition-colors"
                          >
                            {item.name}
                          </Link>
                        )}
                        </div>
                      </td>
                    )}
                    {visibleColumns.brand && <td className="py-4 px-4 text-sm text-gray-600 truncate">{item.brand || 'N/A'}</td>}

                    {activeTab === 'campaigns' && (
                      <>
                        {visibleColumns.start_date && (
                          <td className="py-4 px-4 text-sm text-gray-600">
                            {formatDate((item as Campaign).start_date)}
                          </td>
                        )}
                        {visibleColumns.end_date && (
                          <td className="py-4 px-4 text-sm text-gray-600">
                            {formatDate((item as Campaign).end_date)}
                          </td>
                        )}
                        {visibleColumns.budget && (
                          <td className="py-4 px-4 text-sm font-medium text-gray-900">
                            {formatCurrency((item as Campaign).budget || 0)}
                          </td>
                        )}
                        {visibleColumns.target_impressions && (
                          <td className="py-4 px-4 text-sm text-gray-600">
                            {((item as Campaign).impressions_booked || 0).toLocaleString()}
                          </td>
                        )}
                        {visibleColumns.target_clicks && (
                          <td className="py-4 px-4 text-sm text-gray-600">
                            {getTargetClicks(item as Campaign).toLocaleString()}
                          </td>
                        )}
                        {visibleColumns.delivered_impressions && (
                          <td className="py-4 px-4 text-sm text-gray-600">
                            {((item as Campaign).impressions_delivered || 0).toLocaleString()}
                          </td>
                        )}
                        {visibleColumns.delivered_clicks && (
                          <td className="py-4 px-4 text-sm text-gray-600">
                            {((item as Campaign).clicks || 0).toLocaleString()}
                          </td>
                        )}
                        {visibleColumns.ctr && (
                          <td className="py-4 px-4 text-sm">
                            <span className={`inline-block px-2 py-1 rounded text-xs font-semibold ${
                              (item.ctr && item.ctr > 2)
                                ? 'bg-blue-100 text-blue-700 border border-blue-200'
                                : 'bg-gray-100 text-gray-700 border border-gray-200'
                            }`}>
                              {formatPercentage(item.ctr || 0)}
                            </span>
                          </td>
                        )}
                        {visibleColumns.roas && (
                          <td className="py-4 px-4 text-sm font-medium text-gray-900">
                            {formatRoas((item as Campaign).roas || 0)}
                          </td>
                        )}
                        {visibleColumns.conversions && (
                          <td className="py-4 px-4 text-sm text-gray-600">
                            {((item as Campaign).conversions || 0).toLocaleString()}
                          </td>
                        )}
                        {visibleColumns.spend && (
                          <td className="py-4 px-4 text-sm font-medium text-gray-900">
                            {formatCurrency((item as Campaign).spend || 0)}
                          </td>
                        )}
                        {visibleColumns.cpm && (
                          <td className="py-4 px-4 text-sm text-gray-600">
                            {formatCurrency((item as Campaign).cpm || 0)}
                          </td>
                        )}
                        {visibleColumns.cpc && (
                          <td className="py-4 px-4 text-sm text-gray-600">
                            {formatCurrency((item as Campaign).cpc || 0)}
                          </td>
                        )}
                        {visibleColumns.platform_channel && (
                          <td className="py-4 px-4 text-sm text-gray-600">
                            {(item as Campaign).platform_channel || 'N/A'}
                          </td>
                        )}
                        {visibleColumns.campaign_objective && (
                          <td className="py-4 px-4 text-sm text-gray-600">
                            {(item as Campaign).campaign_objective || 'N/A'}
                          </td>
                        )}
                        {visibleColumns.audience_segment && (
                          <td className="py-4 px-4 text-sm text-gray-600">
                            {(item as Campaign).audience_segment || 'N/A'}
                          </td>
                        )}
                        {visibleColumns.creative_type && (
                          <td className="py-4 px-4 text-sm text-gray-600">
                            {(item as Campaign).creative_type || 'N/A'}
                          </td>
                        )}
                        {visibleColumns.status && (
                          <td className="py-4 px-4">
                            <span className={`text-xs px-3 py-1 rounded-full border font-semibold ${getStatusColor(item.status)}`}>
                              {formatStatusDisplay(item.status)}
                            </span>
                          </td>
                        )}
                        {visibleColumns.navigate_to_campaign && (
                          <td className="py-4 px-4 text-sm">
                            {renderKevelLink((item as Campaign).kevel_id)}
                          </td>
                        )}
                        <td /> {/* Spacer for dropdown align */}
                      </>
                    )}



                    {activeTab === 'insertion_orders' && (
                      <>
                        <td className="py-4 px-4 text-sm">
                          {((item as Campaign).impressions_delivered || 0).toLocaleString()}
                        </td>
                        <td className="py-4 px-4 text-sm">
                          {((item as Campaign).clicks || 0).toLocaleString()}
                        </td>
                        <td className="py-4 px-4 text-sm font-medium text-gray-900">{formatCurrency(item.spend || 0)}</td>
                        <td className="py-4 px-4 text-sm font-medium text-gray-900">{formatRoas(item.roas || 0)}</td>
                        <td className="py-4 px-4 text-sm">
                          <span className={`inline-block px-2 py-1 rounded text-xs font-semibold ${
                            (item.ctr && item.ctr > 2)
                              ? 'bg-blue-100 text-blue-700 border border-blue-200'
                              : 'bg-gray-100 text-gray-700 border border-gray-200'
                          }`}>
                            {formatPercentage(item.ctr || 0)}
                          </span>
                        </td>
                        <td className="py-4 px-4 text-sm">
                          {renderMediaPlanLink((item as any).media_plan_url)}
                        </td>
                        <td className="py-4 px-4 text-sm">
                          {renderSalesforceLink((item as any).salesforce_io_id)}
                        </td>
                        <td className="py-4 px-4">
                          <span className={`text-xs px-3 py-1 rounded-full border font-semibold ${getStatusColor(item.status)}`}>
                            {formatStatusDisplay(item.status)}
                          </span>
                        </td>
                      </>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
          </div>
        )}

        {/* Centered Pagination Footer */}
        <div className="flex items-center px-6 py-4 border-t border-gray-200">
          {/* Left section: "Showing X to Y" */}
          <div className="w-1/4">
            <p className="text-sm text-gray-600 whitespace-nowrap">
              Showing {searchTerm ? currentData?.data?.length || 0 : ((currentPage - 1) * limit) + 1} to {searchTerm ? currentData?.data?.length || 0 : Math.min(currentPage * limit, totalEntriesForPagination)} of {totalEntriesForPagination} entries
            </p>
          </div>

          {/* Middle section: Centered page numbers and limit selector */}
          <div className="flex-1 flex items-center justify-center space-x-4">
            {!searchTerm && (
              <div className="flex items-center space-x-1">
                {dynamicPageButtons}
                {totalPages > 5 && currentPage < totalPages - 2 && (
                  <>
                    <span className="px-2 text-gray-400">...</span>
                    <Button
                      variant="outline"
                      size="sm"
                      className={`w-8 h-8 p-0 ${totalPages === currentPage
                        ? "border-orange-500 text-orange-500 bg-white"
                        : "border-gray-300 text-gray-600 hover:bg-gray-100"
                      }`}
                      onClick={() => setCurrentPage(totalPages)}
                      disabled={isLoading}
                    >
                      {totalPages}
                    </Button>
                  </>
                )}
              </div>
            )}

            <div className="flex items-center space-x-2">
              <select
                value={limit}
                disabled={!!searchTerm}
                onChange={(e) => {
                  setLimit(Number(e.target.value));
                  setCurrentPage(1);
                }}
                className={`text-sm border border-gray-300 rounded px-2 py-1 focus:outline-none ${searchTerm ? 'opacity-50' : ''}`}
              >
                <option value={10}>10</option>
                <option value={20}>20</option>
                <option value={50}>50</option>
                <option value={100}>100</option>
                <option value={200}>200</option>
                <option value={500}>500</option>
              </select>
              <span className="text-sm text-gray-600">/ page</span>
            </div>
          </div>

          {/* Right section: Back/Next buttons */}
          <div className="w-1/4 flex justify-end space-x-1">
            <Button
              variant="ghost"
              size="sm"
              className="text-gray-600 hover:text-gray-800 flex items-center"
              onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
              disabled={currentPage === 1 || isLoading || !!searchTerm}
            >
              <ChevronLeft className="w-4 h-4 mr-1" />
              Back
            </Button>

            <Button
              variant="ghost"
              size="sm"
              className="text-gray-600 hover:text-gray-800 flex items-center"
              onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
              disabled={currentPage === totalPages || isLoading || !!searchTerm}
            >
              Next
              <ChevronRight className="w-4 h-4 ml-1" />
            </Button>
          </div>
        </div>
      </CardContent>
      </Card>
    </div>
  );
};