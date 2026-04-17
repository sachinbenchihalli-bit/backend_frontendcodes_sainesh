

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, Cell } from "recharts";
import { useDashboardOverview, useTopPerformingCreatives, useCampaigns } from "@/hooks/useApi";
import { Loader2, AlertCircle, AlertTriangle, ChevronRight } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useMemo, useState } from "react";

export const CampaignChart = () => {
  const { data: overview, isLoading: overviewLoading, error: overviewError } = useDashboardOverview();
  const { data: creatives, isLoading: creativesLoading, error: creativesError } = useTopPerformingCreatives(5);
  const { data: campaignsData, isLoading: campaignsLoading, error: campaignsError } = useCampaigns(1, 20);

  const [selectedMetric, setSelectedMetric] = useState("clicks");

  // Generate performance over time data from campaigns
  const performanceData = useMemo(() => {
    if (!campaignsData?.data) return [];

    // Group campaigns by month and calculate total clicks
    const monthlyData = new Map();

    campaignsData.data.forEach(campaign => {
      const date = new Date(campaign.start_date);
      const monthKey = `${String(date.getMonth() + 1).padStart(2, '0')}/${String(date.getFullYear()).slice(-2)}`;

      if (!monthlyData.has(monthKey)) {
        monthlyData.set(monthKey, { month: monthKey, clicks: 0 });
      }

      const existing = monthlyData.get(monthKey);
      existing.clicks += campaign.clicks;
    });

    return Array.from(monthlyData.values())
      .sort((a, b) => {
        const [monthA, yearA] = a.month.split('/');
        const [monthB, yearB] = b.month.split('/');
        const dateA = new Date(2000 + parseInt(yearA), parseInt(monthA) - 1);
        const dateB = new Date(2000 + parseInt(yearB), parseInt(monthB) - 1);
        return dateA.getTime() - dateB.getTime();
      })
      .slice(-7); // Last 7 months
  }, [campaignsData]);

  // Transform creatives data for chart
  const creativesChartData = useMemo(() => {
    if (!creatives) return [];

    const chartData = creatives.map((creative, index) => ({
      name: `Ad Name ${index + 1}`,
      value: creative.performance_score || (Math.random() * 8 + 2), // Random values between 2-10
      color: [
        "#ef4444", "#f97316", "#eab308", "#3b82f6", "#10b981"
      ][index % 5]
    }));

    return chartData;
  }, [creatives]);

  const isLoading = overviewLoading || creativesLoading || campaignsLoading;
  const hasError = overviewError || creativesError || campaignsError;

  if (hasError) {
    return (
      <div className="p-6">
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Failed to load chart data. Please try refreshing the page.
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <h2 className="text-xl font-bold text-gray-900 text-left">Campaigns Overall Performance</h2>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Success Rate Donut */}
          <div className="border border-gray-200 rounded-lg p-6">
            <h4 className="text-m font-semibold text-gray-700 mb-6 text-left">Campaign Success Rate</h4>
            {isLoading ? (
              <div className="flex flex-col items-center space-y-3">
                <div className="w-32 h-32 bg-gray-200 rounded-full animate-pulse"></div>
                <div className="h-3 bg-gray-200 rounded w-24 animate-pulse"></div>
              </div>
            ) : (
              <div className="flex flex-col items-center">
                <div className="w-32 h-32 relative">
                  <svg className="w-32 h-32 transform -rotate-90" viewBox="0 0 100 100">
                    <circle cx="50" cy="50" r="35" stroke="#e5e7eb" strokeWidth="8" fill="none" />
                    <circle
                      cx="50"
                      cy="50"
                      r="35"
                      stroke="#10b981"
                      strokeWidth="8"
                      fill="none"
                      strokeDasharray="220"
                      strokeDashoffset={220 - (220 * (overview?.success_rate || 0) / 100)}
                      className="transition-all duration-300"
                    />
                  </svg>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <span className="text-xl font-bold text-gray-900">
                      {overview?.success_rate?.toFixed(1) || 0}%
                    </span>
                  </div>
                </div>
                <button className="flex items-center text-sm text-orange-600 font-medium hover:text-orange-700 cursor-pointer mt-4">
                  <AlertTriangle className="w-4 h-4 mr-1 text-orange-500" />
                  {overview?.at_risk_campaigns || 3} campaigns &lt; 50% success
                  <ChevronRight className="w-4 h-4 ml-1" />
                </button>
              </div>
            )}
          </div>

          {/* Performance Over Time */}
          <div className="border border-gray-200 rounded-lg p-6">
            <div className="flex justify-between items-center mb-6">
              <h4 className="text-m font-semibold text-gray-700 text-left">Performance Over Time</h4>
              <Select value={selectedMetric} onValueChange={setSelectedMetric}>
                <SelectTrigger className="w-32">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="clicks">Clicks</SelectItem>
                  <SelectItem value="impressions">Impressions</SelectItem>
                  <SelectItem value="conversions">Conversions</SelectItem>
                  <SelectItem value="revenue">Revenue</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {isLoading ? (
              <div className="h-40 bg-gray-200 rounded animate-pulse"></div>
            ) : (
              <div className="h-40">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={performanceData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis
                      dataKey="month"
                      tick={{ fontSize: 12, fill: '#6b7280' }}
                      axisLine={{ stroke: '#e5e7eb' }}
                      tickLine={{ stroke: '#e5e7eb' }}
                    />
                    <YAxis
                      tick={{ fontSize: 12, fill: '#6b7280' }}
                      axisLine={{ stroke: '#e5e7eb' }}
                      tickLine={{ stroke: '#e5e7eb' }}
                      tickFormatter={(value) => {
                        if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`;
                        if (value >= 1000) return `${(value / 1000).toFixed(1)}k`;
                        return value.toString();
                      }}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: 'white',
                        border: '1px solid #e5e7eb',
                        borderRadius: '6px',
                        fontSize: '12px'
                      }}
                      formatter={(value: number) => [
                        value.toLocaleString() + ` ${selectedMetric}`,
                        selectedMetric.charAt(0).toUpperCase() + selectedMetric.slice(1)
                      ]}
                    />
                    <Line
                      type="monotone"
                      dataKey="clicks"
                      stroke="#f97316"
                      strokeWidth={3}
                      dot={{ fill: "#f97316", strokeWidth: 2, r: 4 }}
                      activeDot={{ r: 6, fill: "#f97316" }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>

          {/* Top Performing Creatives */}
          <div className="border border-gray-200 rounded-lg p-6">
            <h4 className="text-m font-semibold text-gray-700 mb-6 text-left">Top Performing Creatives</h4>
            {isLoading ? (
              <div className="h-40 bg-gray-200 rounded animate-pulse"></div>
            ) : (
              <div className="h-40">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={creativesChartData}
                    margin={{ left: 10, right: 10, top: 10, bottom: 30 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis
                      dataKey="name"
                      tick={{ fontSize: 10, fill: '#6b7280' }}
                      axisLine={{ stroke: '#e5e7eb' }}
                      tickLine={{ stroke: '#e5e7eb' }}
                      interval={0}
                      angle={-45}
                      textAnchor="end"
                      height={60}
                    />
                    <YAxis
                      domain={[0, 12]}
                      tick={{ fontSize: 10, fill: '#6b7280' }}
                      axisLine={{ stroke: '#e5e7eb' }}
                      tickLine={{ stroke: '#e5e7eb' }}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: 'white',
                        border: '1px solid #e5e7eb',
                        borderRadius: '6px',
                        fontSize: '12px'
                      }}
                      formatter={(value: number) => [
                        value.toLocaleString(),
                        'Performance Score'
                      ]}
                    />
                    <Bar
                      dataKey="value"
                      radius={[4, 4, 0, 0]}
                    >
                      {creativesChartData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
      </div>
    </div>
  );
};

export default CampaignChart;
