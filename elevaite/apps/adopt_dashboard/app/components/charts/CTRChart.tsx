"use client";

import { useMemo } from "react";
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip } from "recharts";
import { CampaignPerformanceSnapshot } from "@/types";
import { TimePeriod } from "@/hooks/useChartTimePeriod";

interface CTRChartProps {
  data?: CampaignPerformanceSnapshot[];
  isLoading: boolean;
  timePeriod: TimePeriod;
  onChartClick?: () => void;
}

interface ChartDataPoint {
  date: string;
  ctr: number;
  formattedDate: string;
}

export default function CTRChart({ 
  data, 
  isLoading, 
  timePeriod, 
  onChartClick 
}: CTRChartProps) {
  
  const chartData = useMemo(() => {
    if (!data || data.length === 0) return [];

    // Sort data by date
    const sortedData = [...data].sort((a, b) => 
      new Date(a.snapshot_date).getTime() - new Date(b.snapshot_date).getTime()
    );

    // Group data based on time period
    const groupedData = new Map<string, { 
      totalClicks: number; 
      totalImpressions: number; 
      count: number; 
      date: Date;
      sumCtrPercent: number; // sum of ctr percentages (used when impressions missing)
    }>();

    sortedData.forEach(item => {
      const date = new Date(item.snapshot_date);
        // if(isNaN(date.getTime())) return
      let key: string;
    
      switch (timePeriod) {
        case 'daily':
        case 'custom':
          // Group by day
          key = date.toISOString().split('T')[0];
          break;
        case 'weekly':
          // Group by week (start on Sunday)
          const weekStart = new Date(date);
          weekStart.setDate(date.getDate() - date.getDay());
          key = weekStart.toISOString().split('T')[0];
          break;
        case 'monthly':
          // Group by month
          key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
          break;
        case 'quarterly':
        default:
          // Group by quarter
          const quarter = Math.floor(date.getMonth() / 3) + 1;
          key = `${date.getFullYear()}-Q${quarter}`;
      }

      if (!groupedData.has(key)) {
        groupedData.set(key, { 
          totalClicks: 0, 
          totalImpressions: 0, 
          count: 0, 
          date,
          sumCtrPercent: 0
        });
      }

      const existing = groupedData.get(key)!;

      // Normalize numeric fields
      const impressions = Number(item.impressions_delivered ?? (item as any).impressions ?? 0) || 0;
      let clicks = Number(item.clicks ?? 0) || 0;

      // If clicks or impressions are missing but backend provided a CTR, try to derive clicks when impressions exist.
      if ((clicks === 0 || impressions === 0) && (item as any).ctr !== undefined && (item as any).ctr !== null) {
        const rawCtr = Number((item as any).ctr);
        if (!isNaN(rawCtr) && impressions > 0) {
          // rawCtr may be a ratio (0.0012) or a percent (0.12 or 12). Convert to ratio first.
          const ratio = rawCtr <= 1 ? rawCtr : rawCtr / 100;
          clicks = Math.round(ratio * impressions);
        }
      }

      // If impressions exist, accumulate clicks/impressions for accurate weighted CTR.
      existing.totalClicks += clicks;
      existing.totalImpressions += impressions;

      // Also track CTR percent sum for cases where impressions are not available, to allow averaging.
      if ((item as any).ctr !== undefined && (item as any).ctr !== null) {
        const rawCtr = Number((item as any).ctr);
        if (!isNaN(rawCtr)) {
          const ctrPercent = rawCtr <= 1 ? rawCtr * 100 : rawCtr;
          existing.sumCtrPercent += ctrPercent;
        }
      }

      existing.count += 1;
    });

    // Convert to chart format and calculate CTR
    const result: ChartDataPoint[] = Array.from(groupedData.entries()).map(([key, value]) => {
      // Calculate CTR: prefer weighted totalClicks/totalImpressions when impressions exist.
      // Otherwise fall back to average of provided CTR percentages (sumCtrPercent / count).
      let ctr = 0;
      if (value.totalImpressions > 0) {
        ctr = (value.totalClicks / value.totalImpressions) * 100;
      } else if (value.sumCtrPercent > 0 && value.count > 0) {
        ctr = value.sumCtrPercent / value.count;
      }
      //Format date for display based on time period
      let formattedDate:string;
      if(timePeriod === 'quarterly'){
          const quarter = Math.floor(value.date.getMonth()/3 + 1);
          formattedDate = `Q${quarter} ${value.date.getFullYear()}`;
        }else if (timePeriod === 'monthly'){
          formattedDate = value.date.toLocaleDateString('en-US', {
          month: 'short',
          year:'numeric' 
        });
      }else if (timePeriod === 'daily' || timePeriod === 'weekly' || timePeriod === 'custom'){
        formattedDate = value.date.toLocaleDateString('en-US', {
        month:'short',
        day:'numeric',
        year:'numeric'  
      });
    }else{
      formattedDate = value.date.toLocaleDateString('en-US',{
        month:'short',
        year:'numeric'
      });
    }

      return {
        date: key,
        ctr: Number(ctr.toFixed(3)), // Round to 3 decimal places for consistency
        formattedDate
        
    };
      
    });

    return result.slice(-20); // Show last 20 data points
  }, [data, timePeriod]);

  const formatPercentage = (value: number) => `${value.toFixed(2)}%`;

  if (isLoading) {
    return (
      <div className="h-64 bg-gray-50 rounded border border-gray-200 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-orange-500"></div>
      </div>
    );
  }

  if (!chartData || chartData.length === 0) {
    return (
      <div className="h-64 bg-gray-50 rounded border border-gray-200 flex items-center justify-center">
        <span className="text-gray-400">No CTR data available</span>
      </div>
    );
  }

  // Calculate min and max for better Y-axis scaling
  const ctrValues = chartData.map(d => d.ctr);
  const minCTR = Math.min(...ctrValues);
  const maxCTR = Math.max(...ctrValues);
  const padding = (maxCTR - minCTR) * 0.1; // 10% padding
  const yAxisMin = Math.max(0, minCTR - padding);
  const yAxisMax = maxCTR + padding;

  return (
    <div 
      className={`h-64 ${onChartClick ? 'cursor-pointer hover:bg-gray-50 rounded transition-colors' : ''}`}
      onClick={onChartClick}
    >
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="ctrGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.3}/>
              <stop offset="95%" stopColor="#3B82F6" stopOpacity={0.05}/>
            </linearGradient>
          </defs>
          <CartesianGrid stroke="#F3F4F6" strokeDasharray="3 3" />
          <XAxis
            dataKey="formattedDate"
            tick={{ fontSize: 11, fill: '#6B7280' }}
            tickLine={false}
            axisLine={{ stroke: '#E5E7EB' }}
            interval={timePeriod === 'weekly' ? 0 : undefined}
          />
          <YAxis 
            domain={[yAxisMin, yAxisMax]}
            tick={{ fontSize: 11, fill: '#6B7280' }} 
            tickLine={false}
            axisLine={{ stroke: '#E5E7EB' }}
            tickFormatter={formatPercentage}
          />
          <Tooltip
            formatter={(value: number) => [formatPercentage(value), 'CTR']}
            labelFormatter={(label) => {
              // Enhanced date formatting for tooltip
              const dataPoint = chartData.find(d => d.formattedDate === label);
              if(!dataPoint) return label || '';
              const date = new Date(dataPoint.date);
              if(isNaN(date.getTime())){
                return '';
              } 
              
                // const date = new Date(dataPoint.date);
                if (timePeriod === 'monthly'){
                  return date.toLocaleDateString('en-US', {
                  year: 'numeric',
                  month: 'short'
                });
              }
                return date.toLocaleDateString('en-US', {
                  weekday: 'short',
                  year: 'numeric',
                  month: 'short',
                  day: 'numeric'
                });
              
              // return label;
            }}
            contentStyle={{
              backgroundColor: 'white',
              border: '1px solid #E5E7EB',
              borderRadius: '6px',
              fontSize: '12px',
              boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
            }}
          />
          <Area
            type="monotone"
            dataKey="ctr"
            stroke="#3B82F6"
            strokeWidth={2}
            fill="url(#ctrGradient)"
            dot={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
