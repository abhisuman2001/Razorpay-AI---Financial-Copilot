import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowDownLeft,
  ArrowUpRight,
  Bot,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Database,
  Info,
  Minus,
  ShieldCheck,
  TrendingUp,
  XCircle,
} from "lucide-react";

import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { apiGet } from "@/lib/api";
import { formatDate, formatPaiseINR } from "@/lib/format";
import type { CashBalanceAnalysis, CashBalanceDailyRow, CashBalanceWaterfallRow } from "@/lib/types";

interface CashBalanceAnalysisSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export default function CashBalanceAnalysisSheet({
  open,
  onOpenChange,
}: CashBalanceAnalysisSheetProps) {
  const query = useQuery({
    queryKey: ["cash-balance-analysis"],
    queryFn: () => apiGet<CashBalanceAnalysis>("/why/cash_balance/analysis"),
    enabled: open,
    retry: false,
  });

  const data = query.data;

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full overflow-y-auto p-0 sm:max-w-2xl"
        data-testid="cash-balance-analysis-panel"
      >
        <SheetHeader className="border-b border-slate-100 p-6 text-left">
          <p
            className="text-[10px] font-bold uppercase tracking-[0.14em] text-rose-600"
            data-testid="cba-eyebrow"
          >
            Underlying analysis
          </p>
          <SheetTitle className="font-heading text-xl" data-testid="cba-title">
            Cash Balance Analysis
          </SheetTitle>
          <SheetDescription data-testid="cba-subtitle">
            Trace how the current cash balance was calculated — step by step, from first principles.
          </SheetDescription>
        </SheetHeader>

        {query.isError ? (
          <div
            className="flex items-start gap-3 p-6 text-sm text-amber-700"
            data-testid="cba-error"
          >
            <XCircle size={16} className="mt-0.5 shrink-0" />
            The cash balance analysis could not be loaded from the financial engine.
          </div>
        ) : data ? (
          <div className="space-y-7 p-6" data-testid="cba-content">
            {/* ── Period + validation banner ────────────────────────────── */}
            <div
              className="flex items-start justify-between gap-4 rounded-lg border border-slate-200 bg-slate-50 p-4"
              data-testid="cba-period-banner"
            >
              <div>
                <p className="text-[9px] font-bold uppercase tracking-[0.13em] text-slate-400">
                  Analysis period
                </p>
                <p className="mt-1 text-xs font-medium text-slate-700">
                  {formatDate(data.period_start)} → {formatDate(data.period_end)}
                </p>
              </div>
              <ValidationBadge
                rounding={data.rounding_difference}
                testId="cba-validation-badge"
              />
            </div>

            {/* ── Waterfall ─────────────────────────────────────────────── */}
            <section data-testid="cba-waterfall-section">
              <SectionHeader
                label="Calculation"
                title="How the balance was built"
                icon={<TrendingUp size={14} />}
              />
              <div
                className="mt-3 divide-y divide-slate-100 overflow-hidden rounded-lg border border-slate-200"
                data-testid="cba-waterfall"
              >
                {data.waterfall.map((row) => (
                  <WaterfallRow key={row.id} row={row} />
                ))}
              </div>
            </section>

            {/* ── Opening balance ───────────────────────────────────────── */}
            <section data-testid="cba-opening-section">
              <SectionHeader
                label="Starting point"
                title="Opening cash balance"
                icon={<Database size={14} />}
              />
              <div className="mt-3 rounded-lg border border-slate-200 bg-white p-5">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-mono text-2xl font-medium text-slate-900" data-testid="cba-opening-value">
                      {formatPaiseINR(data.opening_balance)}
                    </p>
                    <p className="mt-1 text-[10px] text-slate-500" data-testid="cba-opening-date">
                      Effective from {formatDate(data.opening_balance_date)}
                    </p>
                  </div>
                  {data.opening_balance_configurable && (
                    <span className="rounded-full bg-slate-100 px-2 py-1 text-[9px] font-bold uppercase tracking-wide text-slate-500">
                      Configurable
                    </span>
                  )}
                </div>
                <div className="mt-4 space-y-1.5 border-t border-slate-100 pt-4">
                  <SourceRow
                    label="Source"
                    value={data.opening_balance_source}
                    testId="cba-opening-source"
                  />
                  <SourceRow
                    label="Configurable"
                    value={data.opening_balance_configurable ? "Yes — set via environment variable" : "No"}
                    testId="cba-opening-configurable"
                  />
                </div>
              </div>
            </section>

            {/* ── Inflows ───────────────────────────────────────────────── */}
            <section data-testid="cba-inflows-section">
              <SectionHeader
                label="Income / Inflows"
                title="Cash received"
                icon={<ArrowDownLeft size={14} className="text-emerald-600" />}
              />
              <div className="mt-3 space-y-3">
                <InflowCard
                  label="Settled cash received"
                  description="Net settled cash recognized on settlement dates (gross payment minus refunds, fees, and taxes already deducted by the gateway)."
                  amount={data.total_settled_cash}
                  recordCount={data.settlement_record_count}
                  sourceTable="settlements.net_settlement"
                  testId="cba-settled-cash"
                  details={[
                    { label: "Fees already deducted", value: formatPaiseINR(data.settlement_fees_total) },
                    { label: "Refunds already deducted", value: formatPaiseINR(data.settlement_refunds_total) },
                  ]}
                />
                {data.total_other_income > 0 && (
                  <InflowCard
                    label="Other recognized income"
                    description="Additional income types recognized in the current dataset."
                    amount={data.total_other_income}
                    recordCount={0}
                    sourceTable="—"
                    testId="cba-other-income"
                    details={[]}
                  />
                )}
              </div>
            </section>

            {/* ── Outflows ──────────────────────────────────────────────── */}
            <section data-testid="cba-outflows-section">
              <SectionHeader
                label="Expenses / Outflows"
                title="Cash paid out"
                icon={<ArrowUpRight size={14} className="text-rose-600" />}
              />
              <div className="mt-3">
                <OutflowCard
                  label="Booked expenses"
                  description="Operating expenses recognized on their booked dates (payroll, software, marketing, logistics, etc.)."
                  amount={data.total_expenses}
                  recordCount={data.expense_record_count}
                  sourceTable="expenses.amount"
                  testId="cba-expenses"
                />
              </div>
            </section>

            {/* ── Daily breakdown ───────────────────────────────────────── */}
            <section data-testid="cba-daily-section">
              <SectionHeader
                label="Day-by-day movement"
                title="Daily cash flow breakdown"
                icon={<Info size={14} />}
              />
              <p className="mb-3 text-[11px] text-slate-500">
                Showing the last 30 days. Each row shows settled inflows, booked outflows,
                net movement, and ending cash balance.
              </p>
              <DailyBreakdownTable
                rows={data.daily_breakdown.slice(-30)}
                testId="cba-daily-table"
              />
            </section>

            {/* ── Why this matters ──────────────────────────────────────── */}
            <section
              className="rounded-lg border border-rose-100 bg-rose-50/60 p-5"
              data-testid="cba-why-matters"
            >
              <div className="flex items-center gap-2">
                <Bot size={13} className="text-rose-600" />
                <p className="text-[10px] font-bold uppercase tracking-[0.13em] text-rose-700">
                  Why this matters
                </p>
              </div>
              <p
                className="mt-3 text-sm leading-7 text-slate-700"
                data-testid="cba-why-matters-text"
              >
                {data.why_this_matters}
              </p>
              <p
                className="mt-3 flex items-center gap-1.5 text-[9px] font-semibold uppercase tracking-wide text-slate-400"
                data-testid="cba-classification-note"
              >
                <ShieldCheck size={11} className="text-emerald-500" />
                Recorded financial facts · No LLM involvement
              </p>
            </section>

            {/* ── Calculation method ────────────────────────────────────── */}
            <div
              className="rounded-lg border border-slate-200 bg-slate-50 p-4"
              data-testid="cba-methodology"
            >
              <p className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-[0.13em] text-slate-500">
                <Info size={12} />
                Calculation method
              </p>
              <p
                className="mt-2 font-mono text-[10px] leading-5 text-slate-600"
                data-testid="cba-method-text"
              >
                {data.calculation_method}
              </p>
            </div>
          </div>
        ) : (
          <div
            className="flex items-center gap-3 p-8 text-sm text-slate-500"
            data-testid="cba-loading"
          >
            <span className="h-2 w-2 animate-pulse rounded-full bg-rose-500" />
            Loading cash balance breakdown from the financial engine…
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────

function SectionHeader({
  label,
  title,
  icon,
}: {
  label: string;
  title: string;
  icon: React.ReactNode;
}) {
  return (
    <div className="mb-1 flex items-center gap-2">
      <span className="text-slate-400">{icon}</span>
      <div>
        <p className="text-[9px] font-bold uppercase tracking-[0.13em] text-slate-400">{label}</p>
        <h3 className="font-heading text-sm font-bold text-slate-900">{title}</h3>
      </div>
    </div>
  );
}

function ValidationBadge({
  rounding,
  testId,
}: {
  rounding: number;
  testId: string;
}) {
  const isExact = rounding === 0;
  return (
    <div
      className={`flex items-center gap-1.5 rounded-full px-3 py-1.5 text-[10px] font-bold ${
        isExact
          ? "bg-emerald-50 text-emerald-700"
          : "bg-amber-50 text-amber-700"
      }`}
      data-testid={testId}
    >
      {isExact ? (
        <CheckCircle2 size={12} />
      ) : (
        <Info size={12} />
      )}
      {isExact
        ? "Balance reconciles exactly"
        : `Rounding diff: ${formatPaiseINR(Math.abs(rounding))}`}
    </div>
  );
}

function WaterfallRow({ row }: { row: CashBalanceWaterfallRow }) {
  const [expanded, setExpanded] = useState(false);
  const isPositive = row.amount >= 0;
  const amountColor = row.is_subtotal
    ? "text-slate-900"
    : isPositive
    ? "text-emerald-700"
    : "text-rose-700";

  return (
    <div
      className={`${row.is_subtotal ? "bg-slate-950 text-white" : "bg-white"}`}
      data-testid={`cba-waterfall-${row.id}`}
    >
      <div className="flex items-center justify-between px-4 py-3">
        <div className="flex items-center gap-3 min-w-0">
          <span
            className={`flex h-5 w-5 shrink-0 items-center justify-center rounded ${
              row.is_subtotal
                ? "bg-slate-700 text-slate-200"
                : isPositive
                ? "bg-emerald-50 text-emerald-600"
                : "bg-rose-50 text-rose-600"
            }`}
          >
            {row.is_subtotal ? (
              <Minus size={10} />
            ) : isPositive ? (
              <ArrowDownLeft size={10} />
            ) : (
              <ArrowUpRight size={10} />
            )}
          </span>
          <div className="min-w-0">
            <p
              className={`text-xs font-medium ${row.is_subtotal ? "text-white" : "text-slate-700"}`}
              data-testid={`cba-waterfall-${row.id}-label`}
            >
              {row.label}
            </p>
            {row.record_count > 0 && (
              <p className="mt-0.5 text-[9px] text-slate-400" data-testid={`cba-waterfall-${row.id}-records`}>
                {row.record_count.toLocaleString("en-IN")} records
              </p>
            )}
          </div>
        </div>

        <div className="flex items-center gap-3">
          <p
            className={`font-mono text-sm font-medium ${amountColor}`}
            data-testid={`cba-waterfall-${row.id}-amount`}
          >
            {formatPaiseINR(Math.abs(row.amount))}
          </p>
          {!row.is_subtotal && (
            <button
              type="button"
              onClick={() => setExpanded((v) => !v)}
              className="text-slate-300 hover:text-slate-500"
              aria-label={`${expanded ? "Collapse" : "Expand"} source details for ${row.label}`}
              data-testid={`cba-waterfall-${row.id}-toggle`}
            >
              {expanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
            </button>
          )}
        </div>
      </div>

      {expanded && !row.is_subtotal && (
        <div
          className="border-t border-slate-100 bg-slate-50 px-4 py-3 space-y-2"
          data-testid={`cba-waterfall-${row.id}-details`}
        >
          <p className="text-[10px] leading-5 text-slate-500">{row.description}</p>
          <div className="flex flex-wrap gap-2">
            <span className="inline-flex items-center gap-1 rounded bg-white border border-slate-200 px-2 py-1 font-mono text-[9px] text-slate-500">
              <Database size={9} />
              {row.source_table}
            </span>
            {row.record_count > 0 && (
              <span className="inline-flex items-center gap-1 rounded bg-white border border-slate-200 px-2 py-1 font-mono text-[9px] text-slate-500">
                {row.record_count.toLocaleString("en-IN")} records included
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function InflowCard({
  label,
  description,
  amount,
  recordCount,
  sourceTable,
  testId,
  details,
}: {
  label: string;
  description: string;
  amount: number;
  recordCount: number;
  sourceTable: string;
  testId: string;
  details: Array<{ label: string; value: string }>;
}) {
  const [showSource, setShowSource] = useState(false);
  return (
    <div
      className="rounded-lg border border-slate-200 bg-white p-4"
      data-testid={testId}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-xs font-bold text-slate-800" data-testid={`${testId}-label`}>
            {label}
          </p>
          <p className="mt-1 text-[10px] leading-4 text-slate-500">{description}</p>
        </div>
        <div className="ml-4 text-right">
          <p
            className="font-mono text-lg font-medium text-emerald-700"
            data-testid={`${testId}-amount`}
          >
            {formatPaiseINR(amount)}
          </p>
          {recordCount > 0 && (
            <p className="mt-0.5 text-[9px] text-slate-400" data-testid={`${testId}-count`}>
              {recordCount.toLocaleString("en-IN")} records
            </p>
          )}
        </div>
      </div>
      {details.length > 0 && (
        <div className="mt-3 grid grid-cols-2 gap-2 border-t border-slate-100 pt-3">
          {details.map((d) => (
            <div key={d.label}>
              <p className="text-[9px] text-slate-400">{d.label}</p>
              <p className="mt-0.5 font-mono text-[10px] text-slate-600">{d.value}</p>
            </div>
          ))}
        </div>
      )}
      <button
        type="button"
        onClick={() => setShowSource((v) => !v)}
        className="mt-3 inline-flex items-center gap-1 text-[9px] font-bold text-slate-400 hover:text-rose-700 transition-colors"
        data-testid={`${testId}-source-toggle`}
      >
        <Database size={9} />
        {showSource ? "Hide" : "View"} source details
        {showSource ? <ChevronUp size={9} /> : <ChevronDown size={9} />}
      </button>
      {showSource && (
        <div
          className="mt-2 rounded-md border border-slate-100 bg-slate-50 p-3"
          data-testid={`${testId}-source-details`}
        >
          <p className="text-[9px] text-slate-400">Source table / field</p>
          <p className="mt-1 font-mono text-[10px] text-slate-700">{sourceTable}</p>
        </div>
      )}
    </div>
  );
}

function OutflowCard({
  label,
  description,
  amount,
  recordCount,
  sourceTable,
  testId,
}: {
  label: string;
  description: string;
  amount: number;
  recordCount: number;
  sourceTable: string;
  testId: string;
}) {
  const [showSource, setShowSource] = useState(false);
  return (
    <div
      className="rounded-lg border border-slate-200 bg-white p-4"
      data-testid={testId}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-xs font-bold text-slate-800" data-testid={`${testId}-label`}>
            {label}
          </p>
          <p className="mt-1 text-[10px] leading-4 text-slate-500">{description}</p>
        </div>
        <div className="ml-4 text-right">
          <p
            className="font-mono text-lg font-medium text-rose-700"
            data-testid={`${testId}-amount`}
          >
            {formatPaiseINR(amount)}
          </p>
          <p className="mt-0.5 text-[9px] text-slate-400" data-testid={`${testId}-count`}>
            {recordCount.toLocaleString("en-IN")} records
          </p>
        </div>
      </div>
      <button
        type="button"
        onClick={() => setShowSource((v) => !v)}
        className="mt-3 inline-flex items-center gap-1 text-[9px] font-bold text-slate-400 hover:text-rose-700 transition-colors"
        data-testid={`${testId}-source-toggle`}
      >
        <Database size={9} />
        {showSource ? "Hide" : "View"} source details
        {showSource ? <ChevronUp size={9} /> : <ChevronDown size={9} />}
      </button>
      {showSource && (
        <div
          className="mt-2 rounded-md border border-slate-100 bg-slate-50 p-3"
          data-testid={`${testId}-source-details`}
        >
          <p className="text-[9px] text-slate-400">Source table / field</p>
          <p className="mt-1 font-mono text-[10px] text-slate-700">{sourceTable}</p>
        </div>
      )}
    </div>
  );
}

function DailyBreakdownTable({
  rows,
  testId,
}: {
  rows: CashBalanceDailyRow[];
  testId: string;
}) {
  return (
    <div
      className="overflow-hidden rounded-lg border border-slate-200"
      data-testid={testId}
    >
      {/* Header */}
      <div className="grid grid-cols-5 gap-0 border-b border-slate-200 bg-slate-50 px-3 py-2 text-[9px] font-bold uppercase tracking-wide text-slate-400">
        <span>Date</span>
        <span className="text-right">Inflows</span>
        <span className="text-right">Outflows</span>
        <span className="text-right">Net</span>
        <span className="text-right">Ending balance</span>
      </div>
      {/* Rows */}
      <div className="divide-y divide-slate-100 bg-white max-h-72 overflow-y-auto">
        {rows.map((row) => (
          <div
            key={row.date}
            className="grid grid-cols-5 gap-0 px-3 py-2 text-[10px] hover:bg-slate-50"
            data-testid={`cba-daily-row-${row.date}`}
          >
            <span className="font-mono text-slate-500">{row.date.slice(5)}</span>
            <span
              className="text-right font-mono text-emerald-700"
              data-testid={`cba-daily-inflow-${row.date}`}
            >
              {row.inflows > 0 ? formatPaiseINR(row.inflows, true) : "—"}
            </span>
            <span
              className="text-right font-mono text-rose-600"
              data-testid={`cba-daily-outflow-${row.date}`}
            >
              {row.outflows > 0 ? formatPaiseINR(row.outflows, true) : "—"}
            </span>
            <span
              className={`text-right font-mono font-medium ${
                row.net_movement >= 0 ? "text-emerald-700" : "text-rose-700"
              }`}
              data-testid={`cba-daily-net-${row.date}`}
            >
              {row.net_movement >= 0 ? "+" : ""}
              {formatPaiseINR(row.net_movement, true)}
            </span>
            <span
              className="text-right font-mono text-slate-700"
              data-testid={`cba-daily-balance-${row.date}`}
            >
              {formatPaiseINR(row.ending_balance, true)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function SourceRow({
  label,
  value,
  testId,
}: {
  label: string;
  value: string;
  testId: string;
}) {
  return (
    <div className="flex items-start justify-between gap-4">
      <p className="text-[9px] font-semibold uppercase tracking-wide text-slate-400">{label}</p>
      <p
        className="text-right font-mono text-[10px] text-slate-600"
        data-testid={testId}
      >
        {value}
      </p>
    </div>
  );
}
