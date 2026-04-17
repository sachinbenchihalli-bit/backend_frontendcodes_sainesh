"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  TrendingUp,
  Upload,
  Search,
  Filter,
  Grid3X3,
  List,
  ExternalLink,
  Link,
  Zap,
  AlertTriangle,
  CheckCircle,
  MessageSquareText // Updated icon for chatbot
} from "lucide-react";
// Recharts for the pacing line graph
import { LineChart as ReLineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ReferenceLine, ResponsiveContainer } from "recharts";
import CampaignOverview from "../../components/CampaignOverview";
import CampaignPerformanceCharts from "../../components/CampaignPerformanceCharts";
import "../../page.scss";
// ✅ ADDED: Import backendApi for prewarm
import { backendApi } from "@/services/backendApi";

interface CampaignPlacement {
  id: string;
  campaign_id: string;
  start_date: string;
  end_date: string;
  impressions_booked: number;
  impressions_delivered: number;
  booked_clicks: number;
  delivered_clicks: number;
  ctr: number;
  budget: number;
  cpm: number;
  cpc: number;
  created_at: string;
  updated_at: string;
  flight_id?: string; // optional, used for deep links to ad server
}

interface Campaign {
  id: string;
  name: string;
  kevel_id: string;
  status: string;
  brand?: string;
  insertion_order_id?: string;
  created_at: string;
  updated_at: string;
  // Additional fields returned by backend for budget & pacing
  budget?: number;
  spend?: number;
  start_date?: string;
  end_date?: string;
  // Additional fields for overview component
  impressions_booked?: number;
  impressions_delivered?: number;
  clicks?: number;
  booked_clicks?: number;
  ctr?: number;
  roas?: number;
  conversions?: number;
  revenue?: number;
}
//interface for API response structure
interface CampaignInsightsResponse {
  campaign_id:string;
  insights:string[];
  suggestions:string[];
  success:boolean;
  model?:string;
  timestamp?:string
}

export default function CampaignDetailsPage() {
  const params = useParams();
  const campaignId = params.id as string;
  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [placements, setPlacements] = useState<CampaignPlacement[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [viewMode, setViewMode] = useState<'table' | 'grid'>('table');
  const [searchTerm, setSearchTerm] = useState("");
  const [rangeStart, setRangeStart] = useState<string>("");
  const [rangeEnd, setRangeEnd] = useState<string>("");
  const [appliedStart, setAppliedStart] = useState<string | undefined>(undefined);
  const [appliedEnd, setAppliedEnd] = useState<string | undefined>(undefined);
  const [isApplyingRange, setIsApplyingRange] = useState(false);
  const [insights , setInsights] = useState<string[]>([]);
  const [suggestions , setSuggestions] = useState<string[]>([]);
  


  // Helper function to check if a flight ID is synthetic/placeholder
  const isSyntheticFlightId = (flightId: string | undefined): boolean => {
    if (!flightId) return true;
    // Synthetic flight IDs follow pattern: flight-{campaign_name}-{uuid}
    // Real Kevel flight IDs typically don't follow this pattern
    return flightId.startsWith('flight-') && flightId.includes('-') && flightId.split('-').length >= 3;
  };

  // Pacing types and state
  type PacingPoint = { date: string; value: number };
  type PacingPayload = {
    campaign_id: string;
    start_date: string | null;
    end_date: string | null;
    budget: number;
    current_spend: number;
    planned_cumulative: PacingPoint[];
    actual_cumulative: PacingPoint[];
    meta?: any;
  } | null;
  const [pacing, setPacing] = useState<PacingPayload>(null);
  //For Insights and Suggestions
  const fetchCampaignInsights = async (campaignId:string)=>{
  try{
    const BACKEND_URL = 'http://localhost:8000';
    const response = await fetch(`${BACKEND_URL}/api/campaign/${campaignId}/insights`,{
      method:'GET',
      headers:{
        'Content-Type':'application/json',
      },
      credentials:'include'
    });
    if(!response.ok){
      throw new Error(`Failed to fetch insights: ${response.status}`);
    }
    const result: CampaignInsightsResponse = await response.json();
    //Set the insights from API Response
    setInsights(result.insights || []);
    setSuggestions(result.suggestions || []);
  }catch(error){
    console.error('Error fetching campaign insights:' , error);
    // setInsightsError(error instanceof Error ? error.message:'Failed to load Insights');
    setInsights([]);
    setSuggestions([]);
  }
  
};
useEffect(()=>{
  if(campaignId && !isLoading ) {
    fetchCampaignInsights(campaignId);
  }
},[campaignId , isLoading]);

  // Fetch real data from backend API
  useEffect(() => {
    const fetchCampaignData = async () => {
      try {
        setIsLoading(true);

        // Always use API proxy for all environments
        const BACKEND_URL = 'http://localhost:8000';

        // Fetch campaign details
        const campaignResponse = await fetch(`${BACKEND_URL}/api/campaigns/${campaignId}`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
          credentials: 'include'
        });

        if (!campaignResponse.ok) {
          throw new Error('Failed to fetch campaign');
        }

        const campaignResult = await campaignResponse.json();
        if (!campaignResult.success) {
          throw new Error(campaignResult.message || 'Failed to fetch campaign');
        }

        setCampaign(campaignResult.data);

        // Fetch campaign placements
        const placementsResponse = await fetch(`${BACKEND_URL}/api/campaigns/${campaignId}/placements`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
          credentials: 'include'
        });

        if (!placementsResponse.ok) {
          throw new Error('Failed to fetch placements');
        }

        const placementsResult = await placementsResponse.json();
        if (!placementsResult.success) {
          throw new Error(placementsResult.message || 'Failed to fetch placements');
        }

        setPlacements(placementsResult.data);

        // Fetch pacing
        const pacingResp = await fetch(`${BACKEND_URL}/api/campaigns/${campaignId}/pacing`, {
          method: 'GET',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include'
        });
        if (pacingResp.ok) {
          const pacingJson = await pacingResp.json();
          if (pacingJson?.success) {
            setPacing(pacingJson.data as PacingPayload);
          } else {
            setPacing(null);
          }
        } else {
          setPacing(null);
        }

      } catch (error) {
        console.error('Error fetching campaign data:', error);
        // Set empty data on error
        setCampaign(null);
        setPlacements([]);
        setPacing(null);
      } finally {
        setIsLoading(false);
      }
    };

    if (campaignId) {
      fetchCampaignData();
    }
  }, [campaignId]);

  // Initialize date inputs to campaign flight range once campaign loads
  useEffect(() => {
    if (campaign) {
      if (!rangeStart && campaign.start_date) setRangeStart(campaign.start_date);
      if (!rangeEnd && campaign.end_date) setRangeEnd(campaign.end_date);
    }
  }, [campaign]);

  const applyDateRange = async () => {
    if (!rangeStart || !rangeEnd) return;
    try {
      setIsApplyingRange(true);
      const resp = await fetch(`http://localhost:8000/api/campaigns/${campaignId}?start_date=${rangeStart}&end_date=${rangeEnd}`, {
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include'
      });
      const json = await resp.json();
      if (resp.ok && json?.success) {
        setCampaign(json.data);
        setAppliedStart(rangeStart);
        setAppliedEnd(rangeEnd);
      }
    } catch (e) {
      console.error('Failed to apply date range', e);
    } finally {
      setIsApplyingRange(false);
    }
  };

  // Helpers for currency and date math for pacing
  const formatCurrency = (value: number | undefined | null) =>
    `$${(Number(value || 0)).toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
  const toDate = (s?: string) => (s ? new Date(s) : undefined);
  const daysBetween = (a?: Date, b?: Date) => {
    if (!a || !b) return 0;
    const ms = b.getTime() - a.getTime();
    return Math.max(0, Math.ceil(ms / (1000 * 60 * 60 * 24)));
  };
  // Budget & Spend
  const totalBudget = Number((campaign as any)?.budget || 0);
  const totalSpend = Number((campaign as any)?.spend || 0);
  const percentUsed = totalBudget > 0 ? Math.min(100, Math.round((totalSpend / totalBudget) * 100)) : 0;
  // Pacing calculations (optional – displayed when dates exist)
  const start = toDate((campaign as any)?.start_date);
  const end = toDate((campaign as any)?.end_date);
  const today = new Date();
  const effectiveEnd = end && end < today ? end : today;
  const totalDays = daysBetween(start, end);
  const daysElapsed = daysBetween(start, effectiveEnd);
  const timeElapsedPct = totalDays > 0 ? Math.min(100, Math.round((daysElapsed / totalDays) * 100)) : undefined;
  const dailySpend = daysElapsed > 0 ? totalSpend / daysElapsed : undefined;
  const dailyTarget = totalDays > 0 ? totalBudget / totalDays : undefined;
  const remaining = Math.max(0, totalBudget - totalSpend);
  const isUnderspending = timeElapsedPct !== undefined && percentUsed + 5 < timeElapsedPct;
  const isOverspending = timeElapsedPct !== undefined && percentUsed > (timeElapsedPct + 5);

  // deltas for nicer messaging
  const pacingDeltaPct = timeElapsedPct !== undefined ? percentUsed - timeElapsedPct : 0; // negative => behind
  const projectedVariance = dailyTarget && dailySpend !== undefined && totalDays > 0
    ? Math.round((dailySpend - dailyTarget) * (totalDays - daysElapsed))
    : 0;

  const formatPercentage = (value: number) => `${(value).toFixed(2)}%`;

  // Build multi-series data for Recharts when pacing is available
  const pacingChartData = (pacing?.planned_cumulative || []).map((p, idx) => {
    const date = p.date;
    const planned = p.value;
    const actual = pacing?.actual_cumulative?.[idx]?.date === date
      ? pacing?.actual_cumulative?.[idx]?.value
      : undefined;
    return { date, planned, actual } as { date: string; planned: number; actual?: number };
  });

  // Derive planned daily budget (diff of cumulative) for use in Spend vs Budget chart
  const plannedDailyBudget = (pacing?.planned_cumulative || []).map((p, idx, arr) => {
    const prev = idx > 0 ? arr[idx - 1] : undefined;
    const daily = prev ? Math.max(0, (p.value || 0) - (prev.value || 0)) : (p.value || 0);
    return { date: p.date, value: daily } as { date: string; value: number };
  });

  if (isLoading) {
    return (
      <div className="adopt-dashboard-container">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-orange-500"></div>
        </div>
      </div>
    );
  }

  if (!campaign) {
    return (
      <div className="adopt-dashboard-container">
        <div className="text-center py-12">
          <h2 className="text-xl font-semibold text-gray-900">Campaign not found</h2>
          <p className="text-gray-600 mt-2">The campaign you're looking for doesn't exist.</p>
        </div>
      </div>
    );
  }

  return (
    <main className="adopt-dashboard-container relative">
      {/* Header Section */}
      <Card className="bg-white shadow-sm border border-gray-200 mb-6">
        <CardContent className="p-6">
          <div className="flex items-start justify-between">
            <div className="flex items-start space-x-4">
              <div className="w-10 h-10 bg-orange-100 rounded-lg flex items-center justify-center flex-shrink-0">
                <TrendingUp className="w-6 h-6 text-orange-600" />
              </div>
              <div className="flex-1">
                <div className="flex items-center space-x-3 mb-2">
                  <h1 className="text-2xl font-bold text-gray-900">{campaign.name}</h1>
                  <Badge
                    variant={['live','active'].includes(campaign.status?.toLowerCase?.() || '') ? 'default' : 'secondary'}
                    className={`${
                      ['live','active'].includes(campaign.status?.toLowerCase?.() || '')
                        ? 'bg-green-100 text-green-800 border-green-200'
                        : campaign.status?.toLowerCase?.() === 'completed'
                        ? 'bg-blue-100 text-blue-700 border-blue-200'
                        : campaign.status?.toLowerCase?.() === 'paused'
                        ? 'bg-red-100 text-red-700 border-red-200'
                        : campaign.status?.toLowerCase?.() === 'work_in_progress'
                        ? 'bg-orange-100 text-orange-700 border-orange-200'
                        : 'bg-gray-100 text-gray-800 border-gray-200'
                    } capitalize`}
                  >
                    {campaign.status === 'work_in_progress' ? 'WIP' : campaign.status}
                  </Badge>
                </div>


                {/* Campaign Details */}
                <div className="flex flex-wrap items-end gap-8 text-sm">
                  <div className="flex flex-col">
                    <span className="text-[11px] text-gray-500">Brand</span>
                    <span className="text-gray-900">{campaign.brand || 'Not specified'}</span>
                  </div>

                  <div className="flex flex-col">
                    <span className="text-[11px] text-gray-500">Flight Dates</span>
                    <span>
                      {campaign.start_date && campaign.end_date ? (
                        <>
                          {new Date(campaign.start_date).toLocaleDateString('en-US', {
                            month: 'short',
                            day: 'numeric',
                            year: 'numeric'
                          })} – {new Date(campaign.end_date).toLocaleDateString('en-US', {
                            month: 'short',
                            day: 'numeric',
                            year: 'numeric'
                          })}
                        </>
                      ) : 'Not specified'}
                    </span>
                  </div>

                  {campaign.start_date && campaign.end_date && timeElapsedPct !== undefined && (
                    <div className="flex flex-col">
                      <span className="text-[11px] text-gray-500">Time Elapsed</span>
                      <span className={`text-xs px-2 py-1 rounded-full font-medium ${
                        timeElapsedPct >= 100
                          ? 'bg-blue-100 text-blue-700 border border-blue-200'
                          : 'bg-orange-100 text-orange-700 border border-orange-200'
                      }`}>
                        {timeElapsedPct}% time elapsed
                      </span>
                    </div>
                  )}

                  <div className="flex items-center space-x-2">
                    {campaign.insertion_order_id ? (
                      <a
                        href={`/insertion-orders/${campaign.insertion_order_id}`}
                        className="inline-flex items-center px-2 py-1 rounded text-xs font-semibold bg-blue-100 text-blue-700 border border-blue-200"
                      >
                        <span>Insertion Order</span>
                        <Link className="w-3 h-3 ml-1" />
                      </a>
                    ) : (
                      <span className="inline-flex items-center px-2 py-1 rounded text-xs font-semibold bg-gray-100 text-gray-500 border border-gray-200 cursor-not-allowed">
                        <span>Insertion Order</span>
                        <Link className="w-3 h-3 ml-1 opacity-50" />
                      </span>
                    )}
                  </div>

                  <div className="flex items-center space-x-2">
                    {campaign.kevel_id ? (
                      <a
                        href={`https://app.kevel.co/#!/11679/campaign/${campaign.kevel_id}/flights/`}

                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center px-2 py-1 rounded text-xs font-semibold bg-purple-100 text-purple-700 border border-purple-200 hover:bg-purple-200 transition-colors"
                        title={`View in Kevel: ${campaign.kevel_id}`}
                      >
                        <span>Campaign in Ad Server</span>
                        <ExternalLink className="w-3 h-3 ml-1" />
                      </a>
                    ) : (
                      <span className="inline-flex items-center px-2 py-1 rounded text-xs font-semibold bg-gray-100 text-gray-500 border border-gray-200 cursor-not-allowed">
                        <span>Campaign in Ad Server</span>
                        <ExternalLink className="w-3 h-3 ml-1 opacity-50" />
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Action Buttons */}
            {/* <div className="flex items-center space-x-3">
              <Button
                onClick={() => {
                  // Add auto_analyze parameter to trigger automatic analysis
                  window.open(`/campaign-optimization/${campaign.id}?auto_analyze=true`, '_blank');
                }}
                className="bg-gradient-to-r from-orange-500 to-pink-500 hover:from-orange-600 hover:to-pink-600 text-white border-0 shadow-lg hover:shadow-xl transition-all duration-200 transform hover:scale-105"
                size="sm"
              >
                <Zap className="w-4 h-4 mr-2" />
                {campaign.status?.toLowerCase() === 'completed' ? 'Analyze Campaign' : 'Optimize Campaign'}
              </Button>
            </div> */}
          </div>
        </CardContent>
      </Card>

      {/* Date Range Selector (drives Overview + Charts) */}
      <Card className="bg-white shadow-sm border border-gray-200 mb-4">
        <CardContent className="p-4">
          <div className="flex items-center gap-3 flex-wrap">
            <span className="text-sm text-gray-600">Data range:</span>
            <Input
              type="date"
              value={rangeStart}
              onChange={(e) => setRangeStart(e.target.value)}
              className="w-40 border-gray-300 focus:border-orange-500 focus:ring-orange-500"
            />
            <span className="text-gray-400 text-sm">to</span>
            <Input
              type="date"
              value={rangeEnd}
              onChange={(e) => setRangeEnd(e.target.value)}
              className="w-40 border-gray-300 focus:border-orange-500 focus:ring-orange-500"
            />
            <Button onClick={applyDateRange} disabled={isApplyingRange || !rangeStart || !rangeEnd} size="sm" className="bg-orange-500 hover:bg-orange-600 text-white">
              {isApplyingRange ? 'Applying...' : 'Apply'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Campaign Overview */}
      <CampaignOverview campaign={campaign} isLoading={isLoading} pacingData={pacingChartData} />

       {/* Alerts & Suggested Actions */}
      <Card className="bg-white shadow-sm border border-gray-200 mb-6">
        <CardHeader className="pb-2">
          <div className="flex items-center space-x-2">
            <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-orange-100 text-orange-700">✨</span>
            <CardTitle className="text-base">Performance Overview</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          {/* Display dynamic insights and Suggestions */}
        {!isLoading && insights.length === 0 && suggestions.length === 0 ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-orange-500">

              </div>
            </div>
          ):(
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                {/* Left: Insights */}
                 <div>
                  <div className="text-sm font-semibold text-gray-800 mb-2">Insights:</div>
                  {insights.length > 0 ? (<ul className="list-disc pl-5 text-sm text-gray-800 space-y-3">
                    {insights.map((msg, i) => (
                      <li className="list-none" key={i}>{msg}</li>
                    ))}
                  </ul>) : (
                    <p className="tet-sm text-gray-500 italic">No Insights available</p>
                  )}
                  
                </div> 

                {/* Right: Suggestions */}
                <div>
                  <div className="text-sm font-semibold text-gray-800 mb-2">Suggestions:</div>
                  {suggestions.length > 0 ? (
                    <ul className="list-disc pl-5 text-sm text-gray-800 space-y-3">
                    {suggestions.map((s, i) => (
                      <li className="list-none" key={i}>{s}</li>
                    ))}
                  </ul>
                  ) : (
                    <p className="tet-sm text-gray-500 italic">No Suggestions available</p>
                  )}
                  
                </div>
              </div>
          )}
        
        </CardContent>
      </Card>

      {/* Performance Analytics Charts - Currently doesnt work - Need to fix it.*/}
      <CampaignPerformanceCharts
        campaignId={campaignId}
        campaignName={campaign.name}
        campaignStartDate={campaign.start_date}
        campaignEndDate={campaign.end_date}
        campaignBudget={campaign.budget}
        plannedDailyBudget={plannedDailyBudget}
        overrideStartDate={appliedStart}
        overrideEndDate={appliedEnd}
      />
      {/* Budget & Pacing */}
      <Card className="bg-white shadow-sm border border-gray-200">
        <CardContent className="p-6">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center space-x-4">
              <h2 className="text-lg font-semibold text-gray-900">Placements</h2>
            </div>
            <div className="flex items-center space-x-2">
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                placeholder="Search"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent"
              />
            </div>
            <Button variant="outline" size="sm">
              <Filter className="w-4 h-4 mr-2" />
              Filter
            </Button>
            <div className="flex border border-gray-300 rounded-lg">
              <Button
                variant={viewMode === 'table' ? 'default' : 'ghost'}
                size="sm"
                onClick={() => setViewMode('table')}
                className="rounded-r-none"
              >
                <List className="w-4 h-4" />
              </Button>
              <Button
                variant={viewMode === 'grid' ? 'default' : 'ghost'}
                size="sm"
                onClick={() => setViewMode('grid')}
                className="rounded-l-none"
              >
                <Grid3X3 className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </div>

        {/* Placement Table */}
        {viewMode === 'table' && (
          <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-[#DEE3ED]">
                  <tr>
                    <th className="px-6 py-4 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                      Creative
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                      Budget
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                      CPM / CPC
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                      Flight Dates
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                      Impressions
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                      Clicks / CTR
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                      Navigate to Placement
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {placements.map((placement) => (
                    <tr key={placement.id}>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="relative group">
                          <div className="w-16 h-16 bg-gradient-to-br from-orange-400 to-pink-500 rounded-lg flex items-center justify-center">
                            <span className="text-white text-xs font-bold">IMG</span>
                          </div>
                          <Button
                            variant="outline"
                            size="sm"
                            className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity bg-black/50 text-white border-none"
                          >
                            <Upload className="w-4 h-4 mr-1" />
                            Upload
                          </Button>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">
                          ${placement.budget.toLocaleString()}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900">
                          <div>CPM: ${placement.cpm}</div>
                          <div>CPC: ${placement.cpc}</div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900">
                          {placement.start_date && placement.end_date ? (
                            <>
                              {new Date(placement.start_date).toLocaleDateString('en-US', {
                                month: 'short',
                                day: 'numeric',
                                year: 'numeric'
                              })} – {new Date(placement.end_date).toLocaleDateString('en-US', {
                                month: 'short',
                                day: 'numeric',
                                year: 'numeric'
                              })}
                            </>
                          ) : 'N/A'}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900">
                          <div className="font-medium">{placement.impressions_delivered.toLocaleString()}</div>
                          <div className="text-xs text-gray-500">
                            of {placement.impressions_booked.toLocaleString()} booked
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900">
                          <div>
                            <span className="font-medium">{placement.delivered_clicks.toLocaleString()}</span>
                            <span className="text-blue-600 ml-2 text-xs">
                              {formatPercentage(placement.ctr)}
                            </span>
                          </div>
                          <div className="text-xs text-gray-500">
                            of {placement.booked_clicks.toLocaleString()} booked
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {placement.flight_id && !isSyntheticFlightId(placement.flight_id) ? (
                          <a
                            href={`https://app.kevel.co/#!/11679/flight/${placement.flight_id}/edit/`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center px-2 py-1 rounded text-xs font-semibold bg-purple-100 text-purple-700 border border-purple-200 hover:bg-purple-200 transition-colors"
                            title={`View in Kevel: ${placement.flight_id}`}
                          >
                            <ExternalLink className="w-3 h-3 mr-1" />
                            View Placement
                          </a>
                        ) : (
                          <span className="inline-flex items-center px-2 py-1 rounded text-xs font-semibold bg-gray-100 text-gray-500 border border-gray-200 cursor-not-allowed">
                            <ExternalLink className="w-3 h-3 mr-1 opacity-50" />
                            View Placement
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Grid View */}
        {viewMode === 'grid' && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {placements.map((placement, index) => (
              <Card key={placement.id} className="bg-white">
                <CardContent className="p-6">
                  <div className="flex items-center justify-between mb-4">
                    <div className="relative group">
                      <div className="w-16 h-16 bg-gradient-to-br from-orange-400 to-pink-500 rounded-lg flex items-center justify-center">
                        <span className="text-white text-xs font-bold">IMG</span>
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity bg-black/50 text-white border-none"
                      >
                        <Upload className="w-4 h-4" />
                      </Button>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-medium text-gray-900">
                        {placement.flight_id ? `${placement.flight_id.split('-')[0]}-` : ''}
                      </div>
                      <div className="text-xs text-gray-500">
                        {placement.flight_id ? `${placement.flight_id.substring(4, 20)}...` : ''}
                      </div>
                    </div>
                  </div>

                  <div className="space-y-3">
                    <div>
                      <div className="text-xs text-gray-500 uppercase tracking-wider">Dates</div>
                      <div className="text-sm text-gray-900">
                        {new Date(placement.start_date).toLocaleDateString('en-US', {
                          month: 'short',
                          day: 'numeric'
                        })} – {new Date(placement.end_date).toLocaleDateString('en-US', {
                          month: 'short',
                          day: 'numeric'
                        })}
                      </div>
                    </div>

                    <div>
                      <div className="text-xs text-gray-500 uppercase tracking-wider">Performance</div>
                      <div className="flex justify-between text-sm">
                        <span>Impressions: {placement.impressions_delivered.toLocaleString()}</span>
                        <span>CTR: {formatPercentage(placement.ctr)}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span>Clicks: {placement.delivered_clicks}</span>
                        <span>CPM: ${placement.cpm}</span>
                      </div>
                    </div>

                    <div>
                      <div className="text-xs text-gray-500 uppercase tracking-wider">Placement</div>
                      <div className="text-sm text-gray-900">
                        {index === 0 ? 'Instagram Reels' : 'Web Display – Sidebar'}
                      </div>
                    </div>

                    <div className="pt-2">
                      {placement.flight_id && !isSyntheticFlightId(placement.flight_id) ? (
                        <a
                          href={`https://app.kevel.co/#!/11679/flight/${placement.flight_id}/edit/`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center px-2 py-1 rounded text-xs font-semibold bg-purple-100 text-purple-700 border border-purple-200 hover:bg-purple-200 transition-colors"
                          title={`View in Kevel: ${placement.flight_id}`}
                        >
                          <ExternalLink className="w-3 h-3 mr-1" />
                          View Placement
                        </a>
                      ) : (
                        <span className="inline-flex items-center px-2 py-1 rounded text-xs font-semibold bg-gray-100 text-gray-500 border border-gray-200 cursor-not-allowed">
                          <ExternalLink className="w-3 h-3 mr-1 opacity-50" />
                          View Placement
                        </span>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
        </CardContent>
      </Card>

      {/* FLOATING CHATBOT ICON COMPONENT */}
      <div className="fixed bottom-3 right-5 flex flex-col items-end z-50 group">
        {/* Hover Label */}
        <div className="mb-2 px-3 py-1.5 bg-gray-900 text-white text-xs font-semibold rounded-md shadow-lg opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none whitespace-nowrap relative after:content-[''] after:absolute after:top-full after:right-5 after:border-8 after:border-transparent after:border-t-gray-900">
          Campaign Intelligence Assistant
        </div>
        
        {/* Floating Chatbot Button */}
        {/* ✅ CHANGED: fires prewarm before opening chat page so backend caches
            all tool results while the new tab loads. By the time the user types
            their first message, the first token arrives in ~1.4s instead of 20s. */}
        <button
          onClick={() => {
            // ✅ Fire prewarm instantly — backend caches all tools in background
            backendApi.prewarmCampaignContext(campaign.id);
            // Open the chat page (prewarm runs silently while page loads)
            window.open(`/campaign-optimization/${campaign.id}?auto_analyze=true`, '_blank');
          }}
          className="w-16 h-16 rounded-full bg-gradient-to-br from-[#FF681F] to-[#ED4E7A] flex items-center justify-center shadow-xl hover:shadow-2xl hover:scale-110 transition-all duration-300 border-2 border-white focus:outline-none"
        >
          {/* Inner white circle for the chatbot icon */}
          <div className="w-10 h-10 bg-white rounded-full flex items-center justify-center">
            <MessageSquareText className="w-6 h-6 text-[#FF681F]" />
          </div>
        </button>
      </div>

    </main>
  );
}
