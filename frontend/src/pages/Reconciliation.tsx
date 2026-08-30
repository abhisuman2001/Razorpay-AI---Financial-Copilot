import type { ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { Check, CircleAlert, Clock3, Filter } from "lucide-react";

import { apiGet } from "@/lib/api";
import { formatINR, formatDate } from "@/lib/format";
import type { ReconciliationResponse } from "@/lib/types";

export default function Reconciliation() {
  const query = useQuery({ queryKey: ["reconciliation"], queryFn: () => apiGet<ReconciliationResponse>("/dashboard/reconciliation"), retry: false });
  const data = query.data;
  return <div className="space-y-7" data-testid="reconciliation-page">
    <PageHeading eyebrow="Reconcile" title="Every rupee accounted for" description="Deterministic matching across settlements, operating outflows, and expected ledger values." />
    {query.isError ? <DataError /> : data ? <>
      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4" data-testid="reconciliation-summary-cards">
        <Summary label="Match rate" value={`${data.summary.match_rate}%`} sub={`${data.summary.matched_count} matched`} icon={<Check size={16} />} testId="reconciliation-match-card" />
        <Summary label="Total volume" value={formatINR(data.summary.total_volume, true)} sub={data.summary.period_label} icon={<Filter size={16} />} testId="reconciliation-volume-card" />
        <Summary label="Exceptions" value={String(data.summary.exception_count)} sub={`${formatINR(data.summary.exception_value)} variance`} icon={<CircleAlert size={16} />} testId="reconciliation-exception-card" />
        <Summary label="Pending" value={String(data.summary.pending_count)} sub="Awaiting settlement proof" icon={<Clock3 size={16} />} testId="reconciliation-pending-card" />
      </section>
      <section className="rounded-lg border border-slate-200 bg-white" data-testid="reconciliation-table-card">
        <div className="flex flex-col justify-between gap-3 border-b border-slate-100 p-5 sm:flex-row sm:items-center sm:p-6"><div><h2 className="font-heading text-lg font-bold text-slate-900" data-testid="reconciliation-table-title">Transaction queue</h2><p className="mt-1 text-xs text-slate-500" data-testid="reconciliation-table-subtitle">Synthetic ledger · {data.items.length} records</p></div><span className="rounded-md bg-slate-100 px-2.5 py-1.5 text-xs font-semibold text-slate-600" data-testid="reconciliation-period-label">{data.summary.period_label}</span></div>
        <div className="overflow-x-auto"><table className="w-full min-w-[720px] text-left" data-testid="reconciliation-table"><thead className="bg-slate-50 text-[10px] uppercase tracking-[0.13em] text-slate-400"><tr><th className="px-5 py-3 font-semibold">Transaction</th><th className="px-5 py-3 font-semibold">Category</th><th className="px-5 py-3 font-semibold">Date</th><th className="px-5 py-3 text-right font-semibold">Expected</th><th className="px-5 py-3 text-right font-semibold">Actual</th><th className="px-5 py-3 text-right font-semibold">Status</th></tr></thead><tbody className="divide-y divide-slate-100">{data.items.map((item) => <TransactionRow key={item.id} item={item} />)}</tbody></table></div>
      </section>
    </> : <Loading />}
  </div>;
}

function TransactionRow({ item }: { item: ReconciliationResponse["items"][number] }) { const status = { matched: { label: "Matched", className: "bg-emerald-50 text-emerald-700", icon: <Check size={12} /> }, exception: { label: "Exception", className: "bg-rose-50 text-rose-700", icon: <CircleAlert size={12} /> }, pending: { label: "Pending", className: "bg-amber-50 text-amber-700", icon: <Clock3 size={12} /> } }[item.status]; return <tr className="transition-colors hover:bg-slate-50" data-testid={`transaction-row-${item.id}`}><td className="px-5 py-4"><p className="font-mono text-xs font-medium text-slate-800" data-testid={`transaction-reference-${item.id}`}>{item.reference}</p><p className="mt-1 text-[11px] text-slate-400">Ledger record</p></td><td className="px-5 py-4 text-xs text-slate-600">{item.category}</td><td className="px-5 py-4 text-xs text-slate-500">{formatDate(item.date)}</td><td className="px-5 py-4 text-right font-mono text-xs text-slate-500">{formatINR(item.expected_amount)}</td><td className="px-5 py-4 text-right font-mono text-xs font-medium text-slate-800">{formatINR(item.actual_amount)}</td><td className="px-5 py-4 text-right"><span className={`inline-flex items-center gap-1 rounded-full px-2 py-1 text-[10px] font-bold ${status.className}`} data-testid={`transaction-status-${item.id}`}>{status.icon}{status.label}</span></td></tr>; }

function PageHeading({ eyebrow, title, description }: { eyebrow: string; title: string; description: string }) { return <section><p className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-rose-600" data-testid="page-eyebrow">{eyebrow}</p><h1 className="font-heading text-3xl font-bold tracking-[-0.04em] text-slate-950" data-testid="page-title">{title}</h1><p className="mt-2 max-w-2xl text-sm text-slate-500" data-testid="page-description">{description}</p></section>; }
function Summary({ label, value, sub, icon, testId }: { label: string; value: string; sub: string; icon: ReactNode; testId: string }) { return <div className="rounded-lg border border-slate-200 bg-white p-4" data-testid={testId}><div className="flex items-center justify-between"><p className="text-xs text-slate-400" data-testid={`${testId}-label`}>{label}</p><span className="text-slate-400">{icon}</span></div><p className="mt-4 font-mono text-xl font-medium text-slate-900" data-testid={`${testId}-value`}>{value}</p><p className="mt-1 text-[11px] text-slate-500" data-testid={`${testId}-sub`}>{sub}</p></div>; }
function Loading() { return <div className="rounded-lg border border-slate-200 bg-white p-8 text-sm text-slate-500" data-testid="reconciliation-loading">Loading reconciliation queue…</div>; }
function DataError() { return <div className="rounded-lg border border-amber-200 bg-amber-50 p-6 text-sm text-amber-800" data-testid="reconciliation-data-error">The reconciliation service is unavailable. The static workspace remains available.</div>; }