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

export type ReconciliationEngineStatus =
  | "MATCHED"
  | "PARTIALLY_MATCHED"
  | "MISMATCHED"
  | "PENDING"
  | "UNRESOLVED";

export interface ComponentComparison {
  component: string;
  expected_amount: number;
  actual_amount: number | null;
  difference_amount: number | null;
  matches: boolean;
}

export interface ReconciliationEngineRecord {
  id: string;
  payment_id: string | null;
  settlement_id: string | null;
  order_id: string | null;
  customer_id: string | null;
  payment_method: string | null;
  currency: string;
  payment_created_at: string | null;
  settlement_date: string | null;
  gross_payment: number;
  refund_amount: number;
  fees: number;
  taxes: number;
  expected_settlement: number;
  actual_settlement: number | null;
  difference_amount: number | null;
  difference_percentage: number | null;
  status: ReconciliationEngineStatus;
  possible_reason: string;
  component_comparisons: ComponentComparison[];
}

export interface ReconciliationEngineSummary {
  date_from: string;
  date_to: string;
  total_transactions: number;
  matched_transactions: number;
  partially_matched_transactions: number;
  mismatched_transactions: number;
  pending_transactions: number;
  unresolved_transactions: number;
  total_expected_amount: number;
  total_actual_amount: number;
  total_discrepancy: number;
  reconciliation_rate: number;
  amount_unit: string;
}

export interface ReconciliationExceptionPage {
  items: ReconciliationEngineRecord[];
  total: number;
  limit: number;
  offset: number;
  date_from: string;
  date_to: string;
}

export interface HistoricalCashFlowPoint {
  date: string;
  daily_income: number;
  daily_expenses: number;
  daily_net_cashflow: number;
  cumulative_cash_balance: number;
}

export interface PredictedCashFlowPoint {
  date: string;
  predicted_income: number;
  predicted_expenses: number;
  predicted_net_cashflow: number;
  predicted_balance: number;
  balance_lower: number;
  balance_upper: number;
}

export interface ForecastRisk {
  id: string;
  severity: "high" | "medium" | "low";
  category: string;
  title: string;
  description: string;
  metric_label: string;
  metric_value: string;
  source: string;
}

export interface CashFlowForecastResponse {
  horizon_days: 7 | 30 | 90;
  as_of_date: string;
  history_start: string;
  history_end: string;
  opening_cash_balance: number;
  current_cash_balance: number;
  expected_incoming: number;
  expected_outgoing: number;
  forecasted_balance: number;
  confidence_level: number;
  confidence_label: string;
  model_name: string;
  methodology: string;
  amount_unit: string;
  historical: HistoricalCashFlowPoint[];
  forecast: PredictedCashFlowPoint[];
  risks: ForecastRisk[];
}

export interface FinancialToolResult {
  tool_name: string;
  classification: "fact" | "prediction";
  period_label: string;
  generated_at: string;
  data: Record<string, unknown>;
  source_refs: string[];
  insufficient_data: boolean;
}

export interface CfoSource {
  id: string;
  tool_name: string;
  label: string;
  classification: "fact" | "prediction";
  period: string;
}

export interface CfoChatRequest {
  question: string;
}

export interface CfoChatResponse {
  id: string;
  question: string;
  answer: string;
  mode: "deterministic" | "ollama" | "deterministic_fallback";
  facts: string[];
  predictions: string[];
  reasoning: string[];
  recommendations: string[];
  sources: CfoSource[];
  tools_used: string[];
  insufficient_data: boolean;
  read_only: boolean;
  provider_message: string;
}

export interface DailyInsight {
  id: string;
  category: string;
  severity: "high" | "medium" | "low";
  title: string;
  summary: string;
  metric_label: string;
  metric_value: string;
  classification: "fact" | "prediction";
  source_tool: string;
  source_ref: string;
  action: string;
}

export interface DailyInsightsResponse {
  as_of_date: string;
  generated_at: string;
  mode: "deterministic" | "ollama" | "deterministic_fallback";
  disclaimer: string;
  insights: DailyInsight[];
}

export interface MetricEvidence {
  id: string;
  type: string;
  label: string;
  date: string;
  amount: number;
  status: string;
}

export interface ExecutiveMetric {
  id: "revenue" | "current_balance" | "cash_forecast" | "reconciliation_exceptions";
  label: string;
  value: number;
  value_kind: "currency" | "count";
  change_percent: number | null;
  trend: "up" | "down" | "neutral";
  period_label: string;
  detail: string;
  explanation: string;
  calculation: string;
  source_metric: string;
  source_tool: string;
  drilldown_path: string;
  evidence: MetricEvidence[];
}

export interface ExecutiveReconciliation {
  transactions_analyzed: number;
  matched: number;
  partially_matched: number;
  mismatched: number;
  pending: number;
  unresolved: number;
  total_discrepancy: number;
  reconciliation_rate: number;
}

export interface ExecutiveDashboardResponse {
  as_of_date: string;
  metrics: ExecutiveMetric[];
  cashflow_actual: HistoricalCashFlowPoint[];
  cashflow_forecast: PredictedCashFlowPoint[];
  reconciliation: ExecutiveReconciliation;
  insights: DailyInsight[];
  insight_mode: string;
  amount_unit: string;
}

export interface DemoScenario {
  id: string;
  name: string;
  description: string;
  signal: string;
  expected_effects: string[];
  active: boolean;
}

export interface DemoScenarioList {
  active_scenario_id: string;
  scenarios: DemoScenario[];
}

export interface DemoScenarioActivation {
  active_scenario_id: string;
  activated_at: string;
  dataset_run_id: string;
  payment_count: number;
  generated_records: Record<string, number>;
  message: string;
}