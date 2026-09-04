import type { FormEvent, ReactNode } from "react";
import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ArrowRight, Bot, CheckCircle2, CircleAlert, Clock3, Database, Eraser, HelpCircle, RotateCcw, Send, ShieldCheck, Sparkles, UserRound } from "lucide-react";
import { Link } from "react-router-dom";

import WhyMetricSheet from "@/components/WhyMetricSheet";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { apiGet, apiPost } from "@/lib/api";
import type { CfoChatRequest, CfoChatResponse, DailyInsight, DailyInsightsResponse, WhyMetricId, WhyMetricResponse } from "@/lib/types";

const prompts = [
  "What should I be concerned about today?",
  "Why did revenue fall this month?",
  "Will I have enough cash next month?",
  "Which customers are most valuable?",
  "Show me my biggest reconciliation problems.",
];

interface ConversationItem {
  id: string;
  question: string;
  response?: CfoChatResponse;
}

export default function Cfo() {
  const [question, setQuestion] = useState("");
  const [conversation, setConversation] = useState<ConversationItem[]>([]);
  const [whyMetric, setWhyMetric] = useState<WhyMetricId | null>(null);
  const insightsQuery = useQuery({
    queryKey: ["cfo", "daily-insights"],
    queryFn: () => apiGet<DailyInsightsResponse>("/cfo/insights"),
    retry: false,
  });
  const refundWhy = useQuery({ queryKey: ["why", "refund_rate"], queryFn: () => apiGet<WhyMetricResponse>("/why/refund_rate"), retry: false });
  const successWhy = useQuery({ queryKey: ["why", "payment_success_rate"], queryFn: () => apiGet<WhyMetricResponse>("/why/payment_success_rate"), retry: false });
  const chat = useMutation({
    mutationFn: (input: CfoChatRequest) => apiPost<CfoChatResponse>("/cfo/chat", input),
    onSuccess: (response) => {
      setConversation((items) => items.map((item) => item.id === response.id ? item : item.question === response.question && !item.response ? { ...item, id: response.id, response } : item));
    },
  });

  const ask = (value: string) => {
    const clean = value.trim();
    if (clean.length < 3 || chat.isPending) return;
    const localId = `pending-${Date.now()}`;
    setConversation((items) => [...items, { id: localId, question: clean }]);
    setQuestion("");
    chat.mutate({ question: clean });
  };
  const submit = (event: FormEvent) => { event.preventDefault(); ask(question); };
  const insights = insightsQuery.data;

  return (
    <div className="space-y-7" data-testid="cfo-page">
      <section className="flex flex-col justify-between gap-5 xl:flex-row xl:items-end">
        <div><p className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-rose-600" data-testid="cfo-eyebrow">Decide</p><h1 className="font-heading text-3xl font-bold tracking-[-0.04em] text-slate-950" data-testid="cfo-title">AI CFO</h1><p className="mt-2 max-w-2xl text-sm text-slate-500" data-testid="cfo-description">Ask financial questions and see the tools, facts, predictions, and reasoning behind every answer.</p></div>
        <div className="flex items-center gap-2 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs font-semibold text-emerald-700" data-testid="cfo-engine-status"><ShieldCheck size={15} />Deterministic mode · Ollama ready</div>
      </section>

      <section className="grid gap-4 sm:grid-cols-2" data-testid="cfo-operating-signals"><WhySignal title="Refund rate" data={refundWhy.data} loading={refundWhy.isLoading} icon={<RotateCcw size={17} />} onExplain={() => setWhyMetric("refund_rate")} testId="refund-rate-signal" /><WhySignal title="Payment success rate" data={successWhy.data} loading={successWhy.isLoading} icon={<CheckCircle2 size={17} />} onExplain={() => setWhyMetric("payment_success_rate")} testId="payment-success-signal" /></section>

      <section data-testid="cfo-daily-insights-section">
        <div className="mb-4 flex items-end justify-between"><div><p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400" data-testid="cfo-daily-insights-eyebrow">Generated today</p><h2 className="mt-2 font-heading text-xl font-bold tracking-tight text-slate-900" data-testid="cfo-daily-insights-title">Daily financial brief</h2></div>{insights && <p className="font-mono text-[10px] text-slate-400" data-testid="cfo-insights-as-of">As of {insights.as_of_date}</p>}</div>
        {insightsQuery.isError ? <div className="rounded-lg border border-amber-200 bg-amber-50 p-5 text-sm text-amber-800" data-testid="cfo-insights-error">Daily insights are unavailable. The chat workspace remains visible.</div> : insights ? <><div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5" data-testid="cfo-insights-grid">{insights.insights.map((insight) => <InsightCard key={insight.id} insight={insight} onAsk={() => ask(questionForInsight(insight))} />)}</div><p className="mt-3 text-[10px] leading-5 text-slate-400" data-testid="cfo-insights-disclaimer">{insights.disclaimer}</p></> : <div className="rounded-lg border border-slate-200 bg-white p-6 text-sm text-slate-500" data-testid="cfo-insights-loading">Running read-only financial tools…</div>}
      </section>

      <section className="grid min-h-[620px] overflow-hidden rounded-lg border border-slate-200 bg-white xl:grid-cols-[310px_1fr]" data-testid="cfo-chat-workspace">
        <aside className="border-b border-slate-200 bg-slate-50 p-5 xl:border-b-0 xl:border-r" data-testid="cfo-chat-sidebar">
          <div className="flex items-center gap-3"><div className="flex h-9 w-9 items-center justify-center rounded-md bg-rose-600 text-white"><Bot size={18} /></div><div><p className="font-heading text-sm font-bold text-slate-900" data-testid="cfo-chat-sidebar-title">Financial copilot</p><p className="text-[10px] text-slate-400" data-testid="cfo-chat-sidebar-mode">Read-only · grounded answers</p></div></div>
          <div className="mt-7"><p className="text-[10px] font-bold uppercase tracking-[0.14em] text-slate-400" data-testid="cfo-suggested-questions-label">Suggested questions</p><div className="mt-3 space-y-2" data-testid="cfo-suggested-questions">{prompts.map((prompt, index) => <button key={prompt} type="button" onClick={() => ask(prompt)} disabled={chat.isPending} className="group flex w-full items-start justify-between gap-2 rounded-md border border-slate-200 bg-white p-3 text-left text-xs leading-5 text-slate-600 transition-colors hover:border-rose-200 hover:text-rose-700 disabled:opacity-50" data-testid={`cfo-suggested-question-${index + 1}`}><span>{prompt}</span><ArrowRight size={13} className="mt-1 shrink-0 transition-transform group-hover:translate-x-0.5" /></button>)}</div></div>
          <div className="mt-7 rounded-md border border-slate-200 bg-white p-4" data-testid="cfo-safety-card"><div className="flex items-center gap-2 text-xs font-bold text-slate-700" data-testid="cfo-safety-title"><ShieldCheck size={14} className="text-emerald-500" />Safe by design</div><ul className="mt-3 space-y-2 text-[10px] leading-4 text-slate-500" data-testid="cfo-safety-list"><li>No write access to records</li><li>No LLM financial calculations</li><li>Predictions labeled separately</li><li>Sources included with answers</li></ul></div>
        </aside>

        <div className="flex min-h-[620px] flex-col" data-testid="cfo-chat-panel">
          <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4 sm:px-6"><div><p className="font-heading text-sm font-bold text-slate-900" data-testid="cfo-chat-title">Ask your financial data</p><p className="mt-0.5 text-[10px] text-slate-400" data-testid="cfo-chat-subtitle">Session-only conversation · not stored</p></div>{conversation.length > 0 && <Button type="button" variant="ghost" size="sm" onClick={() => setConversation([])} data-testid="cfo-clear-chat-button"><Eraser size={14} />Clear</Button>}</div>

          <div className="flex-1 space-y-6 overflow-y-auto p-5 sm:p-6" data-testid="cfo-chat-messages">
            {conversation.length === 0 && <div className="mx-auto flex max-w-lg flex-col items-center py-16 text-center" data-testid="cfo-chat-empty-state"><div className="flex h-12 w-12 items-center justify-center rounded-lg bg-rose-50 text-rose-600"><Sparkles size={22} /></div><h3 className="mt-5 font-heading text-lg font-bold text-slate-900" data-testid="cfo-chat-empty-title">Start with a financial question</h3><p className="mt-2 text-sm leading-6 text-slate-500" data-testid="cfo-chat-empty-copy">I will select relevant read-only tools, separate facts from forecasts, and show every source used.</p></div>}
            {conversation.map((item) => <Conversation key={item.id} item={item} />)}
            {chat.isError && <div className="rounded-md border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800" data-testid="cfo-chat-error">The financial tools could not answer this question. No records were changed.</div>}
          </div>

          <form onSubmit={submit} className="border-t border-slate-100 bg-white p-4 sm:p-5" data-testid="cfo-chat-form"><div className="rounded-lg border border-slate-200 bg-white p-2 shadow-sm focus-within:border-rose-300 focus-within:ring-2 focus-within:ring-rose-50"><Textarea value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Ask about revenue, settlements, cash, risks, customers…" maxLength={600} rows={2} className="min-h-16 resize-none border-0 bg-transparent shadow-none focus-visible:ring-0" data-testid="cfo-chat-input" /><div className="flex items-center justify-between gap-3 px-2 pb-1"><p className="text-[10px] text-slate-400" data-testid="cfo-chat-input-note">Financial context is selected on the server</p><Button type="submit" disabled={question.trim().length < 3 || chat.isPending} className="bg-rose-600 text-white hover:bg-rose-700" data-testid="cfo-chat-submit-button">{chat.isPending ? "Analyzing…" : "Ask CFO"}<Send size={14} /></Button></div></div></form>
        </div>
      </section>
      <WhyMetricSheet metricId={whyMetric} open={Boolean(whyMetric)} onOpenChange={(open) => { if (!open) setWhyMetric(null); }} />
    </div>
  );
}

function WhySignal({ title, data, loading, icon, onExplain, testId }: { title: string; data?: WhyMetricResponse; loading: boolean; icon: ReactNode; onExplain: () => void; testId: string }) { return <div className="rounded-lg border border-slate-200 bg-white p-5" data-testid={testId}><div className="flex items-start justify-between"><div><p className="text-xs font-medium text-slate-400" data-testid={`${testId}-label`}>{title}</p><p className="mt-3 font-mono text-2xl font-medium text-slate-900" data-testid={`${testId}-value`}>{loading || !data ? "—" : `${data.current_value.toFixed(2)}%`}</p><p className="mt-1 text-[10px] text-slate-500" data-testid={`${testId}-change`}>{data ? `${data.direction} ${data.change_summary} vs previous month` : "Calculating drivers…"}</p></div><span className="flex h-9 w-9 items-center justify-center rounded-md bg-rose-50 text-rose-600">{icon}</span></div><button type="button" onClick={onExplain} disabled={!data} className="mt-4 inline-flex items-center gap-1.5 text-[10px] font-bold text-rose-700 disabled:opacity-40" data-testid={`${testId}-why-button`}><HelpCircle size={12} />Why?</button></div>; }

function questionForInsight(insight: DailyInsight) { const questions: Record<string, string> = { Reconciliation: "Show me my biggest reconciliation problems.", "Cash flow": "Will I have enough cash next month?", Revenue: "Why did revenue fall this month?", "Payment failures": "Why are payments failing this month?", Refunds: "What is driving refunds this month?" }; return questions[insight.category] ?? "What should I be concerned about today?"; }

function InsightCard({ insight, onAsk }: { insight: DailyInsight; onAsk: () => void }) {
  const meta = { high: { className: "bg-rose-50 text-rose-700", icon: <CircleAlert size={13} /> }, medium: { className: "bg-amber-50 text-amber-700", icon: <Clock3 size={13} /> }, low: { className: "bg-emerald-50 text-emerald-700", icon: <CheckCircle2 size={13} /> } }[insight.severity];
  const categoryPaths: Record<string, string> = { Reconciliation: "/reconciliation", "Cash flow": "/forecast", Revenue: "/cfo", "Payment failures": "/cfo", Refunds: "/cfo" };
  const ctaLabels: Record<string, string> = { Reconciliation: "Review Queue", "Cash flow": "View Forecast", Revenue: "Investigate", "Payment failures": "Review Failures", Refunds: "Analyze Refunds" };
  return <article className="flex flex-col rounded-lg border border-slate-200 bg-white p-4 transition-transform hover:-translate-y-0.5 hover:shadow-sm" data-testid={`cfo-insight-${insight.id}`}><div className="flex items-center justify-between"><span className={`inline-flex items-center gap-1 rounded-full px-2 py-1 text-[9px] font-bold uppercase ${meta.className}`} data-testid={`cfo-insight-severity-${insight.id}`}>{meta.icon}{insight.severity}</span><span className="text-[9px] font-semibold uppercase tracking-wide text-slate-400" data-testid={`cfo-insight-classification-${insight.id}`}>{insight.classification}</span></div><p className="mt-4 text-[10px] font-bold uppercase tracking-[0.12em] text-rose-600" data-testid={`cfo-insight-category-${insight.id}`}>{insight.category}</p><h3 className="mt-2 font-heading text-sm font-bold leading-5 text-slate-900" data-testid={`cfo-insight-title-${insight.id}`}>{insight.title}</h3><p className="mt-2 flex-1 text-[11px] leading-5 text-slate-500" data-testid={`cfo-insight-summary-${insight.id}`}>{insight.summary}</p><div className="mt-4 border-t border-slate-100 pt-3"><p className="text-[9px] text-slate-400" data-testid={`cfo-insight-metric-label-${insight.id}`}>{insight.metric_label}</p><p className="mt-1 font-mono text-base font-medium text-slate-900" data-testid={`cfo-insight-metric-value-${insight.id}`}>{insight.metric_value}</p><div className="mt-3 flex items-center gap-2"><button type="button" onClick={onAsk} className="inline-flex items-center gap-1.5 text-[10px] font-bold text-rose-700 transition-transform hover:translate-x-0.5" data-testid={`cfo-insight-ask-${insight.id}`}>Ask Why<ArrowRight size={12} /></button><span className="text-slate-300">·</span><Link to={categoryPaths[insight.category] ?? "/cfo"} className="inline-flex items-center gap-1.5 text-[10px] font-bold text-slate-600 transition-transform hover:translate-x-0.5" data-testid={`cfo-insight-action-${insight.id}`}>{ctaLabels[insight.category] ?? "View Details"}<ArrowRight size={12} /></Link></div></div></article>;
}

function Conversation({ item }: { item: ConversationItem }) { return <div className="space-y-4" data-testid={`cfo-conversation-${item.id}`}><div className="ml-auto flex max-w-2xl items-start justify-end gap-3"><div className="rounded-lg rounded-tr-sm bg-slate-900 px-4 py-3 text-sm leading-6 text-white" data-testid={`cfo-user-message-${item.id}`}>{item.question}</div><div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-100 text-slate-600"><UserRound size={15} /></div></div>{item.response ? <AssistantAnswer response={item.response} /> : <div className="flex items-center gap-3 text-xs text-slate-400" data-testid={`cfo-answer-loading-${item.id}`}><div className="flex h-8 w-8 items-center justify-center rounded-md bg-rose-50 text-rose-600"><Bot size={15} /></div><span className="animate-pulse">Running relevant financial tools…</span></div>}</div>; }

function AssistantAnswer({ response }: { response: CfoChatResponse }) { return <div className="flex items-start gap-3" data-testid={`cfo-assistant-answer-${response.id}`}><div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-rose-600 text-white"><Bot size={15} /></div><div className="min-w-0 max-w-3xl flex-1 rounded-lg rounded-tl-sm border border-slate-200 bg-white p-5"><div className="flex flex-wrap items-center gap-2"><span className="rounded-full bg-emerald-50 px-2 py-1 text-[9px] font-bold uppercase tracking-wide text-emerald-700" data-testid={`cfo-answer-mode-${response.id}`}>{response.mode.replaceAll("_", " ")}</span><span className="inline-flex items-center gap-1 text-[10px] text-slate-400" data-testid={`cfo-answer-readonly-${response.id}`}><ShieldCheck size={11} />Read only</span>{response.insufficient_data && <span className="rounded-full bg-amber-50 px-2 py-1 text-[9px] font-bold text-amber-700" data-testid={`cfo-answer-insufficient-${response.id}`}>Insufficient data</span>}</div><p className="mt-4 text-sm leading-7 text-slate-700" data-testid={`cfo-answer-text-${response.id}`}>{response.answer}</p><AnswerSection title="Recorded facts" items={response.facts} icon={<Database size={13} />} testId={`cfo-facts-${response.id}`} /><AnswerSection title="Predictions" items={response.predictions} icon={<Sparkles size={13} />} testId={`cfo-predictions-${response.id}`} accent /><AnswerSection title="Reasoning" items={response.reasoning} icon={<Bot size={13} />} testId={`cfo-reasoning-${response.id}`} /><AnswerSection title="Recommendations" items={response.recommendations} icon={<ArrowRight size={13} />} testId={`cfo-recommendations-${response.id}`} /><div className="mt-5 border-t border-slate-100 pt-4" data-testid={`cfo-sources-${response.id}`}><div className="flex items-center justify-between"><p className="text-[10px] font-bold uppercase tracking-[0.13em] text-slate-400">Sources used</p><span className="font-mono text-[9px] text-slate-400">{response.tools_used.length} tools</span></div><div className="mt-2 flex flex-wrap gap-1.5">{response.tools_used.map((tool) => <span key={tool} className="rounded bg-slate-100 px-2 py-1 font-mono text-[9px] text-slate-600" data-testid={`cfo-tool-${tool}`}>{tool}</span>)}</div><div className="mt-3 space-y-1" data-testid={`cfo-source-references-${response.id}`}>{response.sources.slice(0, 8).map((source) => <p key={source.id} className="text-[9px] leading-4 text-slate-400" data-testid={`cfo-source-${source.id.replaceAll(":", "-")}`}>{source.classification.toUpperCase()} · {source.label} · {source.period}</p>)}</div><p className="mt-3 text-[10px] leading-5 text-slate-400" data-testid={`cfo-provider-message-${response.id}`}>{response.provider_message} · {response.sources.length} source references attached.</p></div></div></div>; }

function AnswerSection({ title, items, icon, testId, accent = false }: { title: string; items: string[]; icon: ReactNode; testId: string; accent?: boolean }) { if (!items.length) return null; return <div className={`mt-4 rounded-md p-3 ${accent ? "bg-rose-50" : "bg-slate-50"}`} data-testid={testId}><p className={`flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-[0.12em] ${accent ? "text-rose-700" : "text-slate-500"}`}>{icon}{title}</p><ul className="mt-2 space-y-1.5">{items.map((item, index) => <li key={`${title}-${index}`} className="text-xs leading-5 text-slate-600" data-testid={`${testId}-item-${index + 1}`}>{item}</li>)}</ul></div>; }