"use client";

import { useMemo } from "react";
import { ResponsiveContainer, ComposedChart, Line, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from "recharts";
import { CampaignPerformanceSnapshot } from "@/types";
import { TimePeriod } from "@/hooks/useChartTimePeriod";

interface SpendBudgetChartProps {
  data?: CampaignPerformanceSnapshot[];
  isLoading: boolean;
  timePeriod: TimePeriod;
  campaignBudget?: number;
  startDate?: string;
  endDate?: string;
  onChartClick?: () => void;
}

interface ChartDataPoint {
  date: string;
  spend: number;             // total spend in the aggregated period
  budget: number;            // budget allocation for the period
  formattedDate: string;
}

export default function SpendBudgetChart({
  data,
  isLoading,
  timePeriod,
  campaignBudget,
  startDate,
  endDate,
  onChartClick
}: SpendBudgetChartProps) {

  // Date helpers (avoid timezone shifts from toISOString / Date("YYYY-MM-DD") parsing)
  const clamp = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const pad2 = (n: number) => String(n).padStart(2, '0');
  const formatYMD = (d: Date) => `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`;
  const parseAnyDate = (s: string) => {
    const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s);
    if (match) {
      const y = Number(match[1]);
      const m = Number(match[2]);
      const day = Number(match[3]);
      return new Date(y, m - 1, day);
    }
    return new Date(s);
  };
  const parseDateOnly = (s?: string) => (s ? clamp(parseAnyDate(s)) : undefined);
  
  const chartData = useMemo(() => {
    if (!data || data.length === 0) return [];

    // Sort data by date
    const sortedData = [...data].sort((a, b) => 
      parseAnyDate(a.snapshot_date).getTime() - parseAnyDate(b.snapshot_date).getTime()
    );

    // Group data based on time period
    // Note: backend performance snapshots may include a per-day planned budget (item.budget).
    const groupedData = new Map<string, { spend: number; budgetFromSnapshots: number; count: number; date: Date }>();

    sortedData.forEach(item => {
      const date = clamp(parseAnyDate(item.snapshot_date));
      let key: string;
      let anchorDate: Date;

      switch (timePeriod) {
        case 'daily':
        case 'custom': {
          key = formatYMD(date);
          anchorDate = date;
          break;
        }
        case 'weekly': {
          // Group by week (start on Sunday)
          const weekStart = new Date(date);
          weekStart.setDate(date.getDate() - date.getDay());
          anchorDate = clamp(weekStart);
          key = formatYMD(anchorDate);
          break;
        }
        case 'monthly': {
          anchorDate = new Date(date.getFullYear(), date.getMonth(), 1);
          key = `${anchorDate.getFullYear()}-${pad2(anchorDate.getMonth() + 1)}`;
          break;
        }
        case 'quarterly':
        default: {
          const quarterStartMonth = Math.floor(date.getMonth() / 3) * 3;
          anchorDate = new Date(date.getFullYear(), quarterStartMonth, 1);
          const quarter = Math.floor(date.getMonth() / 3) + 1;
          key = `${date.getFullYear()}-Q${quarter}`;
          break;
        }
      }

      if (!groupedData.has(key)) {
        groupedData.set(key, { spend: 0, budgetFromSnapshots: 0, count: 0, date: clamp(anchorDate) });
      }

      const existing = groupedData.get(key)!;
      const spendVal = Number(item.spend ?? 0) || 0;
      const budgetVal = Number((item as any).budget ?? 0) || 0;
      existing.spend += spendVal;
      existing.budgetFromSnapshots += budgetVal;
      existing.count += 1;
    });

    const msPerDay = 1000 * 60 * 60 * 24;

    const campaignStart = parseDateOnly(startDate);
    const campaignEnd = parseDateOnly(endDate);

    const totalDays = campaignStart && campaignEnd ? Math.max(0, Math.floor((campaignEnd.getTime() - campaignStart.getTime()) / msPerDay) + 1) : 0;
    const dailyBudget = campaignBudget && totalDays > 0 ? campaignBudget / totalDays : 0;

    const overlapDays = (aStart: Date, aEnd: Date, bStart?: Date, bEnd?: Date) => {
      if (!bStart || !bEnd) return 0;
      const start = clamp(new Date(Math.max(aStart.getTime(), bStart.getTime())));
      const end = clamp(new Date(Math.min(aEnd.getTime(), bEnd.getTime())));
      const diff = Math.floor((end.getTime() - start.getTime()) / msPerDay) + 1;
      return diff > 0 ? diff : 0;
    };

    // Convert to chart format
    let result: ChartDataPoint[] = Array.from(groupedData.entries()).map(([key, value]) => {
      // Determine this period's date range
      const d = value.date;
      let periodStart = clamp(d);
      let periodEnd = clamp(d);
      let formattedDate:string;
      if (timePeriod === 'weekly') {
        periodStart = clamp(d);
        periodEnd = new Date(periodStart);
        periodEnd.setDate(periodStart.getDate() + 6);
        periodEnd = clamp(periodEnd);
      } else if (timePeriod === 'monthly') {
        periodStart = new Date(d.getFullYear(), d.getMonth(), 1);
        periodEnd = new Date(d.getFullYear(), d.getMonth() + 1, 0);
      } else if (timePeriod === 'quarterly') {
        const quarterStartMonth = Math.floor(d.getMonth() / 3) * 3;
        periodStart = new Date(d.getFullYear(), quarterStartMonth, 1);
        periodEnd = new Date(d.getFullYear(), quarterStartMonth + 3, 0);
      }

      const days = overlapDays(periodStart, periodEnd, campaignStart, campaignEnd);

      // Prefer backend-provided budget series when available.
      // Fallback to an evenly-distributed campaign budget when snapshot budgets are missing
      // or clearly not representing per-day planned budget.
      const evenBudgetForPeriod = dailyBudget * days;
      const snapshotBudgetForPeriod = value.budgetFromSnapshots;
      const maxReasonable = campaignBudget ? campaignBudget * 1.1 : undefined;
      const useSnapshotBudget =
        snapshotBudgetForPeriod > 0 &&
        (maxReasonable === undefined || snapshotBudgetForPeriod <= maxReasonable);
      const budgetForPeriod = useSnapshotBudget ? snapshotBudgetForPeriod : evenBudgetForPeriod;
      if(timePeriod === 'quarterly'){
          const quarter = Math.floor(value.date.getMonth()/3) + 1;
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
        spend: value.spend,
        budget: budgetForPeriod,
        formattedDate
      };
    });

    return result.slice(-20); // Show last 20 data points
  }, [data, timePeriod, campaignBudget, startDate, endDate]);

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
        <span className="text-gray-400">No spend data available</span>
      </div>
    );
  }

  return (
    <div 
      className={`h-64 ${onChartClick ? 'cursor-pointer hover:bg-gray-50 rounded transition-colors' : ''}`}
      onClick={onChartClick}
    >
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={chartData} margin={{ top: 24, right: 10, left: 0, bottom: 24 }}>
          <defs>
            <linearGradient id="spendGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#FF681F" stopOpacity={0.25} />
              <stop offset="95%" stopColor="#FF681F" stopOpacity={0.05} />
            </linearGradient>
          </defs>
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
            tick={{ fontSize: 11, fill: '#6B7280' }} 
            tickLine={false}
            axisLine={{ stroke: '#E5E7EB' }}
            tickFormatter={formatCurrency}
          />
          <Tooltip
            formatter={(value: number, name: string) => [formatCurrency(value), name]}
            labelFormatter={(label) => {
              // Enhanced date formatting for tooltip
              const dataPoint = chartData.find(d => d.formattedDate === label);
              if(!dataPoint) return label || '';

              if (timePeriod === 'quarterly') {
                const match = /^(\d{4})-Q(\d)$/.exec(dataPoint.date);
                if (!match) return label || '';
                return `Q${match[2]} ${match[1]}`;
              }

              if (timePeriod === 'monthly'){
                const match = /^(\d{4})-(\d{2})$/.exec(dataPoint.date);
                if (!match) return label || '';
                const y = Number(match[1]);
                const m = Number(match[2]);
                const dt = new Date(y, m - 1, 1);
                return dt.toLocaleDateString('en-US', {
                  year: 'numeric',
                  month: 'short'
                });
              }

              // daily / weekly / custom: key is YYYY-MM-DD (week start for weekly)
              const dt = parseAnyDate(dataPoint.date);
              if (isNaN(dt.getTime())) return label || '';
              return dt.toLocaleDateString('en-US', {
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
          <Area
            type="monotone"
            dataKey="spend"
            stroke="#FF681F"
            strokeWidth={2}
            fill="url(#spendGradient)"
            dot={false}
            name="Spend (by period)"
          />
          <Line
            type="monotone"
            dataKey="budget"
            stroke="#10B981"
            strokeWidth={2}
            dot={false}
            name="Budget (by period)"
            strokeDasharray="5 5"
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}