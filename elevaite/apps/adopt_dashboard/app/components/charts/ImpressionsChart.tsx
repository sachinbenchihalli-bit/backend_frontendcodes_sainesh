"use client";

import { useMemo } from "react";
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from "recharts";
import { CampaignPerformanceSnapshot } from "@/types";
import { TimePeriod } from "@/hooks/useChartTimePeriod";

interface ImpressionsChartProps {
  data?: CampaignPerformanceSnapshot[];
  isLoading: boolean;
  timePeriod: TimePeriod;
  onChartClick?: () => void;
}

interface ChartDataPoint {
  date: string;
  impressions: number;
  spend: number;
  formattedDate: string;
}

export default function ImpressionsChart({ 
  data, 
  isLoading, 
  timePeriod, 
  onChartClick 
}: ImpressionsChartProps) {
  
  const chartData = useMemo(() => {
    if (!data || data.length === 0) return [];

    // Sort data by date
    const sortedData = [...data].sort((a, b) => 
      new Date(a.snapshot_date).getTime() - new Date(b.snapshot_date).getTime()
    );

    // Group data based on time period
    const groupedData = new Map<string, { impressions: number; spend: number; count: number; date: Date }>();

    sortedData.forEach(item => {
      const date = new Date(item.snapshot_date);
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
        groupedData.set(key, { impressions: 0, spend: 0, count: 0, date });
      }

      const existing = groupedData.get(key)!;
      const impressionsVal = Number(item.impressions_delivered ?? 0) || 0;
      const spendVal = Number(item.spend ?? 0) || 0;
      existing.impressions += impressionsVal;
      existing.spend += spendVal;
      existing.count += 1;
    });

    // Convert to chart format
    const result: ChartDataPoint[] = Array.from(groupedData.entries()).map(([key, value]) => {
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
        impressions: value.impressions,
        spend: value.spend,
        formattedDate
      };
    });

    return result.slice(-20); // Show last 20 data points
  }, [data, timePeriod]);

  const formatNumber = (value: number) => {
    if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`;
    if (value >= 1000) return `${(value / 1000).toFixed(1)}k`;
    return value.toLocaleString();
  };

  const formatCurrency = (value: number) => {
    if (value >= 1000000) return `$${(value / 1000000).toFixed(1)}M`;
    if (value >= 1000) return `$${(value / 1000).toFixed(1)}k`;
    return `$${value.toFixed(0)}`;
  };

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
        <span className="text-gray-400">No spend/impressions data available</span>
      </div>
    );
  }

  return (
    <div 
      className={`h-64 ${onChartClick ? 'cursor-pointer hover:bg-gray-50 rounded transition-colors' : ''}`}
      onClick={onChartClick}
    >
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 24, right: 10, left: 0, bottom: 24 }}>
          <CartesianGrid stroke="#F3F4F6" strokeDasharray="3 3" />
          <XAxis
            dataKey="formattedDate"
            tick={{ fontSize: 11, fill: '#6B7280' }}
            tickLine={false}
            axisLine={{ stroke: '#E5E7EB' }}
            tickMargin={10}
            minTickGap={14}
            interval={timePeriod === 'weekly' ? 0 : undefined}
            angle={timePeriod === 'weekly' ? -30 : 0}
            textAnchor={timePeriod === 'weekly' ? 'end' : 'middle'}
          />
          <YAxis
            yAxisId="left"
            tick={{ fontSize: 11, fill: '#6B7280' }}
            tickLine={false}
            axisLine={{ stroke: '#E5E7EB' }}
            tickFormatter={formatCurrency}
          />
          <YAxis
            yAxisId="right"
            orientation="right"
            tick={{ fontSize: 11, fill: '#6B7280' }}
            tickLine={false}
            axisLine={{ stroke: '#E5E7EB' }}
            tickFormatter={formatNumber}
          />
          <Tooltip
            formatter={(value: number, name: string) => {
              if (name === 'Spend') {
                return [formatCurrency(value), name];
              } else {
                return [formatNumber(value), name];
              }
            }}
            labelFormatter={(label) => {
              // Enhanced date formatting for tooltip
              const dataPoint = chartData.find(d => d.formattedDate === label);
              if(!dataPoint) return label || '';
              const date = new Date(dataPoint.date);
              if(isNaN(date.getTime())){
                return ''
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
          <Legend verticalAlign="top" align="right" />
          <Line
            type="monotone"
            dataKey="spend"
            stroke="#3B82F6"
            strokeWidth={2}
            dot={false}
            name="Spend"
            yAxisId="left"
          />
          <Line
            type="monotone"
            dataKey="impressions"
            stroke="#7C3AED"
            strokeWidth={2}
            dot={false}
            name="Delivered Impressions"
            yAxisId="right"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
