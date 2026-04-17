// Campaign and Performance Data Types
export interface Campaign {
  id: string;
  insertion_order_id?: string;
  name: string;
  kevel_id?: string;
  start_date: string;
  end_date: string;
  impressions_booked: number;
  impressions_delivered: number;
  booked_clicks?: number; // Target clicks from campaign_placements.booked_clicks
  clicks: number; // Delivered clicks from campaign_placements.delivered_clicks
  ctr: number;
  budget: number;
  spend: number;
  revenue?: number;
  cpm?: number;
  cpc?: number;
  conversions: number;
  roas: number;
  status: 'draft' | 'active' | 'paused' | 'completed' | 'work_in_progress';
  created_at: string;
  updated_at: string;
  brand?: string;

  // Placeholder synthetic data fields (will show N/A for now)
  platform_channel?: string;
  campaign_objective?: string;
  audience_segment?: string;
  creative_type?: string;
}

export interface CampaignPerformanceSnapshot {
  id: string;
  campaign_id: string;
  snapshot_date: string;
  snapshot_hour?: number;
  impressions_delivered: number;
  clicks: number;
  spend: number;
  conversions: number;
  conversion_value: number;
  created_at: string;
}

export interface CampaignHealthMetric {
  id: string;
  campaign_id: string;
  health_score: number;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  issues: HealthIssue[];
  suggested_actions: SuggestedAction[];
  last_updated: string;
}

export interface HealthIssue {
  type: 'low_ctr' | 'low_conversion' | 'underspend' | 'overspend' | 'delivery_issue';
  severity: 'low' | 'medium' | 'high' | 'critical';
  message: string;
}

export interface SuggestedAction {
  action: 'review_creative' | 'optimize_landing_page' | 'increase_bids' | 'decrease_bids' | 'adjust_targeting';
  message: string;
}

export interface CampaignCreative {
  id: string;
  campaign_id: string;
  creative_id: string;
  weight: number;
  start_date: string;
  end_date: string;
  status: 'active' | 'paused' | 'completed';
  created_at: string;
}

export interface CreativePerformance {
  id: string;
  creative_id: string;
  campaign_id: string;
  impressions: number;
  clicks: number;
  ctr: number;
  conversions: number;
  conversion_rate: number;
  spend: number;
  date: string;
  created_at: string;
}

export interface CampaignBenchmark {
  id: string;
  campaign_type: 'brand_awareness' | 'conversion' | 'retargeting';
  benchmark_ctr: number;
  benchmark_conversion_rate: number;
  benchmark_cpm: number;
  benchmark_cpc: number;
  benchmark_roas: number;
  created_at: string;
  updated_at: string;
}

// Dashboard Overview Types
export interface DashboardOverview {
  total_campaigns_active: number;
  total_insertion_orders: number;
  success_rate: number;
  campaigns_in_flight: number;
  campaigns_at_risk: number;
  total_spend: number;
  total_budget: number;
  total_impressions: number;
  total_clicks: number;
  average_ctr: number;
  average_roas: number;
  spend_vs_budget_percentage: number;
  // Detailed metrics for Key Insights
  io_pending_approval: number;
  io_approved: number;
  io_rejected: number;
  campaigns_wip: number;
  campaigns_paused: number;
  campaigns_completed: number;
}

// API Response Types
export interface ApiResponse<T> {
  data: T;
  success: boolean;
  message?: string;
}

// Kevel API Types
export interface KevelFlightStatus {
  status: string;
  impressions: number;
  clicks: number;
  ctr: number;
  flight_details?: any;
  flight_counts?: any;
}

export interface KevelFlightStatusResponse {
  data: KevelFlightStatus;
  success: boolean;
  message: string;
  source: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  limit: number;
  total_pages: number;
}

// Filter and Query Types
export interface CampaignFilters {
  status?: string[];
  date_range?: {
    start: string;
    end: string;
  };
  search?: string;
  risk_level?: CampaignHealthMetric['risk_level'][];
}

export interface SortOptions {
  field: keyof Campaign;
  direction: 'asc' | 'desc';
}

// Chart Data Types
export interface ChartDataPoint {
  date: string;
  value: number;
  label?: string;
}

export interface PerformanceChartData {
  impressions: ChartDataPoint[];
  clicks: ChartDataPoint[];
  spend: ChartDataPoint[];
  conversions: ChartDataPoint[];
  ctr: ChartDataPoint[];
  roas: ChartDataPoint[];
}

export interface CreativeChartData {
  creative_id: string;
  name: string;
  performance_score: number;
  impressions: number;
  clicks: number;
  conversions: number;
  spend: number;
}

// Task Management Types
export interface Task {
  id: string;
  title: string;
  description?: string;
  priority: 'low' | 'medium' | 'high';
  due_date: string;
  status: 'pending' | 'in_progress' | 'completed' | 'dismissed';
  assigned_to?: string;
  campaign_id?: string;
  created_at: string;
  updated_at?: string;
}

// Error Types
export interface ApiError {
  message: string;
  code?: string;
  details?: any;
}

// Loading States
export interface LoadingState {
  isLoading: boolean;
  error?: ApiError | null;
}

// Date Range Types
export interface DateRange {
  start: Date;
  end: Date;
}

export interface TimeSeriesOptions {
  granularity: 'hourly' | 'daily' | 'weekly' | 'monthly';
  days: number;
}

// Insertion Order Types (matching backend model)
export interface InsertionOrder {
  id: string;
  name: string;
  status: string;
  start_date: string;
  end_date: string;
  budget: number;
  spent: number;
  remaining?: number;
  days_left?: number;
  campaign_count?: number;
  created_at: string;
  // Additional fields for display compatibility with campaigns
  brand?: string;
  roas?: number;
  ctr?: number;
  spend?: number; // Alias for spent
  salesforce_io_id?: string; // Salesforce insertion order ID
  media_plan_url?: string; // Media plan URL
}

// Campaign Optimization Types
export interface CampaignOptimizationRequest {
  message?: string;
  session_id?: string;
  user_id?: string;
}

export interface CampaignOptimizationResponse {
  data: any;
  success: boolean;
  message: string;
  source: string;
  cached?: boolean;
  analysis_timestamp?: string;
}

export interface CampaignAnalysisContext {
  campaign_details: {
    basic_info: {
      campaign_name: string;
      brand: string;
      platform_channel: string;
      campaign_objective: string;
      duration_days: number;
      targeting_type: string;
      audience_segment: string;
      campaign_start: string;
      campaign_end: string;
      age_group: string;
      geo_location: string;
    };
    performance_metrics: {
      spend: number;
      booked_impressions: number;
      delivered_impressions: number;
      clicks: number;
      ctr: number;
      conversions: number;
      conversion_rate: number;
      roas: number;
      cpa: number;
      delivery_rate?: number;
    };
  };
  platform_comparison: {
    platform: string;
    total_platform_campaigns: number;
    platform_averages: {
      ctr: number;
      roas: number;
      impressions: number;
    };
    campaign_vs_platform: {
      ctr: { value: number; difference_percent: number };
      roas: { value: number; difference_percent: number };
      impressions: { value: number; difference_percent: number };
    };
  };
  objective_comparison: {
    objective: string;
    total_objective_campaigns: number;
    objective_averages: {
      ctr: number;
      roas: number;
      impressions: number;
    };
    campaign_vs_objective: {
      ctr: { value: number; difference_percent: number };
      roas: { value: number; difference_percent: number };
      impressions: { value: number; difference_percent: number };
    };
  };
  overall_ranking: {
    total_campaigns: number;
    rankings: {
      ctr: { rank: number; percentile: number };
      roas: { rank: number; percentile: number };
      impressions: { rank: number; percentile: number };
    };
    overall_performance: {
      level: string;
      average_percentile: number;
    };
  };
  similar_better_campaigns: {
    total_better_campaigns: number;
    top_3_campaigns: Array<{
      name: string;
      brand: string;
      platform: string;
      objective: string;
      audience_segment: string;
      duration: number;
      performance: {
        spend: number;
        booked_impressions: number;
        delivered_impressions: number;
        ctr: number;
        roas: number;
        conversions: number;
        conversion_rate: number;
        delivery_rate?: number;
      };
      improvements_vs_current: {
        impressions_percent: number;
        ctr_percent: number;
        roas_percent: number;
      };
    }>;
    analysis_criteria: {
      platform_filter: string;
      objective_filter: string;
      comparison_metrics: string[];
    };
  };
  analysis_metadata: {
    total_campaigns_analyzed: number;
    analysis_timestamp: string;
    campaign_id: string;
  };
}

export interface ChatMessage {
  id: number;
  text: string;
  sender: "user" | "bot";
  timestamp: Date;
  suggestions?: string[];
  isLoading?: boolean;
  error?: string;
}
