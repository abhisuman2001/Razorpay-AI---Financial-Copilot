import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowDownRight, ArrowRight, ArrowUpRight, Bot, CircleMinus, Database, Info, Sparkles } from "lucide-react";
import { Link } from "react-router-dom";

import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import CashBalanceAnalysisSheet from "@/components/CashBalanceAnalysisSheet";
import { apiGet } from "@/lib/api";
import { formatDate, formatPaiseINR } from "@/lib/format";
import type { MetricEvidence, WhyMetricId, WhyMetricResponse } from "@/lib/types";

interface WhyMetricSheetProps {
  metricId: WhyMetricId | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  evidence?: MetricEvidence[];
}

function formatValue(value: number, unit: WhyMetricResponse["unit"]) {
  if (unit === "currency") return formatPaiseINR(value);
  if (unit === "percent") return `${value.toFixed(2)}%`;
  return value.toLocaleString("en-IN");
}

export default function WhyMetricSheet({ metricId, open, onOpenChange, evidence = [] }: WhyMetricSheetProps) {
  const [analysisOpen, setAnalysisOpen] = useState(false);

  function handleAnalysisOpen() {
    // Close the Why? sheet first, then open the analysis sheet in the next tick
    // so the two Sheet portals don't fight over the overlay.
    onOpenChange(false);
    setTimeout(() => setAnalysisOpen(true), 120);
  }

  const query = useQuery({
    queryKey: ["why", metricId],
    queryFn: () => apiGet<WhyMetricResponse>(`/why/${metricId}`),
    enabled: open && Boolean(metricId), retry: false,
  });
  const data = query.data;
  return (
    <>
      <Sheet open={open} onOpenChange={onOpenChange}><SheetContent side="right" className="w-full overflow-y-auto p-0 sm:max-w-xl" data-testid="why-metric-panel"><SheetHeader className="border-b border-slate-100 p-6 text-left"><p className="text-[10px] font-bold uppercase tracking-[0.14em] text-rose-600" data-testid="why-panel-eyebrow">Why?</p><SheetTitle className="font-heading text-xl" data-testid="why-panel-title">{data?.metric_label ?? "Analyzing financial drivers"}</SheetTitle><SheetDescription data-testid="why-panel-period">{data ? `${data.current_period} · compared with ${data.comparison_period}` : "Calculating deterministic contributors…"}</SheetDescription></SheetHeader>{query.isError ? <div className="p-6 text-sm text-amber-700" data-testid="why-panel-error">The explanation could not be generated from the available data.</div> : data ? <div className="space-y-6 p-6" data-testid="why-panel-content"><div className="grid grid-cols-2 gap-3" data-testid="why-value-comparison"><ValueBlock label="Current" value={formatValue(data.current_value, data.unit)} testId="why-current-value" /><ValueBlock label="Previous" value={formatValue(data.previous_value, data.unit)} testId="why-previous-value" /><div className="col-span-2 flex items-center justify-between rounded-lg bg-slate-950 p-4 text-white" data-testid="why-change-summary"><div><p className="text-[9px] uppercase tracking-[0.13em] text-slate-400">Observed change</p><p className="mt-1 font-mono text-xl font-medium">{data.change_summary}</p></div><span className={`flex h-9 w-9 items-center justify-center rounded-md ${data.direction === "increased" ? "bg-emerald-500/15 text-emerald-300" : data.direction === "decreased" ? "bg-rose-500/15 text-rose-300" : "bg-slate-700 text-slate-300"}`}>{data.direction === "increased" ? <ArrowUpRight size={17} /> : data.direction === "decreased" ? <ArrowDownRight size={17} /> : <CircleMinus size={17} />}</span></div></div><div className="rounded-lg border border-rose-100 bg-rose-50/60 p-5" data-testid="why-ai-explanation"><div className="flex items-center justify-between"><p className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.13em] text-rose-700"><Bot size={13} />AI CFO explanation</p><span className="rounded-full bg-white px-2 py-1 text-[8px] font-bold text-slate-500" data-testid="why-explanation-mode">{data.explanation_mode}</span></div><p className="mt-3 text-sm leading-7 text-slate-700" data-testid="why-explanation-text">{data.explanation}</p><p className="mt-3 flex items-center gap-1.5 text-[9px] font-semibold uppercase tracking-wide text-slate-400" data-testid="why-explanation-classification"><Sparkles size={11} />{data.classification === "prediction" ? "Prediction — not a recorded fact" : "Recorded financial facts"}</p></div><div data-testid="why-drivers-section"><div className="flex items-end justify-between"><div><p className="text-[10px] font-bold uppercase tracking-[0.14em] text-slate-400">Top contributors</p><h3 className="mt-1 font-heading text-sm font-bold text-slate-900">Ranked by material movement</h3></div><span className="text-[9px] text-slate-400">Top {data.drivers.length}</span></div><div className="mt-3 space-y-2">{data.drivers.map((driver, index) => <article key={driver.id} className="rounded-lg border border-slate-200 p-4" data-testid={`why-driver-${driver.id}`}><div className="flex items-start justify-between gap-3"><div className="flex min-w-0 items-start gap-3"><span className="flex h-6 w-6 shrink-0 items-center justify-center rounded bg-slate-100 font-mono text-[9px] text-slate-500">0{index + 1}</span><div><p className="text-xs font-bold text-slate-800" data-testid={`why-driver-${driver.id}-label`}>{driver.label}</p><p className="mt-1 text-[10px] leading-4 text-slate-500" data-testid={`why-driver-${driver.id}-description`}>{driver.description}</p></div></div><span className={`shrink-0 rounded-full px-2 py-1 text-[8px] font-bold uppercase ${driver.effect === "negative" ? "bg-rose-50 text-rose-700" : driver.effect === "positive" ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-600"}`} data-testid={`why-driver-${driver.id}-effect`}>{driver.effect}</span></div><div className="mt-3 grid grid-cols-3 gap-2 border-t border-slate-100 pt-3"><DriverValue label="Current" value={formatValue(driver.current_value, driver.unit)} /><DriverValue label="Previous" value={formatValue(driver.previous_value, driver.unit)} /><DriverValue label="Change" value={`${driver.direction} ${driver.change_summary}`} emphasize /></div><div className="mt-3 flex flex-wrap gap-1">{driver.source_metrics.map((source) => <span key={source} className="rounded bg-slate-50 px-2 py-1 font-mono text-[8px] text-slate-400">{source}</span>)}</div></article>)}</div></div>{evidence.length > 0 && <div data-testid="why-underlying-evidence"><p className="text-[10px] font-bold uppercase tracking-[0.14em] text-slate-400">Underlying records</p><div className="mt-3 divide-y divide-slate-100 rounded-lg border border-slate-200">{evidence.map((item) => <div key={item.id} className="grid grid-cols-[1fr_auto] gap-3 p-3" data-testid={`why-evidence-${item.id}`}><div className="min-w-0"><p className="truncate font-mono text-[9px] text-slate-700">{item.id}</p><p className="mt-1 truncate text-[9px] text-slate-400">{item.type} · {item.label} · {formatDate(item.date)}</p></div><div className="text-right"><p className="font-mono text-[10px] text-slate-700">{formatPaiseINR(item.amount)}</p><p className="mt-1 text-[8px] uppercase text-slate-400">{item.status.replaceAll("_", " ")}</p></div></div>)}</div></div>}<div className="rounded-lg border border-slate-200 bg-slate-50 p-4" data-testid="why-methodology"><p className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-[0.13em] text-slate-500"><Info size={12} />Methodology</p><p className="mt-2 text-[10px] leading-5 text-slate-500">{data.methodology}</p><div className="mt-3 flex flex-wrap gap-1.5">{data.source_refs.map((source) => <span key={source} className="inline-flex items-center gap-1 rounded bg-white px-2 py-1 font-mono text-[8px] text-slate-500"><Database size={9} />{source}</span>)}</div></div>{metricId === "cash_balance" ? (
          <button
            type="button"
            onClick={handleAnalysisOpen}
            className="inline-flex w-full items-center justify-center gap-2 rounded-md bg-rose-600 px-4 py-3 text-xs font-bold text-white transition-colors hover:bg-rose-700"
            data-testid="why-drilldown-button"
          >
            View underlying analysis <ArrowRight size={14} />
          </button>
        ) : (
          <Link to={data.drilldown_path} className="inline-flex w-full items-center justify-center gap-2 rounded-md bg-rose-600 px-4 py-3 text-xs font-bold text-white transition-colors hover:bg-rose-700" data-testid="why-drilldown-link">View underlying analysis <ArrowRight size={14} /></Link>
        )}</div> : <div className="flex items-center gap-3 p-8 text-sm text-slate-500" data-testid="why-panel-loading"><span className="h-2 w-2 animate-pulse rounded-full bg-rose-500" />Calculating top drivers from backend data…</div>}</SheetContent>
      </Sheet>
      <CashBalanceAnalysisSheet open={analysisOpen} onOpenChange={setAnalysisOpen} />
    </>
  );
}

function ValueBlock({ label, value, testId }: { label: string; value: string; testId: string }) { return <div className="rounded-lg bg-slate-50 p-4" data-testid={testId}><p className="text-[9px] uppercase tracking-[0.12em] text-slate-400">{label}</p><p className="mt-2 font-mono text-lg font-medium text-slate-900">{value}</p></div>; }
function DriverValue({ label, value, emphasize = false }: { label: string; value: string; emphasize?: boolean }) { return <div><p className="text-[8px] uppercase tracking-[0.1em] text-slate-400">{label}</p><p className={`mt-1 font-mono text-[9px] ${emphasize ? "font-bold text-slate-800" : "text-slate-600"}`}>{value}</p></div>; }