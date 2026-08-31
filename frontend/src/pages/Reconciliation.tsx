import type { ReactNode } from "react";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, ArrowRight, CalendarDays, Check, CircleAlert, Clock3, Equal, Filter, Search, ShieldCheck, X } from "lucide-react";

import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { apiGet } from "@/lib/api";
import { formatDate, formatPaiseINR } from "@/lib/format";
import type {
  ReconciliationEngineRecord,
  ReconciliationEngineStatus,
  ReconciliationEngineSummary,
  ReconciliationExceptionPage,
} from "@/lib/types";

const PAGE_SIZE = 25;

function queryString(values: Record<string, string | number>) {
  const params = new URLSearchParams();
  Object.entries(values).forEach(([key, value]) => {
    if (value !== "" && value !== "ALL") params.set(key, String(value));
  });
  const encoded = params.toString();
  return encoded ? `?${encoded}` : "";
}

export default function Reconciliation() {
  const [status, setStatus] = useState("ALL");
  const [method, setMethod] = useState("ALL");
  const [search, setSearch] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [offset, setOffset] = useState(0);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const dateQuery = queryString({ date_from: dateFrom, date_to: dateTo });
  const summaryQuery = useQuery({
    queryKey: ["reconciliation", "summary", dateFrom, dateTo],
    queryFn: () => apiGet<ReconciliationEngineSummary>(`/reconciliation/summary${dateQuery}`),
    retry: false,
  });
  const exceptionQuery = queryString({
    date_from: dateFrom, date_to: dateTo, status, payment_method: method,
    search, limit: PAGE_SIZE, offset,
  });
  const exceptionsQuery = useQuery({
    queryKey: ["reconciliation", "exceptions", dateFrom, dateTo, status, method, search, offset],
    queryFn: () => apiGet<ReconciliationExceptionPage>(`/reconciliation/exceptions${exceptionQuery}`),
    retry: false,
  });
  const detailQuery = useQuery({
    queryKey: ["reconciliation", "detail", selectedId],
    queryFn: () => apiGet<ReconciliationEngineRecord>(`/reconciliation/${selectedId}`),
    enabled: Boolean(selectedId),
    retry: false,
  });

  const summary = summaryQuery.data;
  const exceptions = exceptionsQuery.data;
  const resetFilters = () => {
    setStatus("ALL"); setMethod("ALL"); setSearch(""); setDateFrom(""); setDateTo(""); setOffset(0);
  };
  const updateFilter = (setter: (value: string) => void, value: string) => {
    setter(value); setOffset(0);
  };

  return (
    <div className="space-y-7" data-testid="reconciliation-page">
      <section className="flex flex-col justify-between gap-4 xl:flex-row xl:items-end">
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-rose-600" data-testid="reconciliation-eyebrow">Reconcile</p>
          <h1 className="font-heading text-3xl font-bold tracking-[-0.04em] text-slate-950" data-testid="reconciliation-title">Expected vs actual</h1>
          <p className="mt-2 max-w-2xl text-sm text-slate-500" data-testid="reconciliation-description">Exact-paise settlement checks, calculated deterministically from payments, refunds, fees, and taxes.</p>
        </div>
        <div className="inline-flex items-center gap-2 self-start rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs font-semibold text-emerald-700" data-testid="reconciliation-engine-status"><ShieldCheck size={15} />Deterministic engine · no AI math</div>
      </section>

      {summaryQuery.isError ? <DataError /> : summary ? <>
        <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5" data-testid="reconciliation-summary-cards">
          <SummaryCard label="Total transactions" value={summary.total_transactions.toLocaleString("en-IN")} sub={`${formatDate(summary.date_from)} — ${formatDate(summary.date_to)}`} icon={<Filter size={16} />} testId="reconciliation-total-card" />
          <SummaryCard label="Matched" value={summary.matched_transactions.toLocaleString("en-IN")} sub={`${summary.partially_matched_transactions} partially matched`} icon={<Check size={16} />} testId="reconciliation-matched-card" tone="green" />
          <SummaryCard label="Mismatched" value={summary.mismatched_transactions.toLocaleString("en-IN")} sub="Non-zero net difference" icon={<CircleAlert size={16} />} testId="reconciliation-mismatched-card" tone="red" />
          <SummaryCard label="Pending" value={summary.pending_transactions.toLocaleString("en-IN")} sub={`${summary.unresolved_transactions} unresolved`} icon={<Clock3 size={16} />} testId="reconciliation-pending-card" tone="amber" />
          <SummaryCard label="Total discrepancy" value={formatPaiseINR(summary.total_discrepancy, true)} sub="Absolute difference" icon={<Equal size={16} />} testId="reconciliation-discrepancy-card" tone="red" />
        </section>

        <section className="grid gap-4 lg:grid-cols-[1.15fr_1fr]" data-testid="reconciliation-rate-section">
          <div className="rounded-lg border border-slate-200 bg-white p-5 sm:p-6" data-testid="reconciliation-rate-card">
            <div className="flex items-end justify-between gap-4"><div><p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-400" data-testid="reconciliation-rate-label">Reconciliation rate</p><p className="mt-2 font-mono text-3xl font-medium tracking-tight text-slate-950" data-testid="reconciliation-rate-value">{summary.reconciliation_rate}%</p></div><p className="max-w-48 text-right text-[11px] leading-5 text-slate-500" data-testid="reconciliation-rate-note">Matched and component-level partial matches across the selected period</p></div>
            <div className="mt-5 h-2 overflow-hidden rounded-full bg-slate-100" data-testid="reconciliation-rate-track"><div className="h-full rounded-full bg-emerald-500 transition-[width] duration-500" style={{ width: `${summary.reconciliation_rate}%` }} data-testid="reconciliation-rate-fill" /></div>
          </div>
          <div className="grid grid-cols-2 divide-x divide-slate-100 rounded-lg border border-slate-200 bg-white" data-testid="reconciliation-totals-card">
            <AmountTotal label="Expected settlement" value={summary.total_expected_amount} testId="reconciliation-expected-total" />
            <AmountTotal label="Actual settlement" value={summary.total_actual_amount} testId="reconciliation-actual-total" />
          </div>
        </section>
      </> : <Loading label="Calculating reconciliation summary…" />}

      <section className="rounded-lg border border-slate-200 bg-white" data-testid="reconciliation-exceptions-card">
        <div className="border-b border-slate-100 p-5 sm:p-6">
          <div className="mb-5 flex flex-col justify-between gap-2 sm:flex-row sm:items-end"><div><h2 className="font-heading text-lg font-bold text-slate-900" data-testid="reconciliation-table-title">Exception queue</h2><p className="mt-1 text-xs text-slate-500" data-testid="reconciliation-table-subtitle">Investigate partial matches, mismatches, pending records, and unresolved links.</p></div><p className="font-mono text-xs text-slate-500" data-testid="reconciliation-exception-count">{exceptions ? `${exceptions.total.toLocaleString("en-IN")} exceptions` : "Loading…"}</p></div>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-[1.4fr_0.8fr_0.8fr_0.9fr_0.9fr_auto]" data-testid="reconciliation-filters">
            <label className="relative" data-testid="reconciliation-search-label"><Search size={14} className="pointer-events-none absolute left-3 top-2.5 text-slate-400" /><input value={search} onChange={(event) => updateFilter(setSearch, event.target.value)} placeholder="Payment, order or settlement ID" className="h-9 w-full rounded-md border border-slate-200 bg-white pl-9 pr-3 text-xs outline-none transition-colors focus:border-rose-400 focus:ring-2 focus:ring-rose-100" data-testid="reconciliation-search-input" /></label>
            <select value={status} onChange={(event) => updateFilter(setStatus, event.target.value)} className="h-9 rounded-md border border-slate-200 bg-white px-3 text-xs text-slate-600 outline-none focus:border-rose-400" data-testid="reconciliation-status-filter"><option value="ALL">All statuses</option><option value="PARTIALLY_MATCHED">Partially matched</option><option value="MISMATCHED">Mismatched</option><option value="PENDING">Pending</option><option value="UNRESOLVED">Unresolved</option></select>
            <select value={method} onChange={(event) => updateFilter(setMethod, event.target.value)} className="h-9 rounded-md border border-slate-200 bg-white px-3 text-xs text-slate-600 outline-none focus:border-rose-400" data-testid="reconciliation-method-filter"><option value="ALL">All methods</option><option value="upi">UPI</option><option value="card">Card</option><option value="netbanking">Netbanking</option><option value="wallet">Wallet</option><option value="emi">EMI</option></select>
            <label className="relative" data-testid="reconciliation-date-from-label"><CalendarDays size={13} className="pointer-events-none absolute left-2.5 top-2.5 text-slate-400" /><input type="date" value={dateFrom || summary?.date_from || ""} onChange={(event) => updateFilter(setDateFrom, event.target.value)} className="h-9 w-full rounded-md border border-slate-200 bg-white pl-8 pr-2 text-[11px] text-slate-600 outline-none focus:border-rose-400" data-testid="reconciliation-date-from-input" /></label>
            <label className="relative" data-testid="reconciliation-date-to-label"><CalendarDays size={13} className="pointer-events-none absolute left-2.5 top-2.5 text-slate-400" /><input type="date" value={dateTo || summary?.date_to || ""} onChange={(event) => updateFilter(setDateTo, event.target.value)} className="h-9 w-full rounded-md border border-slate-200 bg-white pl-8 pr-2 text-[11px] text-slate-600 outline-none focus:border-rose-400" data-testid="reconciliation-date-to-input" /></label>
            <button type="button" onClick={resetFilters} className="inline-flex h-9 items-center justify-center gap-1.5 rounded-md border border-slate-200 px-3 text-xs font-semibold text-slate-500 transition-colors hover:bg-slate-50 hover:text-slate-800 active:scale-[0.98]" data-testid="reconciliation-reset-filters"><X size={13} />Reset</button>
          </div>
        </div>

        {exceptionsQuery.isError ? <div className="p-6 text-sm text-amber-700" data-testid="reconciliation-exceptions-error">Unable to load the exception queue.</div> : exceptions ? <>
          <div className="overflow-x-auto"><table className="w-full min-w-[900px] text-left" data-testid="reconciliation-exceptions-table"><thead className="bg-slate-50 text-[10px] uppercase tracking-[0.13em] text-slate-400"><tr><th className="px-5 py-3 font-semibold">Transaction</th><th className="px-5 py-3 font-semibold">Method</th><th className="px-5 py-3 font-semibold">Date</th><th className="px-5 py-3 text-right font-semibold">Expected</th><th className="px-5 py-3 text-right font-semibold">Actual</th><th className="px-5 py-3 text-right font-semibold">Difference</th><th className="px-5 py-3 text-right font-semibold">Status</th></tr></thead><tbody className="divide-y divide-slate-100">{exceptions.items.map((item) => <ExceptionRow key={item.id} item={item} onOpen={() => setSelectedId(item.id)} />)}</tbody></table></div>
          {exceptions.items.length === 0 && <div className="p-10 text-center text-sm text-slate-500" data-testid="reconciliation-empty-state">No exceptions match these filters.</div>}
          <div className="flex items-center justify-between border-t border-slate-100 px-5 py-4" data-testid="reconciliation-pagination"><p className="text-[11px] text-slate-400" data-testid="reconciliation-pagination-range">{exceptions.total ? `${offset + 1}–${Math.min(offset + PAGE_SIZE, exceptions.total)} of ${exceptions.total}` : "0 records"}</p><div className="flex gap-2"><button type="button" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))} className="inline-flex h-8 items-center gap-1 rounded-md border border-slate-200 px-3 text-xs font-semibold text-slate-600 transition-colors hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40" data-testid="reconciliation-previous-page"><ArrowLeft size={13} />Previous</button><button type="button" disabled={offset + PAGE_SIZE >= exceptions.total} onClick={() => setOffset(offset + PAGE_SIZE)} className="inline-flex h-8 items-center gap-1 rounded-md border border-slate-200 px-3 text-xs font-semibold text-slate-600 transition-colors hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40" data-testid="reconciliation-next-page">Next<ArrowRight size={13} /></button></div></div>
        </> : <Loading label="Reconciling settlements…" />}
      </section>

      <Sheet open={Boolean(selectedId)} onOpenChange={(open) => { if (!open) setSelectedId(null); }}>
        <SheetContent side="right" className="w-full overflow-y-auto p-0 sm:max-w-xl" data-testid="reconciliation-detail-panel">
          <SheetHeader className="border-b border-slate-100 p-6 text-left"><SheetTitle className="font-heading text-xl" data-testid="reconciliation-detail-title">Transaction reconciliation</SheetTitle><SheetDescription data-testid="reconciliation-detail-description">Backend-calculated expected vs actual settlement evidence.</SheetDescription></SheetHeader>
          {detailQuery.isLoading ? <Loading label="Loading transaction detail…" /> : detailQuery.data ? <DetailPanel item={detailQuery.data} /> : <div className="p-6 text-sm text-amber-700" data-testid="reconciliation-detail-error">Transaction detail is unavailable.</div>}
        </SheetContent>
      </Sheet>
    </div>
  );
}

const statusStyles: Record<ReconciliationEngineStatus, string> = {
  MATCHED: "bg-emerald-50 text-emerald-700", PARTIALLY_MATCHED: "bg-blue-50 text-blue-700",
  MISMATCHED: "bg-rose-50 text-rose-700", PENDING: "bg-amber-50 text-amber-700",
  UNRESOLVED: "bg-slate-100 text-slate-700",
};

function SummaryCard({ label, value, sub, icon, testId, tone = "slate" }: { label: string; value: string; sub: string; icon: ReactNode; testId: string; tone?: "slate" | "green" | "red" | "amber" }) {
  const colors = { slate: "text-slate-400", green: "text-emerald-500", red: "text-rose-500", amber: "text-amber-500" };
  return <div className="rounded-lg border border-slate-200 bg-white p-4 transition-transform hover:-translate-y-0.5 hover:shadow-sm" data-testid={testId}><div className="flex items-center justify-between"><p className="text-xs text-slate-400" data-testid={`${testId}-label`}>{label}</p><span className={colors[tone]}>{icon}</span></div><p className="mt-4 font-mono text-xl font-medium text-slate-900" data-testid={`${testId}-value`}>{value}</p><p className="mt-1 truncate text-[11px] text-slate-500" data-testid={`${testId}-sub`}>{sub}</p></div>;
}

function AmountTotal({ label, value, testId }: { label: string; value: number; testId: string }) { return <div className="flex flex-col justify-center p-5 sm:p-6" data-testid={testId}><p className="text-xs text-slate-400" data-testid={`${testId}-label`}>{label}</p><p className="mt-3 font-mono text-xl font-medium text-slate-900" data-testid={`${testId}-value`}>{formatPaiseINR(value, true)}</p><p className="mt-1 text-[10px] text-slate-400" data-testid={`${testId}-unit`}>Calculated in integer paise</p></div>; }

function ExceptionRow({ item, onOpen }: { item: ReconciliationEngineRecord; onOpen: () => void }) {
  const date = item.payment_created_at?.slice(0, 10) ?? item.settlement_date;
  return <tr className="transition-colors hover:bg-slate-50" data-testid={`reconciliation-row-${item.id}`}><td className="px-5 py-4"><button type="button" onClick={onOpen} className="text-left transition-colors hover:text-rose-700" data-testid={`reconciliation-open-${item.id}`}><p className="font-mono text-xs font-medium" data-testid={`reconciliation-id-${item.id}`}>{item.payment_id ?? item.settlement_id}</p><p className="mt-1 text-[10px] text-slate-400" data-testid={`reconciliation-link-${item.id}`}>{item.settlement_id ? `Settlement ${item.settlement_id.slice(-8)}` : "No settlement linked"}</p></button></td><td className="px-5 py-4 text-xs capitalize text-slate-600" data-testid={`reconciliation-method-${item.id}`}>{item.payment_method ?? "—"}</td><td className="px-5 py-4 text-xs text-slate-500" data-testid={`reconciliation-date-${item.id}`}>{date ? formatDate(date) : "—"}</td><td className="px-5 py-4 text-right font-mono text-xs text-slate-600" data-testid={`reconciliation-expected-${item.id}`}>{formatPaiseINR(item.expected_settlement)}</td><td className="px-5 py-4 text-right font-mono text-xs text-slate-800" data-testid={`reconciliation-actual-${item.id}`}>{item.actual_settlement === null ? "—" : formatPaiseINR(item.actual_settlement)}</td><td className={`px-5 py-4 text-right font-mono text-xs font-medium ${(item.difference_amount ?? 0) !== 0 ? "text-rose-600" : "text-slate-500"}`} data-testid={`reconciliation-difference-${item.id}`}>{item.difference_amount === null ? "—" : formatPaiseINR(item.difference_amount)}</td><td className="px-5 py-4 text-right"><span className={`inline-flex rounded-full px-2 py-1 text-[9px] font-bold tracking-wide ${statusStyles[item.status]}`} data-testid={`reconciliation-status-${item.id}`}>{item.status.replaceAll("_", " ")}</span></td></tr>;
}

function DetailPanel({ item }: { item: ReconciliationEngineRecord }) {
  return <div className="space-y-6 p-6" data-testid="reconciliation-detail-content"><div className="flex items-center justify-between"><span className={`rounded-full px-2.5 py-1 text-[10px] font-bold ${statusStyles[item.status]}`} data-testid="reconciliation-detail-status">{item.status.replaceAll("_", " ")}</span><span className="font-mono text-[10px] text-slate-400" data-testid="reconciliation-detail-id">{item.id}</span></div><div className="grid grid-cols-2 gap-3" data-testid="reconciliation-detail-comparison"><DetailAmount label="Expected settlement" value={item.expected_settlement} testId="detail-expected-settlement" /><DetailAmount label="Actual settlement" value={item.actual_settlement} testId="detail-actual-settlement" /><DetailAmount label="Difference" value={item.difference_amount} testId="detail-difference" emphasis /><div className="rounded-lg bg-slate-50 p-4" data-testid="detail-difference-percentage"><p className="text-[10px] uppercase tracking-[0.12em] text-slate-400">Difference %</p><p className="mt-2 font-mono text-lg font-medium text-slate-900">{item.difference_percentage === null ? "—" : `${item.difference_percentage.toFixed(4)}%`}</p></div></div><div className="rounded-lg border border-amber-200 bg-amber-50 p-4" data-testid="reconciliation-possible-reason"><p className="text-[10px] font-bold uppercase tracking-[0.13em] text-amber-700">Possible reason</p><p className="mt-2 text-sm leading-6 text-amber-900">{item.possible_reason}</p></div><div data-testid="reconciliation-component-breakdown"><h3 className="font-heading text-sm font-bold text-slate-900" data-testid="component-breakdown-title">Calculation breakdown</h3><div className="mt-3 divide-y divide-slate-100 rounded-lg border border-slate-200">{item.component_comparisons.map((component) => <div key={component.component} className="grid grid-cols-[1fr_0.8fr_0.8fr_auto] items-center gap-2 px-4 py-3 text-xs" data-testid={`component-row-${component.component}`}><span className="capitalize text-slate-600" data-testid={`component-name-${component.component}`}>{component.component.replaceAll("_", " ")}</span><span className="text-right font-mono text-slate-500" data-testid={`component-expected-${component.component}`}>{formatPaiseINR(component.expected_amount)}</span><span className="text-right font-mono text-slate-800" data-testid={`component-actual-${component.component}`}>{component.actual_amount === null ? "—" : formatPaiseINR(component.actual_amount)}</span><span className={component.matches ? "text-emerald-500" : "text-rose-500"} data-testid={`component-result-${component.component}`}>{component.matches ? <Check size={14} /> : <CircleAlert size={14} />}</span></div>)}</div><div className="mt-2 grid grid-cols-[1fr_0.8fr_0.8fr_auto] gap-2 px-4 text-[9px] uppercase tracking-[0.12em] text-slate-400" data-testid="component-table-labels"><span>Component</span><span className="text-right">Expected</span><span className="text-right">Actual</span><span>Check</span></div></div><div className="grid grid-cols-2 gap-x-4 gap-y-4 border-t border-slate-100 pt-5" data-testid="reconciliation-identifiers"><Identifier label="Payment ID" value={item.payment_id} testId="detail-payment-id" /><Identifier label="Settlement ID" value={item.settlement_id} testId="detail-settlement-id" /><Identifier label="Order ID" value={item.order_id} testId="detail-order-id" /><Identifier label="Payment method" value={item.payment_method} testId="detail-payment-method" /></div></div>;
}

function DetailAmount({ label, value, testId, emphasis = false }: { label: string; value: number | null; testId: string; emphasis?: boolean }) { return <div className={`rounded-lg p-4 ${emphasis && value ? "bg-rose-50" : "bg-slate-50"}`} data-testid={testId}><p className="text-[10px] uppercase tracking-[0.12em] text-slate-400" data-testid={`${testId}-label`}>{label}</p><p className={`mt-2 font-mono text-lg font-medium ${emphasis && value ? "text-rose-700" : "text-slate-900"}`} data-testid={`${testId}-value`}>{value === null ? "—" : formatPaiseINR(value)}</p></div>; }
function Identifier({ label, value, testId }: { label: string; value: string | null; testId: string }) { return <div data-testid={testId}><p className="text-[10px] uppercase tracking-[0.12em] text-slate-400" data-testid={`${testId}-label`}>{label}</p><p className="mt-1 break-all font-mono text-[11px] text-slate-700" data-testid={`${testId}-value`}>{value ?? "—"}</p></div>; }
function Loading({ label }: { label: string }) { return <div className="p-8 text-sm text-slate-500" data-testid="reconciliation-loading">{label}</div>; }
function DataError() { return <div className="rounded-lg border border-amber-200 bg-amber-50 p-6 text-sm text-amber-800" data-testid="reconciliation-data-error">The deterministic reconciliation service is unavailable. The dashboard shell remains available.</div>; }