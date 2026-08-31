import type { FormEvent } from "react";
import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Check, Database, FileCheck2, FileSpreadsheet, Link2, LoaderCircle, RefreshCw, Search, ShieldCheck, SlidersHorizontal, UploadCloud } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { apiGet, apiPost, apiPut, apiUpload } from "@/lib/api";
import { formatDate, formatPaiseINR } from "@/lib/format";
import type {
  ColumnMapping,
  FinancialImportResult,
  FinancialSourceType,
  ImportBatchList,
  ImportedTransactionPage,
  ImportedTransactionView,
  ImportMatchStatus,
  ImportReconciliationSummary,
  ImportWorkspaceResponse,
} from "@/lib/types";

const sourceTypes: Array<{ id: FinancialSourceType; label: string; detail: string }> = [
  { id: "bank", label: "Bank transactions", detail: "Statements, credits, debits and UTR references" },
  { id: "payment_gateway", label: "Payment gateway", detail: "Payments, fees, refunds and settlement references" },
  { id: "accounting", label: "Accounting ledger", detail: "Invoices, journal entries and booked expenses" },
  { id: "marketplace", label: "Marketplace", detail: "Orders, commissions and marketplace payouts" },
];

const mappingFields: Array<{ key: keyof ColumnMapping; label: string; required?: boolean; note: string }> = [
  { key: "transaction_id", label: "Transaction ID", note: "Unique source identifier" },
  { key: "reference", label: "Reference / Order ID", note: "Used for strongest match" },
  { key: "date", label: "Transaction date", required: true, note: "Required" },
  { key: "amount", label: "Amount", note: "Use instead of split debit/credit" },
  { key: "debit", label: "Debit amount", note: "Optional split bank column" },
  { key: "credit", label: "Credit amount", note: "Optional split bank column" },
  { key: "direction", label: "Direction", note: "Credit / debit" },
  { key: "description", label: "Description", note: "Narration or memo" },
  { key: "currency", label: "Currency", note: "Defaults to INR" },
  { key: "status", label: "Status", note: "Original transaction state" },
  { key: "counterparty", label: "Counterparty", note: "Customer, vendor or payee" },
];

export default function Connect() {
  const queryClient = useQueryClient();
  const [sourceType, setSourceType] = useState<FinancialSourceType>("bank");
  const [file, setFile] = useState<File | null>(null);
  const [activeBatchId, setActiveBatchId] = useState<string | null>(null);
  const [mapping, setMapping] = useState<ColumnMapping | null>(null);
  const [matchFilter, setMatchFilter] = useState<ImportMatchStatus | "ALL">("ALL");
  const [selectedTransaction, setSelectedTransaction] = useState<ImportedTransactionView | null>(null);

  const batchesQuery = useQuery({
    queryKey: ["import-batches"], queryFn: () => apiGet<ImportBatchList>("/imports/batches"), retry: false,
  });
  const workspaceQuery = useQuery({
    queryKey: ["import-workspace", activeBatchId],
    queryFn: () => apiGet<ImportWorkspaceResponse>(`/imports/${activeBatchId}`),
    enabled: Boolean(activeBatchId), retry: false,
  });
  const workspace = workspaceQuery.data;
  useEffect(() => {
    if (workspace) setMapping(workspace.mapping);
  }, [workspace?.batch.id, workspace?.batch.status]);

  const transactionsQuery = useQuery({
    queryKey: ["import-transactions", activeBatchId, matchFilter],
    queryFn: () => apiGet<ImportedTransactionPage>(`/imports/${activeBatchId}/transactions${matchFilter === "ALL" ? "" : `?match_status=${matchFilter}`}`),
    enabled: Boolean(activeBatchId && workspace && ["IMPORTED", "RECONCILED"].includes(workspace.batch.status)),
    retry: false,
  });

  const analyze = useMutation({
    mutationFn: async () => {
      if (!file) throw new Error("Select a CSV file");
      const body = new FormData();
      body.append("source_type", sourceType);
      body.append("file", file);
      return apiUpload<ImportWorkspaceResponse>("/imports/analyze", body);
    },
    onSuccess: (result) => {
      setActiveBatchId(result.batch.id);
      setMapping(result.mapping);
      queryClient.setQueryData(["import-workspace", result.batch.id], result);
      queryClient.invalidateQueries({ queryKey: ["import-batches"] });
      toast.success("CSV analyzed", { description: `${result.batch.row_count.toLocaleString("en-IN")} source rows are ready for mapping.` });
    },
    onError: () => toast.error("CSV analysis failed", { description: "Check the file format, size, and header row." }),
  });
  const saveMapping = useMutation({
    mutationFn: () => apiPut<ImportWorkspaceResponse>(`/imports/${activeBatchId}/mapping`, { mapping }),
    onSuccess: (result) => {
      queryClient.setQueryData(["import-workspace", result.batch.id], result);
      setMapping(result.mapping);
      toast.success("Column mapping applied");
    },
    onError: () => toast.error("Mapping is incomplete", { description: "Map a date and either amount or debit/credit columns." }),
  });
  const confirmImport = useMutation({
    mutationFn: () => apiPost<FinancialImportResult>(`/imports/${activeBatchId}/import`, {}),
    onSuccess: async (result) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["import-workspace", result.batch.id] }),
        queryClient.invalidateQueries({ queryKey: ["import-transactions", result.batch.id] }),
        queryClient.invalidateQueries({ queryKey: ["import-batches"] }),
      ]);
      toast.success("Import and reconciliation complete", { description: result.message });
    },
    onError: () => toast.error("Import failed", { description: "Resolve mapping or row validation errors and try again." }),
  });
  const reconcile = useMutation({
    mutationFn: () => apiPost<FinancialImportResult>(`/imports/${activeBatchId}/reconcile`, {}),
    onSuccess: async (result) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["import-workspace", result.batch.id] }),
        queryClient.invalidateQueries({ queryKey: ["import-transactions", result.batch.id] }),
      ]);
      toast.success("Reconciliation refreshed", { description: result.message });
    },
    onError: () => toast.error("Reconciliation could not run"),
  });

  const mappingReady = Boolean(mapping?.date && (mapping.amount || mapping.debit || mapping.credit));
  const mappingDirty = Boolean(workspace && mapping && JSON.stringify(mapping) !== JSON.stringify(workspace.mapping));
  const submitUpload = (event: FormEvent) => { event.preventDefault(); analyze.mutate(); };

  return (
    <div className="space-y-7" data-testid="connect-sources-page">
      <section className="flex flex-col justify-between gap-4 border-b border-slate-200 pb-7 lg:flex-row lg:items-end">
        <div><p className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-rose-600" data-testid="connect-sources-eyebrow">Universal data import</p><h1 className="font-heading text-3xl font-bold tracking-[-0.04em] text-slate-950" data-testid="connect-sources-title">Connect Financial Sources</h1><p className="mt-2 max-w-2xl text-sm text-slate-500" data-testid="connect-sources-description">Map any financial CSV into one traceable transaction model, then reconcile it with deterministic rules.</p></div><div className="inline-flex items-center gap-2 self-start rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs font-semibold text-emerald-700" data-testid="connect-sources-safety"><ShieldCheck size={15} />Local SQLite · no external APIs</div>
      </section>

      <section className="grid grid-cols-3 gap-px overflow-hidden rounded-lg border border-slate-200 bg-slate-200 md:grid-cols-6" data-testid="import-workflow-steps">{["Upload CSV", "Source Type", "Column Mapping", "Preview", "Import", "Reconcile"].map((step, index) => <div key={step} className="bg-white p-3 sm:p-4" data-testid={`import-step-${index + 1}`}><p className="font-mono text-[9px] text-rose-500">0{index + 1}</p><p className="mt-1 text-[10px] font-bold text-slate-700 sm:text-xs">{step}</p></div>)}</section>

      <section className="grid gap-5 xl:grid-cols-[1.55fr_0.75fr]" data-testid="import-start-section">
        <form onSubmit={submitUpload} className="rounded-lg border border-slate-200 bg-white p-5 sm:p-6" data-testid="csv-upload-form">
          <div className="flex items-start gap-3"><div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-rose-50 text-rose-600"><UploadCloud size={19} /></div><div><h2 className="font-heading text-lg font-bold text-slate-900" data-testid="csv-upload-title">Upload CSV</h2><p className="mt-1 text-xs text-slate-500" data-testid="csv-upload-limits">Up to 25 MB and 100,000 rows. Original row values are preserved.</p></div></div>
          <div className="mt-6 grid gap-4 sm:grid-cols-[0.8fr_1.2fr]">
            <label data-testid="source-type-label"><span className="mb-2 block text-[10px] font-bold uppercase tracking-[0.13em] text-slate-400">Source Type</span><select value={sourceType} onChange={(event) => setSourceType(event.target.value as FinancialSourceType)} className="h-11 w-full rounded-md border border-slate-200 bg-white px-3 text-xs text-slate-700 outline-none transition-colors focus:border-rose-400" data-testid="source-type-select">{sourceTypes.map((source) => <option key={source.id} value={source.id}>{source.label}</option>)}</select><span className="mt-2 block text-[10px] leading-4 text-slate-400">{sourceTypes.find((source) => source.id === sourceType)?.detail}</span></label>
            <label className="group flex min-h-28 cursor-pointer items-center justify-center rounded-lg border border-dashed border-slate-300 bg-slate-50 p-4 text-center transition-colors hover:border-rose-300 hover:bg-rose-50/40" data-testid="csv-file-dropzone"><input type="file" accept=".csv,text/csv" onChange={(event) => setFile(event.target.files?.[0] ?? null)} className="sr-only" data-testid="csv-file-input" /><div><FileSpreadsheet size={22} className="mx-auto text-slate-400 group-hover:text-rose-500" /><p className="mt-2 text-xs font-semibold text-slate-700" data-testid="csv-selected-file">{file?.name ?? "Choose a CSV file"}</p><p className="mt-1 text-[10px] text-slate-400">Click to browse</p></div></label>
          </div>
          <div className="mt-5 flex justify-end"><Button type="submit" disabled={!file || analyze.isPending} className="bg-rose-600 text-white hover:bg-rose-700" data-testid="csv-analyze-button">{analyze.isPending ? <><LoaderCircle size={14} className="animate-spin" />Detecting columns…</> : <><Search size={14} />Analyze CSV</>}</Button></div>
        </form>

        <div className="rounded-lg border border-slate-200 bg-white p-5" data-testid="import-batch-history"><div className="flex items-center justify-between"><div><p className="text-[10px] font-bold uppercase tracking-[0.13em] text-slate-400">Import history</p><h2 className="mt-1 font-heading text-sm font-bold text-slate-900">Recent batches</h2></div><Database size={17} className="text-slate-400" /></div><div className="mt-4 space-y-2">{batchesQuery.data?.batches.slice(0, 5).map((batch) => <button key={batch.id} type="button" onClick={() => { setActiveBatchId(batch.id); setMatchFilter("ALL"); }} className={`w-full rounded-md border p-3 text-left transition-colors ${activeBatchId === batch.id ? "border-rose-300 bg-rose-50" : "border-slate-200 hover:bg-slate-50"}`} data-testid={`import-batch-${batch.id}`}><div className="flex items-center justify-between gap-2"><p className="truncate text-xs font-semibold text-slate-700" data-testid={`import-batch-${batch.id}-filename`}>{batch.filename}</p><span className="rounded bg-slate-100 px-1.5 py-0.5 text-[8px] font-bold text-slate-500">{batch.status}</span></div><p className="mt-1 text-[9px] text-slate-400">{batch.source_type.replaceAll("_", " ")} · {batch.row_count.toLocaleString("en-IN")} rows</p></button>)}{!batchesQuery.data?.batches.length && <p className="rounded-md bg-slate-50 p-4 text-center text-[10px] text-slate-400" data-testid="import-history-empty">No CSV imports yet</p>}</div></div>
      </section>

      {workspace && mapping && <>
        <section className="rounded-lg border border-slate-200 bg-white" data-testid="column-mapping-section">
          <div className="flex flex-col justify-between gap-3 border-b border-slate-100 p-5 sm:flex-row sm:items-center sm:p-6"><div><div className="flex items-center gap-2"><SlidersHorizontal size={16} className="text-rose-600" /><h2 className="font-heading text-lg font-bold text-slate-900" data-testid="column-mapping-title">Column Mapping</h2></div><p className="mt-1 text-xs text-slate-500" data-testid="column-mapping-subtitle">Auto-detected values can be corrected before import.</p></div><div className="text-left sm:text-right"><p className="text-[10px] text-slate-400" data-testid="mapping-batch-filename">{workspace.batch.filename}</p><p className="font-mono text-[9px] text-slate-400" data-testid="mapping-file-hash">SHA-256 · {workspace.batch.file_sha256.slice(0, 16)}…</p></div></div>
          <div className="grid gap-px bg-slate-100 sm:grid-cols-2 xl:grid-cols-3" data-testid="mapping-fields-grid">{mappingFields.map((field) => { const suggestion = workspace.suggestions.find((item) => item.internal_field === field.key); return <label key={field.key} className="bg-white p-4" data-testid={`mapping-field-${field.key}`}><div className="flex items-center justify-between"><span className="text-xs font-semibold text-slate-700">{field.label}{field.required && <span className="ml-1 text-rose-500">*</span>}</span><span className={`text-[9px] font-bold ${suggestion && suggestion.confidence >= 0.8 ? "text-emerald-600" : "text-slate-400"}`} data-testid={`mapping-confidence-${field.key}`}>{suggestion?.detected_column ? `${Math.round(suggestion.confidence * 100)}% detected` : field.note}</span></div><select value={mapping[field.key] ?? ""} onChange={(event) => setMapping({ ...mapping, [field.key]: event.target.value || null })} disabled={workspace.batch.status !== "ANALYZED"} className="mt-2 h-9 w-full rounded-md border border-slate-200 bg-white px-2 text-xs text-slate-600 outline-none focus:border-rose-400 disabled:bg-slate-50" data-testid={`mapping-select-${field.key}`}><option value="">Not mapped</option>{workspace.headers.map((header) => <option key={header} value={header}>{header}</option>)}</select></label>; })}</div>
          {workspace.batch.status === "ANALYZED" && <div className="flex items-center justify-between border-t border-slate-100 p-4 sm:px-6"><p className={`text-[10px] ${mappingReady ? "text-emerald-600" : "text-amber-600"}`} data-testid="mapping-readiness">{mappingReady ? "Required fields are mapped" : "Map a date and an amount or debit/credit column"}</p><Button type="button" variant="outline" disabled={!mappingReady || saveMapping.isPending} onClick={() => saveMapping.mutate()} data-testid="apply-mapping-button">{saveMapping.isPending ? "Applying…" : "Apply mapping"}</Button></div>}
        </section>

        <section className="rounded-lg border border-slate-200 bg-white" data-testid="import-preview-section"><div className="flex items-center justify-between border-b border-slate-100 p-5 sm:p-6"><div><h2 className="font-heading text-lg font-bold text-slate-900" data-testid="import-preview-title">Preview</h2><p className="mt-1 text-xs text-slate-500" data-testid="import-preview-subtitle">Original source rows normalized into the internal transaction model.</p></div><span className="rounded-full bg-slate-100 px-2.5 py-1 text-[9px] font-bold uppercase text-slate-500" data-testid="import-preview-row-count">First {workspace.preview.length} rows</span></div><div className="overflow-x-auto"><table className="w-full min-w-[800px] text-left" data-testid="import-preview-table"><thead className="bg-slate-50 text-[9px] uppercase tracking-[0.12em] text-slate-400"><tr><th className="px-5 py-3">Source row</th><th className="px-5 py-3">ID / Reference</th><th className="px-5 py-3">Date</th><th className="px-5 py-3 text-right">Amount</th><th className="px-5 py-3">Direction</th><th className="px-5 py-3">Validation</th></tr></thead><tbody className="divide-y divide-slate-100">{workspace.preview.map((row) => <tr key={row.source_row_number} data-testid={`preview-row-${row.source_row_number}`}><td className="px-5 py-3 font-mono text-[10px] text-slate-400">#{row.source_row_number}</td><td className="px-5 py-3 font-mono text-[10px] text-slate-700">{row.normalized?.external_id ?? row.normalized?.reference ?? "—"}</td><td className="px-5 py-3 text-xs text-slate-500">{row.normalized?.transaction_date ? formatDate(row.normalized.transaction_date) : "—"}</td><td className="px-5 py-3 text-right font-mono text-xs text-slate-700">{row.normalized?.amount === null || row.normalized?.amount === undefined ? "—" : formatPaiseINR(row.normalized.amount)}</td><td className="px-5 py-3 text-xs capitalize text-slate-500">{row.normalized?.direction ?? "—"}</td><td className="px-5 py-3">{row.errors.length ? <span className="inline-flex items-center gap-1 rounded-full bg-rose-50 px-2 py-1 text-[9px] font-bold text-rose-700"><AlertTriangle size={10} />{row.errors[0]}</span> : <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-1 text-[9px] font-bold text-emerald-700"><Check size={10} />Ready</span>}</td></tr>)}</tbody></table></div>
          <div className="flex flex-col justify-between gap-3 border-t border-slate-100 p-4 sm:flex-row sm:items-center sm:px-6"><p className="text-[10px] text-slate-400" data-testid="import-trace-note">{mappingDirty ? "Apply mapping changes before import." : "Every normalized row retains its batch, filename, source row number, hash, and original values."}</p>{workspace.batch.status === "ANALYZED" ? <Button type="button" disabled={!mappingReady || mappingDirty || confirmImport.isPending} onClick={() => confirmImport.mutate()} className="bg-rose-600 text-white hover:bg-rose-700" data-testid="confirm-import-button">{confirmImport.isPending ? <><LoaderCircle size={14} className="animate-spin" />Importing & reconciling…</> : <><FileCheck2 size={14} />Import & Reconcile</>}</Button> : <Button type="button" variant="outline" disabled={reconcile.isPending} onClick={() => reconcile.mutate()} data-testid="rerun-reconciliation-button">{reconcile.isPending ? <><LoaderCircle size={14} className="animate-spin" />Reconciling…</> : <><RefreshCw size={14} />Reconcile again</>}</Button>}</div>
        </section>

        {workspace.reconciliation && <ReconciliationResults summary={workspace.reconciliation} transactions={transactionsQuery.data} filter={matchFilter} onFilter={setMatchFilter} onTrace={setSelectedTransaction} />}
      </>}

      <Sheet open={Boolean(selectedTransaction)} onOpenChange={(open) => { if (!open) setSelectedTransaction(null); }}><SheetContent side="right" className="w-full overflow-y-auto p-0 sm:max-w-xl" data-testid="import-trace-panel">{selectedTransaction && <><SheetHeader className="border-b border-slate-100 p-6 text-left"><p className="text-[10px] font-bold uppercase tracking-[0.14em] text-rose-600" data-testid="trace-source-label">{selectedTransaction.source_type.replaceAll("_", " ")} · source row {selectedTransaction.source_row_number}</p><SheetTitle className="font-heading text-xl" data-testid="trace-title">Transaction lineage</SheetTitle><SheetDescription data-testid="trace-description">Normalized values, deterministic match evidence, and untouched source fields.</SheetDescription></SheetHeader><TracePanel transaction={selectedTransaction} /></>}</SheetContent></Sheet>
    </div>
  );
}

function ReconciliationResults({ summary, transactions, filter, onFilter, onTrace }: { summary: ImportReconciliationSummary; transactions?: ImportedTransactionPage; filter: ImportMatchStatus | "ALL"; onFilter: (value: ImportMatchStatus | "ALL") => void; onTrace: (value: ImportedTransactionView) => void }) { return <section className="space-y-4" data-testid="import-reconciliation-results"><div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-end"><div><p className="text-xs font-semibold uppercase tracking-[0.16em] text-rose-600" data-testid="import-reconciliation-eyebrow">Reconcile</p><h2 className="mt-2 font-heading text-xl font-bold text-slate-900" data-testid="import-reconciliation-title">Deterministic reconciliation results</h2></div><p className="text-[10px] text-slate-400" data-testid="import-reconciliation-rule">Reference → exact amount/date → amount within ±2 days</p></div><div className="grid gap-3 sm:grid-cols-3 xl:grid-cols-6" data-testid="import-reconciliation-summary"><ResultMetric label="Matched" value={summary.matched.toLocaleString("en-IN")} tone="green" testId="import-summary-matched" /><ResultMetric label="Unmatched" value={summary.unmatched.toLocaleString("en-IN")} tone="slate" testId="import-summary-unmatched" /><ResultMetric label="Amount mismatch" value={summary.amount_mismatches.toLocaleString("en-IN")} tone="red" testId="import-summary-amount-mismatch" /><ResultMetric label="Date mismatch" value={summary.date_mismatches.toLocaleString("en-IN")} tone="amber" testId="import-summary-date-mismatch" /><ResultMetric label="Duplicates" value={summary.duplicates.toLocaleString("en-IN")} tone="blue" testId="import-summary-duplicates" /><ResultMetric label="Avg. confidence" value={`${summary.average_confidence}%`} tone="green" testId="import-summary-confidence" /></div><div className="rounded-lg border border-slate-200 bg-white" data-testid="import-transactions-card"><div className="flex flex-col justify-between gap-3 border-b border-slate-100 p-4 sm:flex-row sm:items-center sm:px-5"><div><h3 className="font-heading text-sm font-bold text-slate-900" data-testid="import-transactions-title">Normalized transactions</h3><p className="mt-1 text-[10px] text-slate-400" data-testid="import-transactions-count">{transactions ? `${transactions.total.toLocaleString("en-IN")} records` : "Loading records…"}</p></div><select value={filter} onChange={(event) => onFilter(event.target.value as ImportMatchStatus | "ALL")} className="h-9 rounded-md border border-slate-200 bg-white px-3 text-xs text-slate-600 outline-none focus:border-rose-400" data-testid="import-match-filter"><option value="ALL">All results</option><option value="MATCHED">Matched</option><option value="UNMATCHED">Unmatched</option><option value="AMOUNT_MISMATCH">Amount mismatch</option><option value="DATE_MISMATCH">Date mismatch</option><option value="DUPLICATE">Duplicates</option></select></div><div className="overflow-x-auto"><table className="w-full min-w-[920px] text-left" data-testid="import-transactions-table"><thead className="bg-slate-50 text-[9px] uppercase tracking-[0.12em] text-slate-400"><tr><th className="px-5 py-3">Source record</th><th className="px-5 py-3">Date</th><th className="px-5 py-3 text-right">Amount</th><th className="px-5 py-3">Match result</th><th className="px-5 py-3">Confidence</th><th className="px-5 py-3">Reason</th><th className="px-5 py-3 text-right">Trace</th></tr></thead><tbody className="divide-y divide-slate-100">{transactions?.items.map((item) => <tr key={item.id} className="transition-colors hover:bg-slate-50" data-testid={`import-transaction-${item.id}`}><td className="px-5 py-3"><p className="font-mono text-[10px] text-slate-700">{item.external_id ?? item.reference ?? item.id}</p><p className="mt-1 text-[9px] text-slate-400">row {item.source_row_number} · {item.source_type.replaceAll("_", " ")}</p></td><td className="px-5 py-3 text-xs text-slate-500">{formatDate(item.transaction_date)}</td><td className="px-5 py-3 text-right font-mono text-xs text-slate-700">{formatPaiseINR(item.amount)}</td><td className="px-5 py-3"><StatusBadge status={item.match_status} id={item.id} /></td><td className="px-5 py-3"><div className="flex items-center gap-2"><div className="h-1.5 w-16 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-emerald-500" style={{ width: `${item.confidence}%` }} /></div><span className="font-mono text-[9px] text-slate-500">{item.confidence}%</span></div></td><td className="max-w-xs truncate px-5 py-3 text-[10px] text-slate-500">{item.reason}</td><td className="px-5 py-3 text-right"><button type="button" onClick={() => onTrace(item)} className="inline-flex items-center gap-1 text-[10px] font-bold text-rose-700" data-testid={`trace-transaction-${item.id}`}><Link2 size={11} />Trace</button></td></tr>)}</tbody></table></div></div></section>; }

function ResultMetric({ label, value, tone, testId }: { label: string; value: string; tone: "green" | "slate" | "red" | "amber" | "blue"; testId: string }) { const colors = { green: "text-emerald-700", slate: "text-slate-700", red: "text-rose-700", amber: "text-amber-700", blue: "text-blue-700" }; return <div className="rounded-lg border border-slate-200 bg-white p-4" data-testid={testId}><p className="text-[9px] uppercase tracking-[0.12em] text-slate-400" data-testid={`${testId}-label`}>{label}</p><p className={`mt-2 font-mono text-xl font-medium ${colors[tone]}`} data-testid={`${testId}-value`}>{value}</p></div>; }
function StatusBadge({ status, id }: { status: ImportMatchStatus; id: string }) { const styles: Record<ImportMatchStatus, string> = { MATCHED: "bg-emerald-50 text-emerald-700", UNMATCHED: "bg-slate-100 text-slate-700", AMOUNT_MISMATCH: "bg-rose-50 text-rose-700", DATE_MISMATCH: "bg-amber-50 text-amber-700", DUPLICATE: "bg-blue-50 text-blue-700" }; return <span className={`inline-flex rounded-full px-2 py-1 text-[8px] font-bold tracking-wide ${styles[status]}`} data-testid={`match-status-${id}`}>{status.replaceAll("_", " ")}</span>; }
function TracePanel({ transaction }: { transaction: ImportedTransactionView }) { return <div className="space-y-6 p-6" data-testid="trace-content"><div className="grid grid-cols-2 gap-3" data-testid="trace-normalized-values"><TraceValue label="Internal ID" value={transaction.id} testId="trace-internal-id" /><TraceValue label="External ID" value={transaction.external_id ?? "—"} testId="trace-external-id" /><TraceValue label="Reference" value={transaction.reference ?? "—"} testId="trace-reference" /><TraceValue label="Date" value={formatDate(transaction.transaction_date)} testId="trace-date" /><TraceValue label="Amount" value={formatPaiseINR(transaction.amount)} testId="trace-amount" /><TraceValue label="Direction" value={transaction.direction} testId="trace-direction" /></div><div className="rounded-lg border border-slate-200 bg-slate-50 p-4" data-testid="trace-match-evidence"><div className="flex items-center justify-between"><p className="text-[10px] font-bold uppercase tracking-[0.13em] text-slate-400">Match evidence</p><StatusBadge status={transaction.match_status} id="trace-panel" /></div><p className="mt-3 text-sm leading-6 text-slate-700" data-testid="trace-match-reason">{transaction.reason}</p><div className="mt-4 grid grid-cols-2 gap-3"><TraceValue label="Rule" value={transaction.match_rule} testId="trace-match-rule" /><TraceValue label="Confidence" value={`${transaction.confidence}%`} testId="trace-confidence" /><TraceValue label="Matched record" value={transaction.matched_transaction_id ?? "—"} testId="trace-matched-id" /><TraceValue label="Date difference" value={transaction.date_difference_days === null ? "—" : `${transaction.date_difference_days} days`} testId="trace-date-difference" /></div></div><div data-testid="trace-original-source"><div className="flex items-end justify-between"><div><p className="text-[10px] font-bold uppercase tracking-[0.13em] text-slate-400">Original source information</p><p className="mt-1 text-xs text-slate-500">Untouched values from CSV row {transaction.source_row_number}</p></div><Database size={15} className="text-slate-400" /></div><div className="mt-3 divide-y divide-slate-100 rounded-lg border border-slate-200">{Object.entries(transaction.original_data).map(([key, value]) => <div key={key} className="grid grid-cols-[0.8fr_1.2fr] gap-3 p-3 text-xs" data-testid={`trace-original-${key.toLowerCase().replaceAll(" ", "-")}`}><span className="text-slate-400">{key}</span><span className="break-all font-mono text-[10px] text-slate-700">{value || "—"}</span></div>)}</div></div></div>; }
function TraceValue({ label, value, testId }: { label: string; value: string; testId: string }) { return <div data-testid={testId}><p className="text-[9px] uppercase tracking-[0.12em] text-slate-400">{label}</p><p className="mt-1 break-all font-mono text-[10px] font-medium text-slate-700">{value}</p></div>; }