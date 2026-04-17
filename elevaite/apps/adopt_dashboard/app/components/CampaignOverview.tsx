"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";



interface Campaign {
  id: string;
  name: string;
  status: string;
  brand?: string;
  budget?: number;
  spend?: number;
  start_date?: string;
  end_date?: string;
  // Additional fields from dashboard_campaigns_view
  impressions_booked?: number;
  impressions_delivered?: number;
  clicks?: number;
  booked_clicks?: number;
  ctr?: number;
  cpa?: number;
  conversions?: number;
  roas?: number;
  cpm?: number;
  cpc?: number;
  revenue?: number;
  //Indivisual health Metrics
  cpa_health?:string;
  ctr_health?:string;
  roas_health?:string;
}

interface CampaignOverviewProps {
  campaign: Campaign;
  isLoading?: boolean;
  pacingData?: Array<{ date: string; actual?: number; planned?: number }>;
}
interface PerformanceStyles {
  dotColor: string;
  indicator: string;
}
type HealthStatus = "good" | "average" | "bad";
//helper function for performance health
const getPerformanceStyles = (health?:string)=>{
  switch(health?.toLocaleLowerCase()){
    case "good":
      return{
        dotColor:"bg-green-500",
        indicator:'▲'
      };
      case "average":
      return{
        dotColor:"",
        indicator:'-'
      };
      case "bad":
        return{
          dotColor:"bg-red-500",
          indicator:'▼'
        };
      default:
        return{
          dotColor:"bg-gray-500",
          indicator:""
        }  
  }
};

export function CampaignOverview({ campaign, isLoading }: CampaignOverviewProps) {
  if (isLoading) {
    return (
      <Card className="bg-white shadow-sm border border-gray-200 mb-6">
        <CardContent className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[1, 2, 3].map((i) => (
              <div key={i} className="animate-pulse">
                <div className="h-4 bg-gray-200 rounded w-1/2 mb-2"></div>
                <div className="h-8 bg-gray-200 rounded w-3/4 mb-2"></div>
                <div className="h-2 bg-gray-200 rounded w-full"></div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  // Helper functions
  const formatNumber = (num?: number, useDecimals: boolean = false) => {
    if (num === undefined || num === null) return useDecimals ? '0.00' : '0';
    if (useDecimals) {
      return num.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }
    return num.toLocaleString();
  };

  const formatCurrency = (num?: number) => {
    if (num === undefined || num === null) return '$0.00';
    return `$${num.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const formatPercentage = (value?: number) => {
    if (value === undefined || value === null) return '0%';
    return `${value.toFixed(2)}%`;
  };

  const formatDecimal = (value?: number, decimals: number = 2) => {
    if (value === undefined || value === null) return '0';
    return value.toFixed(decimals);
  };

  // Extracted Metrics
  const revenue = Number(campaign.revenue)

  // CPA with 2 decimal places
  const cpa = Number(campaign.cpa)

  // Spend/Budget & Impressions helpers
  const totalBudget = Number(campaign.budget || 0);
  const totalSpend = Number(campaign.spend || 0);
  const budgetUsedPct = totalBudget > 0 ? (totalSpend / totalBudget) * 100 : 0;

  const impressionsBooked = Number(campaign.impressions_booked || 0);
  const impressionsDelivered = Number(campaign.impressions_delivered || 0);
  const impressionsPct = impressionsBooked > 0 ? (impressionsDelivered / impressionsBooked) * 100 : 0;

  // Normalize CTR: backend may return ratio (e.g., 0.0012) or percent (e.g., 0.12 or 12).
  // Convert to percent for display (e.g., 0.12 -> 12.00%). If value <= 1 treat as ratio and multiply by 100.
  let ctrPct = 0;
  if (campaign.ctr !== undefined && campaign.ctr !== null) {
    const rawCtr = Number(campaign.ctr);
    if (!isNaN(rawCtr)) {
      ctrPct = rawCtr;
    }
  }

//helper function to get budget bg color based on percentage
const getBudgetStatusColor = (percentage:number) =>{
  if(percentage >= 90){
    return 'bg-green-500 text-white'
  }else if(percentage >= 70){
    return 'bg-yellow-500 text-white'
  } else {
    return 'bg-red-500 text-white'
  }
}


  return (
    <Card className="bg-white shadow-sm border border-gray-200 mb-6">
      <CardHeader className="pb-2">
        <CardTitle className="text-lg font-semibold">Overview</CardTitle>
      </CardHeader>
      <CardContent className="p-6">
        {/* Metrics Grid - 4 columns with first column wider */}
        <div className="grid grid-cols-1 lg:[grid-template-columns:1.8fr_1fr_1fr_1fr] gap-4">

          {/* Column 1 (wide): Spend vs Budget + Impressions */}
          <div className="grid grid-rows-2 gap-4 h-full">
            {/* Total Spend vs Budget */}
            <div className="border border-gray-300 rounded-lg p-4 bg-white h-full">
              <div className="flex items-center justify-between mb-2">
                <div className="text-sm font-medium text-gray-600">Total Spend vs. Budget</div>
                <span className={`text-[11px] font-medium px-2 py-0.5 rounded-full ${getBudgetStatusColor(budgetUsedPct)}`}>
                  {budgetUsedPct.toFixed(2)}% budget used
                </span>
              </div>
              <div className="flex items-center justify-between mb-2">
                <div className="text-2xl font-bold text-gray-900">{formatCurrency(totalSpend)}</div>
                <div className="text-sm text-gray-500">{formatCurrency(totalBudget)}</div>
              </div>
              <div className="flex items-center justify-between text-xs text-gray-500 mb-2">
                <span>Spent</span>
                <span>Budget</span>
              </div>
              <div className="relative h-2 w-full overflow-hidden rounded-full bg-gray-200">
                <div className="h-full bg-teal-500" style={{ width: `${Math.min(100, budgetUsedPct)}%` }} />
              </div>
            </div>

            {/* Impressions: Booked vs Delivered */}
            <div className="border border-gray-300 rounded-lg p-4 bg-white h-full">
              <div className="flex items-center justify-between mb-2">
                <div className="text-sm font-medium text-gray-600 mb-2">Impressions</div>
              <span className={`text-[11px] font-medium px-2 py-0.5 rounded-full ${getBudgetStatusColor(impressionsPct)}`}>
                  {impressionsPct.toFixed(2)}% bids won
                </span>
              </div>
              
              <div className="flex items-baseline justify-between mb-1">
                <div className="text-2xl font-bold text-gray-900">{formatNumber(impressionsDelivered)}</div>
                <div className="text-2xl font-bold text-gray-900">{formatNumber(impressionsBooked)}</div>
              </div>
              <div className="flex items-center justify-between text-xs text-gray-500 mb-2">
                <span>Delivered</span>
                <span>Booked</span>
              </div>
              <div className="relative h-2 w-full overflow-hidden rounded-full bg-gray-200">
                <div className="h-full bg-yellow-600" style={{ width: `${Math.min(100, impressionsPct)}%` }} />
              </div>
            </div>
          </div>

          {/* Column 2: Revenue + CPA */}
          <div className="grid grid-rows-2 gap-4 h-full">
            <div className="border border-gray-300 rounded-lg p-4 bg-gray-50 h-full">
              <div className="text-sm font-medium text-gray-600 mb-2">Revenue</div>
              <div className="text-2xl font-bold text-gray-900">{formatCurrency(revenue)}</div>
            </div>
            <div className="border border-dashed border-gray-300 rounded-lg p-4 bg-gray-50 h-full">
              <div className="flex items-center justify-between mb-2">
                <div className="text-sm font-medium text-gray-600">CPA</div>
                <div className={`w-4 h-4 rounded-full ${getPerformanceStyles(campaign.cpa_health).dotColor}`}>
                  {getPerformanceStyles(campaign.cpa_health).indicator === "-" ? (
                    <svg className="w-5 h-5 text-orange-500" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM7 9a1 1 0 000 2h6a1 1 0 100-2H7z" clipRule="evenodd"></path></svg>
                  ) : (
                    <span className="text-xs flex justify-center items-center font-semibold text-white">{getPerformanceStyles(campaign.cpa_health).indicator}</span>
                  )}
                </div>
              </div>
              <div className="text-2xl font-bold text-gray-900">{formatCurrency(cpa)}</div>
            </div>
          </div>

          {/* Column 3: Conversion + CTR */}
          <div className="grid grid-rows-2 gap-4 h-full">
            <div className="border border-gray-300 rounded-lg p-4 bg-gray-50 h-full">
              <div className="text-sm font-medium text-gray-600 mb-2">Conversion</div>
              <div className="text-2xl font-bold text-gray-900">{formatNumber(campaign.conversions)}</div>
            </div>
            <div className="border border-gray-300 rounded-lg p-4 bg-gray-50 h-full">
              <div className="flex items-center justify-between mb-2">
                <div className="text-sm font-medium text-gray-600">CTR%</div>
                <div className={`w-4 h-4 rounded-full ${getPerformanceStyles(campaign.ctr_health).dotColor}`}>
                  {getPerformanceStyles(campaign.ctr_health).indicator === "-" ? (
                    <svg className="w-5 h-5 text-orange-500" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM7 9a1 1 0 000 2h6a1 1 0 100-2H7z" clipRule="evenodd"></path></svg>
                  ) : (
                    <span className="text-xs flex justify-center items-center font-semibold text-white">{getPerformanceStyles(campaign.ctr_health).indicator}</span>
                  )}
                </div>
              </div>
              <div className="text-2xl font-bold text-gray-900">{formatPercentage(ctrPct)}</div>
            </div>
          </div>

          {/* Column 4: Clicks + ROAS */}
          <div className="grid grid-rows-2 gap-4 h-full">
            <div className="border border-gray-300 rounded-lg p-4 bg-gray-50 h-full">
              <div className="text-sm font-medium text-gray-600 mb-2">Clicks</div>
              <div className="text-2xl font-bold text-gray-900">{formatNumber(campaign.clicks)}</div>
            </div>
            <div className="border border-gray-300 rounded-lg p-4 bg-gray-50 h-full">
              <div className="flex items-center justify-between mb-2">
                <div className="text-sm font-medium text-gray-600">ROAS</div>
                <div className={`w-4 h-4 rounded-full ${getPerformanceStyles(campaign.roas_health).dotColor}`}>
                {getPerformanceStyles(campaign.roas_health).indicator === "-" ? (
                  <svg className="w-5 h-5 text-orange-500" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM7 9a1 1 0 000 2h6a1 1 0 100-2H7z" clipRule="evenodd"></path></svg>
                ) : (
                  <span className="text-xs flex justify-center items-center font-semibold text-white">{getPerformanceStyles(campaign.roas_health).indicator}</span>
                )}
                </div>
              </div>
              <div className="text-2xl font-bold text-gray-900">{formatDecimal(campaign.roas)}</div>
            </div>
          </div>

        </div>


      </CardContent>
    </Card>
  );


}

export default CampaignOverview;
