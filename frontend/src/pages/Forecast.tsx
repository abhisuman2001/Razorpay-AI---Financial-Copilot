import type { ReactNode } from "react";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Area, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ArrowDownLeft, ArrowUpRight, Banknote, CircleAlert, HelpCircle, Info, ShieldCheck, TrendingUp } from "lucide-react";

import WhyMetricSheet from "@/components/WhyMetricSheet";
import { apiGet } from "@/lib/api";
import { formatDate, formatPaiseINR } from "@/lib/format";
import type { CashFlowForecastResponse, ForecastRisk, WhyMetricId } from "@/lib/types";

type Horizon = 7 | 30 | 90;

interface ChartPoint {
  date: string;
  actual_balance: number | null;
  predicted_balance: number | null;
  balance_lower: number | null;
  balance_upper: number | null;
}

export default function Forecast() {
  const [horizon, setHorizon] = useState<Horizon>(30);
  const [whyMetric, setWhyMetric] = useState<WhyMetricId | null>(null);
  const query = useQuery({
    queryKey: ["forecast", horizon],
    queryFn: () => apiGet<CashFlowForecastResponse>(`/forecast/${horizon}`),
    retry: false,
  });
  const data = query.data;
  const chartData: ChartPoint[] = data ? [
    ...data.historical.map((point) => ({
      date: point.date, actual_balance: point.cumulative_cash_balance,
      predicted_balance: null, balance_lower: null, balance_upper: null,
    })),
    ...data.forecast.map((point) => ({
      date: point.date, actual_balance: null, predicted_balance: point.predicted_balance,
      balance_lower: point.balance_lower, balance_upper: point.balance_upper,
    })),
  ] : [];

  return (
    <div className="space-y-7" data-testid="forecast-page">
      <section className="flex flex-col justify-between gap-5 xl:flex-row xl:items-end">
        <div><p className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-rose-600" data-testid="forecast-eyebrow">Predict</p><h1 className="font-heading text-3xl font-bold tracking-[-0.04em] text-slate-950" data-testid="forecast-title">Cash-flow forecast</h1><p className="mt-2 max-w-2xl text-sm text-slate-500" data-testid="forecast-description">Settled income and booked expenses, modeled daily without an LLM.</p></div>
        <div className="flex rounded-md border border-slate-200 bg-white p-1" data-testid="forecast-horizon-selector">{([7, 30, 90] as Horizon[]).map((days) => <button key={days} type="button" onClick={() => setHorizon(days)} className={`rounded px-4 py-2 text-xs font-bold transition-colors active:scale-[0.98] ${horizon === days ? "bg-rose-600 text-white shadow-sm" : "text-slate-500 hover:bg-slate-50 hover:text-slate-800"}`} data-testid={`forecast-horizon-${days}-button`}>{days} days</button>)}</div>
      </section>

      {query.isError ? <div className="rounded-lg border border-amber-200 bg-amber-50 p-6 text-sm text-amber-800" data-testid="forecast-data-error">The statistical forecast service is unavailable. The dashboard shell remains available.</div> : data ? <>
        <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" data-testid="forecast-summary-cards">
          <ForecastMetric label="Current cash balance" value={formatPaiseINR(data.current_cash_balance, true)} detail={`As of ${formatDate(data.as_of_date)}`} icon={<Banknote size={16} />} testId="forecast-current-card" onExplain={() => setWhyMetric("cash_balance")} />
          <ForecastMetric label="Expected incoming" value={formatPaiseINR(data.expected_incoming, true)} detail={`Next ${data.horizon_days} days`} icon={<ArrowDownLeft size={16} />} testId="forecast-incoming-card" tone="green" />
          <ForecastMetric label="Expected outgoing" value={formatPaiseINR(data.expected_outgoing, true)} detail={`Next ${data.horizon_days} days`} icon={<ArrowUpRight size={16} />} testId="forecast-outgoing-card" tone="amber" />
          <ForecastMetric label="Forecasted balance" value={formatPaiseINR(data.forecasted_balance, true)} detail={`End of ${data.horizon_days}-day horizon`} icon={<TrendingUp size={16} />} testId="forecast-ending-card" tone="red" onExplain={() => setWhyMetric("forecasted_balance")} />
        </section>

        <section className="rounded-lg border border-slate-200 bg-white" data-testid="forecast-chart-card">
          <div className="flex flex-col justify-between gap-4 border-b border-slate-100 p-5 sm:flex-row sm:items-center sm:p-6"><div><h2 className="font-heading text-lg font-bold text-slate-900" data-testid="forecast-chart-title">Actual vs predicted cash balance</h2><p className="mt-1 text-xs text-slate-500" data-testid="forecast-chart-subtitle">90 days of actual history followed by the selected forecast horizon</p></div><div className="flex flex-wrap items-center gap-4 text-[11px] text-slate-500"><Legend color="bg-slate-500" label="Actual" testId="forecast-legend-actual" /><Legend color="bg-rose-600" label="Predicted" testId="forecast-legend-predicted" /><Legend color="bg-rose-200" label="80% range" testId="forecast-legend-range" /></div></div>
          <div className="h-[360px] w-full p-3 sm:p-6" data-testid="forecast-chart"><ResponsiveContainer width="100%" height="100%"><ComposedChart data={chartData} margin={{ top: 12, right: 8, left: 8, bottom: 0 }}><defs><linearGradient id="upperBand" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#fda4af" stopOpacity={0.4} /><stop offset="100%" stopColor="#fda4af" stopOpacity={0.08} /></linearGradient></defs><CartesianGrid stroke="#526072" strokeOpacity={0.24} vertical={false} /><XAxis dataKey="date" tickFormatter={(value: string) => value.slice(5)} minTickGap={28} tick={{ fontSize: 10, fill: "#94a3b8" }} axisLine={false} tickLine={false} /><YAxis tickFormatter={(value: number) => formatPaiseINR(value, true)} tick={{ fontSize: 10, fill: "#94a3b8" }} axisLine={false} tickLine={false} width={64} /><Tooltip content={<CashFlowTooltip />} /><Area type="monotone" dataKey="balance_upper" stroke="none" fill="url(#upperBand)" connectNulls={false} /><Area type="monotone" dataKey="balance_lower" stroke="#fecdd3" fill="var(--chart-surface)" fillOpacity={0.92} connectNulls={false} /><Line type="monotone" dataKey="actual_balance" stroke="#64748b" strokeWidth={2} dot={false} connectNulls={false} /><Line type="monotone" dataKey="predicted_balance" stroke="#e11d48" strokeWidth={2.5} dot={false} connectNulls={false} /></ComposedChart></ResponsiveContainer></div>
          <div className="flex flex-col gap-3 border-t border-slate-100 px-5 py-4 text-[11px] leading-5 text-slate-500 sm:flex-row sm:items-start sm:justify-between sm:px-6"><span className="flex max-w-3xl items-start gap-2" data-testid="forecast-method-note"><Info size={14} className="mt-0.5 shrink-0 text-slate-400" />{data.methodology}</span><span className="inline-flex shrink-0 items-center gap-1.5 font-semibold text-slate-600" data-testid="forecast-confidence"><ShieldCheck size={14} className="text-emerald-500" />{data.confidence_label}</span></div>
        </section>

        <section data-testid="forecast-risks-section"><div className="mb-4 flex items-end justify-between"><div><p className="text-xs font-semibold uppercase tracking-[0.16em] text-rose-600" data-testid="forecast-risks-eyebrow">Watchlist</p><h2 className="mt-2 font-heading text-xl font-bold tracking-tight text-slate-900" data-testid="forecast-risks-title">Important forecast risks</h2></div><p className="hidden text-xs text-slate-400 sm:block" data-testid="forecast-risks-source">Deterministic backend rules</p></div><div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4" data-testid="forecast-risks-grid">{data.risks.map((risk) => <RiskCard key={risk.id} risk={risk} />)}</div></section>
      </> : <div className="rounded-lg border border-slate-200 bg-white p-8 text-sm text-slate-500" data-testid="forecast-loading">Fitting daily income and expense models…</div>}
      <WhyMetricSheet metricId={whyMetric} open={Boolean(whyMetric)} onOpenChange={(open) => { if (!open) setWhyMetric(null); }} />
    </div>
  );
}

function ForecastMetric({ label, value, detail, icon, testId, tone = "slate", onExplain }: { label: string; value: string; detail: string; icon: ReactNode; testId: string; tone?: "slate" | "green" | "amber" | "red"; onExplain?: () => void }) { const tones = { slate: "text-slate-500", green: "text-emerald-500", amber: "text-amber-500", red: "text-rose-600" }; return <div className="rounded-lg border border-slate-200 bg-white p-4 transition-transform hover:-translate-y-0.5 hover:shadow-sm" data-testid={testId}><div className="flex items-center justify-between"><p className="text-xs text-slate-400" data-testid={`${testId}-label`}>{label}</p><span className={tones[tone]}>{icon}</span></div><p className="mt-4 font-mono text-xl font-medium text-slate-900" data-testid={`${testId}-value`}>{value}</p><div className="mt-1 flex items-center justify-between gap-2"><p className="text-[11px] text-slate-500" data-testid={`${testId}-detail`}>{detail}</p>{onExplain && <button type="button" onClick={onExplain} className="inline-flex items-center gap-1 text-[9px] font-bold text-rose-700" data-testid={`${testId}-why-button`}><HelpCircle size={11} />Why?</button>}</div></div>; }
function Legend({ color, label, testId }: { color: string; label: string; testId: string }) { return <span className="flex items-center gap-1.5" data-testid={testId}><span className={`h-2 w-2 rounded-full ${color}`} />{label}</span>; }
function RiskCard({ risk }: { risk: ForecastRisk }) { const style = { high: "bg-rose-50 text-rose-700", medium: "bg-amber-50 text-amber-700", low: "bg-emerald-50 text-emerald-700" }[risk.severity]; return <article className="rounded-lg border border-slate-200 bg-white p-5 transition-transform hover:-translate-y-0.5 hover:shadow-sm" data-testid={`forecast-risk-${risk.id}`}><div className="flex items-center justify-between"><span className={`rounded-full px-2 py-1 text-[9px] font-bold uppercase tracking-wide ${style}`} data-testid={`forecast-risk-severity-${risk.id}`}>{risk.severity}</span><CircleAlert size={14} className="text-slate-300" /></div><p className="mt-4 text-[10px] font-bold uppercase tracking-[0.13em] text-slate-400" data-testid={`forecast-risk-category-${risk.id}`}>{risk.category}</p><h3 className="mt-2 font-heading text-sm font-bold leading-5 text-slate-900" data-testid={`forecast-risk-title-${risk.id}`}>{risk.title}</h3><p className="mt-2 text-xs leading-5 text-slate-500" data-testid={`forecast-risk-description-${risk.id}`}>{risk.description}</p><div className="mt-5 border-t border-slate-100 pt-4"><p className="text-[10px] text-slate-400" data-testid={`forecast-risk-metric-label-${risk.id}`}>{risk.metric_label}</p><p className="mt-1 font-mono text-base font-medium text-slate-900" data-testid={`forecast-risk-metric-value-${risk.id}`}>{risk.metric_value}</p><p className="mt-2 text-[9px] text-slate-400" data-testid={`forecast-risk-source-${risk.id}`}>{risk.source}</p></div></article>; }
function CashFlowTooltip({ active, payload, label }: { active?: boolean; payload?: Array<{ value?: number; dataKey?: string }>; label?: string }) { if (!active || !payload?.length) return null; const labels: Record<string, string> = { actual_balance: "Actual balance", predicted_balance: "Predicted balance", balance_lower: "Lower bound", balance_upper: "Upper bound" }; return <div className="rounded-md border border-slate-200 bg-white px-3 py-2 text-xs shadow-lg" data-testid="forecast-tooltip"><p className="mb-1.5 text-slate-400" data-testid="forecast-tooltip-date">{label}</p>{payload.map((entry) => <p key={entry.dataKey} className="font-mono font-medium text-slate-800" data-testid={`forecast-tooltip-${entry.dataKey}`}>{labels[entry.dataKey ?? ""]}: {formatPaiseINR(entry.value ?? 0)}</p>)}</div>; }