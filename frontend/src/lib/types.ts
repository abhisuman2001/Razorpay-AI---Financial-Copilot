export type TransactionStatus = "matched" | "exception" | "pending";
export type InsightPriority = "high" | "medium" | "low";

export interface ReconciliationItem {
  id: string;
  date: string;
  reference: string;
  category: string;
  expected_amount: number;
  actual_amount: number;
  variance: number;
  status: TransactionStatus;
}

export interface ReconciliationSummary {
  period_label: string;
  total_transactions: number;
  matched_count: number;
  exception_count: number;
  pending_count: number;
  total_volume: number;
  matched_volume: number;
  exception_value: number;
  match_rate: number;
}

export interface ReconciliationResponse {
  summary: ReconciliationSummary;
  items: ReconciliationItem[];
}

export interface ForecastPoint {
  period: string;
  label: string;
  actual: number | null;
  forecast: number | null;
  lower: number | null;
  upper: number | null;
  is_forecast: boolean;
}

export interface ForecastResponse {
  horizon_weeks: number;
  current_cash: number;
  ending_cash: number;
  change_percent: number;
  confidence_label: string;
  points: ForecastPoint[];
}

export interface Insight {
  id: string;
  priority: InsightPriority;
  title: string;
  body: string;
  metric_label: string;
  metric_value: string;
  action: string;
  source: string;
}

export interface CfoResponse {
  generated_by: string;
  disclaimer: string;
  insights: Insight[];
}

export interface DashboardSummary {
  cash_balance: number;
  cash_delta_percent: number;
  incoming_30d: number;
  outgoing_30d: number;
  runway_weeks: number;
  reconciliation_rate: number;
  open_exceptions: number;
  data_as_of: string;
}

export interface DashboardResponse {
  summary: DashboardSummary;
  reconciliation: ReconciliationSummary;
  forecast: ForecastResponse;
  insights: Insight[];
}