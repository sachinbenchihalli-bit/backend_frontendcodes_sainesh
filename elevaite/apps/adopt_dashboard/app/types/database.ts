// Database-specific types that map to PostgreSQL schema

export interface DatabaseCampaign {
  id: string; // UUID as string
  insertion_order_id: string | null; // UUID as string
  campaign_id: string | null; // Reference to original campaign_data_table
  name: string;
  product: string | null;
  start_date: string; // DATE as string
  end_date: string; // DATE as string
  impressions_booked: number;
  impressions_delivered: number;
  clicks: number;
  conversions: number;
  ctr: number; // NUMERIC(10, 6)
  budget: number; // NUMERIC(15, 2)
  spend: number; // NUMERIC(15, 2)
  roas: number; // NUMERIC(10, 2)
  status: string; // VARCHAR(50)
  success_rate: number; // NUMERIC(5, 2)
  created_at: string; // TIMESTAMP WITH TIME ZONE as string
  updated_at: string; // TIMESTAMP WITH TIME ZONE as string
}

export interface DatabaseCreative {
  id: string; // UUID as string
  campaign_id: string; // UUID as string
  creative_id: string | null; // UUID as string, nullable
  name: string;
  file_type: string | null;
  impressions: number;
  clicks: number;
  conversions: number;
  ctr: number; // NUMERIC(10, 6)
  created_at: string; // TIMESTAMP WITH TIME ZONE as string
}

export interface DatabasePerformanceSnapshot {
  id: string; // UUID as string
  campaign_id: string; // UUID as string
  snapshot_date: string; // DATE as string
  impressions: number;
  clicks: number;
  conversions: number;
  spend: number; // NUMERIC(15, 2)
  ctr: number; // NUMERIC(10, 6)
  created_at: string; // TIMESTAMP WITH TIME ZONE as string
}

export interface DatabaseTodoItem {
  id: string; // UUID as string
  title: string;
  description: string | null;
  priority: string; // VARCHAR(20)
  due_date: string; // DATE as string
  status: string; // VARCHAR(20)
  assigned_to: string | null;
  created_at: string; // TIMESTAMP WITH TIME ZONE as string
}

export interface DatabaseInsertionOrder {
  id: string; // UUID as string
  name: string;
  status: string; // VARCHAR(50)
  start_date: string; // DATE as string
  end_date: string; // DATE as string
  budget: number; // NUMERIC(15, 2)
  spent: number; // NUMERIC(15, 2)
  remaining: number | null; // NUMERIC(15, 2)
  days_left: number | null;
  campaign_count: number | null;
  created_at: string; // TIMESTAMP WITH TIME ZONE as string
}

// Database query result types for aggregations
export interface DashboardOverviewQueryResult {
  total_campaigns_active: string; // COUNT returns string
  total_insertion_orders: string; // COUNT returns string
  success_rate: string | null; // AVG returns string or null
  campaigns_in_flight: string; // COUNT returns string
  campaigns_at_risk: string; // COUNT returns string
  total_spend: string | null; // SUM returns string or null
  total_budget: string | null; // SUM returns string or null
  total_impressions: string | null; // SUM returns string or null
  total_clicks: string | null; // SUM returns string or null
  average_ctr: string | null; // AVG returns string or null
  average_roas: string | null; // AVG returns string or null
}

// Utility type for database connection errors
export interface DatabaseError extends Error {
  code?: string;
  detail?: string;
  hint?: string;
  position?: string;
  internalPosition?: string;
  internalQuery?: string;
  where?: string;
  schema?: string;
  table?: string;
  column?: string;
  dataType?: string;
  constraint?: string;
  file?: string;
  line?: string;
  routine?: string;
}

// Database connection status
export interface DatabaseConnectionStatus {
  connected: boolean;
  error?: string;
  lastChecked: Date;
}
