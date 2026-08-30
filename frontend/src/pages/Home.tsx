import type { ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, CheckCircle2, CircleAlert, Clock3, TrendingUp } from "lucide-react";

import { apiGet } from "@/lib/api";
import { formatINR } from "@/lib/format";
import type { DashboardResponse } from "@/lib/types";

export default function Home() {
  const dashboard = useQuery({ queryKey: ["dashboard"], queryFn: () => apiGet<DashboardResponse>("/dashboard"), retry: false });
  const data = dashboard.data;

  return (
    <div className="space-y-7" data-testid="overview-page">
      <section className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-rose-600" data-testid="overview-eyebrow">Financial intelligence</p>
          <h1 className="font-heading text-3xl font-bold tracking-[-0.04em] text-slate-950 sm:text-4xl" data-testid="overview-title">Good morning, Aarav</h1>
          <p className="mt-2 max-w-xl text-sm text-slate-500" data-testid="overview-subtitle">A clear view of what moved, what is next, and where to focus today.</p>
        </div>
        <div className="text-left sm:text-right"><p className="text-xs text-slate-400" data-testid="overview-data-label">Data as of</p><p className="font-mono text-xs font-medium text-slate-700" data-testid="overview-data-date">{data?.summary.data_as_of ?? "Loading ledger…"}</p></div>
      </section>

      {dashboard.isError ? <DataUnavailable /> : data ? <>
        <section className="grid gap-4 md:grid-cols-3" data-testid="overview-primary-cards">
          <MetricCard label="Cash position" value={formatINR(data.summary.cash_balance)} detail={`${data.summary.cash_delta_percent >= 0 ? "+" : ""}${data.summary.cash_delta_percent}% next 6 weeks`} icon={<TrendingUp size={17} />} accent="rose" testId="cash-position-card" />
          <MetricCard label="Runway" value={`${data.summary.runway_weeks} weeks`} detail="At current operating burn" icon={<Clock3 size={17} />} accent="slate" testId="runway-card" />
          <MetricCard label="Reconciled" value={`${data.summary.reconciliation_rate}%`} detail={`${data.summary.open_exceptions} items need review`} icon={<CheckCircle2 size={17} />} accent="emerald" testId="reconciled-card" />
        </section>

        <section className="grid gap-5 xl:grid-cols-[1.45fr_1fr]" data-testid="overview-insight-grid">
          <div className="rounded-lg border border-slate-200 bg-white" data-testid="overview-flow-card">
            <div className="flex items-start justify-between border-b border-slate-100 p-5 sm:p-6"><div><p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400" data-testid="flow-card-eyebrow">Reconcile → Predict → Decide</p><h2 className="mt-2 font-heading text-xl font-bold tracking-tight text-slate-900" data-testid="flow-card-title">Your money, explained</h2></div><span className="rounded-full bg-emerald-50 px-2.5 py-1 text-[11px] font-semibold text-emerald-700" data-testid="flow-card-status">On track</span></div>
            <div className="grid divide-y divide-slate-100 sm:grid-cols-3 sm:divide-x sm:divide-y-0"><FlowStep number="01" title="Reconcile" description={`${data.reconciliation.matched_count} of ${data.reconciliation.total_transactions} transactions matched`} href="/reconciliation" testId="flow-step-reconcile" /><FlowStep number="02" title="Predict" description={`${data.forecast.horizon_weeks}-week cash outlook`} href="/forecast" testId="flow-step-predict" /><FlowStep number="03" title="Decide" description={`${data.insights.length} actions to consider`} href="/cfo" testId="flow-step-decide" /></div>
          </div>
          <div className="rounded-lg border border-rose-100 bg-rose-50/60 p-5 sm:p-6" data-testid="overview-cfo-card"><div className="mb-5 flex items-center justify-between"><div><p className="text-xs font-semibold uppercase tracking-[0.16em] text-rose-600" data-testid="cfo-card-eyebrow">AI CFO brief</p><h2 className="mt-2 font-heading text-xl font-bold tracking-tight text-slate-900" data-testid="cfo-card-title">Focus for today</h2></div><div className="flex h-9 w-9 items-center justify-center rounded-md bg-white text-rose-600 shadow-sm"><CircleAlert size={18} /></div></div><p className="text-sm leading-6 text-slate-600" data-testid="cfo-card-body">{data.insights[0]?.body}</p><a href="/cfo" className="mt-5 inline-flex items-center gap-2 text-xs font-bold text-rose-700 transition-transform hover:translate-x-0.5" data-testid="cfo-card-link">See CFO recommendations <ArrowRight size={14} /></a></div>
        </section>
      </> : <LoadingPanel />}
    </div>
  );
}

function MetricCard({ label, value, detail, icon, accent, testId }: { label: string; value: string; detail: string; icon: ReactNode; accent: "rose" | "slate" | "emerald"; testId: string }) {
  const colors = { rose: "bg-rose-50 text-rose-600", slate: "bg-slate-100 text-slate-500", emerald: "bg-emerald-50 text-emerald-600" };
  return <div className="rounded-lg border border-slate-200 bg-white p-5 transition-transform hover:-translate-y-0.5 hover:shadow-md" data-testid={testId}><div className="flex items-center justify-between"><p className="text-xs font-medium text-slate-400" data-testid={`${testId}-label`}>{label}</p><span className={`flex h-8 w-8 items-center justify-center rounded-md ${colors[accent]}`}>{icon}</span></div><p className="mt-5 font-mono text-2xl font-medium tracking-tight text-slate-950" data-testid={`${testId}-value`}>{value}</p><p className="mt-2 text-xs text-slate-500" data-testid={`${testId}-detail`}>{detail}</p></div>;
}

function FlowStep({ number, title, description, href, testId }: { number: string; title: string; description: string; href: string; testId: string }) {
  return <a href={href} className="group p-5 transition-colors hover:bg-slate-50 sm:p-6" data-testid={testId}><div className="mb-8 flex items-center justify-between"><span className="font-mono text-xs text-slate-300" data-testid={`${testId}-number`}>{number}</span><ArrowRight size={15} className="text-slate-300 transition-transform group-hover:translate-x-1 group-hover:text-rose-600" /></div><h3 className="font-heading text-sm font-bold text-slate-900" data-testid={`${testId}-title`}>{title}</h3><p className="mt-2 text-xs leading-5 text-slate-500" data-testid={`${testId}-description`}>{description}</p></a>;
}

function LoadingPanel() { return <div className="rounded-lg border border-slate-200 bg-white p-8 text-sm text-slate-500" data-testid="overview-loading">Loading synthetic ledger…</div>; }
function DataUnavailable() { return <div className="rounded-lg border border-amber-200 bg-amber-50 p-6" data-testid="overview-data-unavailable"><p className="font-heading font-bold text-amber-900" data-testid="overview-data-unavailable-title">Preview mode</p><p className="mt-1 text-sm text-amber-800" data-testid="overview-data-unavailable-copy">The shell is ready. Connect the backend to load financial metrics.</p></div>; }
