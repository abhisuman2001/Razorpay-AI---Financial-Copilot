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

export interface CustomerRecord {
  customer_id: string;
  name: string;
  email: string;
  phone: string;
  city: string;
  state: string;
  segment: string;
  created_at: string;
}

export interface OrderRecord {
  order_id: string;
  customer_id: string;
  amount: number;
  currency: string;
  status: string;
  receipt: string;
  created_at: string;
}

export interface PaymentRecord {
  payment_id: string;
  order_id: string;
  customer_id: string;
  amount: number;
  currency: string;
  status: string;
  payment_method: string;
  created_at: string;
  captured_at: string | null;
}

export interface RefundRecord {
  refund_id: string;
  payment_id: string;
  amount: number;
  currency: string;
  status: string;
  reason: string;
  created_at: string;
  processed_at: string | null;
}

export interface SettlementRecord {
  settlement_id: string;
  payment_id: string | null;
  external_reference: string;
  gross_amount: number;
  refund_amount: number;
  fees: number;
  taxes: number;
  net_settlement: number;
  settlement_date: string;
  status: string;
}

export interface ExpenseRecord {
  expense_id: string;
  category: string;
  vendor: string;
  amount: number;
  currency: string;
  date: string;
  recurring: boolean;
  payment_mode: string;
}

export interface ChargebackRecord {
  chargeback_id: string;
  payment_id: string;
  amount: number;
  reason_code: string;
  status: string;
  opened_at: string;
  due_at: string;
  resolved_at: string | null;
}

export interface FailedPaymentRecord {
  failed_payment_id: string;
  payment_id: string;
  error_code: string;
  error_description: string;
  failure_stage: string;
  retryable: boolean;
  failed_at: string;
}

export interface AnomalyRecord {
  anomaly_id: string;
  dataset_run_id: string;
  anomaly_type: string;
  entity_type: string;
  entity_id: string;
  related_entity_id: string | null;
  expected_amount: number | null;
  actual_amount: number | null;
  description: string;
  created_at: string;
}

export interface DatasetPage<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface DatasetCounts {
  customers: number;
  orders: number;
  payments: number;
  refunds: number;
  settlements: number;
  expenses: number;
  chargebacks: number;
  failed_payments: number;
  anomalies: number;
}

export interface AnomalyCount {
  anomaly_type: string;
  count: number;
}

export interface DatasetSummary {
  dataset_run_id: string;
  seed: number;
  generated_at: string;
  period_start: string;
  period_end: string;
  amount_unit: string;
  counts: DatasetCounts;
  anomalies_by_type: AnomalyCount[];
}