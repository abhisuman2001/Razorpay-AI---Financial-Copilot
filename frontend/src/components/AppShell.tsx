import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { motion } from "motion/react";
import { NavLink, Outlet } from "react-router-dom";
import { Activity, Bot, ChartNoAxesCombined, Check, ChevronRight, CircleHelp, LayoutDashboard, ListChecks, LoaderCircle, Menu, Presentation, RefreshCw } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Toaster } from "@/components/ui/sonner";
import { apiGet, apiPost } from "@/lib/api";
import type { DashboardResponse, DemoScenarioActivation, DemoScenarioList } from "@/lib/types";

const navItems = [
  { to: "/", label: "Overview", icon: LayoutDashboard },
  { to: "/reconciliation", label: "Reconciliation", icon: ListChecks },
  { to: "/forecast", label: "Cash flow", icon: ChartNoAxesCombined },
  { to: "/cfo", label: "AI CFO", icon: Bot },
];

const navClass = ({ isActive }: { isActive: boolean }) =>
  `group flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition-colors ${
    isActive ? "bg-rose-50 text-rose-700" : "text-slate-500 hover:bg-slate-50 hover:text-slate-900"
  }`;

export default function AppShell() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [demoOpen, setDemoOpen] = useState(false);
  const [selectedScenario, setSelectedScenario] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const dashboard = useQuery({
    queryKey: ["dashboard"],
    queryFn: () => apiGet<DashboardResponse>("/dashboard"),
    retry: false,
  });
  const demoQuery = useQuery({
    queryKey: ["demo-scenarios"],
    queryFn: () => apiGet<DemoScenarioList>("/demo/scenarios"),
    retry: false,
  });
  const activeScenario = demoQuery.data?.scenarios.find((scenario) => scenario.active);
  const scenarioMutation = useMutation({
    mutationFn: (scenarioId: string) => apiPost<DemoScenarioActivation>(`/demo/scenarios/${scenarioId}/activate`, {}),
    onSuccess: async (result) => {
      await queryClient.invalidateQueries();
      setDemoOpen(false);
      setSelectedScenario(null);
      toast.success("Demo scenario activated", { description: result.message });
    },
    onError: () => toast.error("Scenario switch failed", { description: "The existing dataset remains active." }),
  });
  const refresh = async () => {
    await queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    await queryClient.invalidateQueries({ queryKey: ["executive-dashboard"] });
    await queryClient.invalidateQueries({ queryKey: ["reconciliation"] });
    await queryClient.invalidateQueries({ queryKey: ["forecast"] });
    await queryClient.invalidateQueries({ queryKey: ["cfo"] });
  };

  return (
    <div className="min-h-screen bg-[#f8f9fb] text-slate-900">
      <aside className="fixed inset-y-0 left-0 z-20 hidden w-[250px] border-r border-slate-200 bg-white lg:flex lg:flex-col">
        <div className="flex h-[72px] items-center gap-3 border-b border-slate-100 px-6" data-testid="sidebar-brand">
          <div className="flex h-9 w-9 items-center justify-center rounded-md bg-rose-600 text-lg font-bold text-white shadow-sm">R</div>
          <div>
            <p className="font-heading text-sm font-bold tracking-tight" data-testid="sidebar-product-name">Razorpay AI</p>
            <p className="text-[11px] text-slate-400" data-testid="sidebar-product-type">Financial Copilot</p>
          </div>
        </div>

        <div className="flex-1 px-4 py-7">
          <p className="mb-3 px-3 text-[10px] font-bold uppercase tracking-[0.16em] text-slate-400" data-testid="sidebar-navigation-label">Workspace</p>
          <nav className="space-y-1" aria-label="Primary navigation" data-testid="primary-navigation">
            {navItems.map(({ to, label, icon: Icon }) => (
              <NavLink key={to} to={to} end={to === "/"} className={navClass} data-testid={`nav-${label.toLowerCase().replaceAll(" ", "-")}`}>
                <Icon size={17} strokeWidth={1.8} />
                <span data-testid={`nav-label-${label.toLowerCase().replaceAll(" ", "-")}`}>{label}</span>
                <ChevronRight className="ml-auto h-3.5 w-3.5 opacity-0 transition-opacity group-hover:opacity-60" />
              </NavLink>
            ))}
          </nav>

          <div className="mt-10 rounded-lg border border-slate-200 bg-slate-50 p-4" data-testid="sidebar-model-card">
            <div className="mb-3 flex items-center justify-between">
              <span className="flex items-center gap-2 text-xs font-semibold text-slate-700" data-testid="model-status-label"><Activity size={13} className="text-emerald-500" />Data engine</span>
              <span className="h-2 w-2 rounded-full bg-emerald-500" data-testid="model-status-indicator" />
            </div>
            <p className="text-[11px] leading-5 text-slate-500" data-testid="model-status-copy">Synthetic ledger connected. Financial calculations are deterministic.</p>
          </div>
        </div>

        <div className="border-t border-slate-100 p-4">
          <div className="flex items-center gap-3 rounded-md p-2" data-testid="sidebar-user-profile">
            <img src="https://images.pexels.com/photos/27086922/pexels-photo-27086922.jpeg" alt="Aarav Mehta" className="h-8 w-8 rounded-full object-cover" />
            <div className="min-w-0">
              <p className="truncate text-xs font-semibold text-slate-800" data-testid="profile-name">Aarav Mehta</p>
              <p className="truncate text-[11px] text-slate-400" data-testid="profile-role">Finance lead</p>
            </div>
            <CircleHelp size={15} className="ml-auto text-slate-400" />
          </div>
        </div>
      </aside>

      <main className="lg:pl-[250px]">
        <header className="sticky top-0 z-10 flex h-[72px] items-center justify-between border-b border-slate-200 bg-white/95 px-5 backdrop-blur-sm sm:px-8" data-testid="top-header">
          <div className="flex items-center gap-3">
            <button type="button" onClick={() => setMobileOpen(true)} className="flex h-9 w-9 items-center justify-center rounded-md border border-slate-200 text-slate-600 transition-colors hover:bg-slate-50 lg:hidden" aria-label="Open navigation" data-testid="mobile-navigation-button"><Menu size={17} /></button>
            <div>
              <p className="text-xs font-medium text-slate-400" data-testid="header-breadcrumb">Workspace / Finance intelligence</p>
              <p className="font-heading text-sm font-semibold text-slate-800" data-testid="header-account-name">Northstar Commerce Pvt Ltd</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className="hidden items-center gap-1.5 text-xs text-slate-400 sm:flex" data-testid="header-data-status">
              <span className={`h-1.5 w-1.5 rounded-full ${dashboard.isError ? "bg-amber-500" : "bg-emerald-500"}`} />
              {dashboard.isError ? "Offline preview" : "Live synthetic data"}
            </span>
            <button type="button" onClick={() => { setSelectedScenario(demoQuery.data?.active_scenario_id ?? null); setDemoOpen(true); }} className="inline-flex items-center gap-2 rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-xs font-bold text-rose-700 transition-colors hover:bg-rose-100 active:scale-[0.98]" data-testid="demo-mode-button"><Presentation size={14} /><span>Demo Mode</span><span className="hidden font-medium text-rose-500 xl:inline" data-testid="demo-active-scenario-label">· {activeScenario?.name ?? "Loading"}</span></button>
            <button type="button" onClick={refresh} className="hidden items-center gap-2 rounded-md border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-600 transition-colors hover:border-slate-300 hover:bg-slate-50 active:scale-[0.98] sm:inline-flex" data-testid="header-refresh-button">
              <RefreshCw size={14} className={dashboard.isFetching ? "animate-spin" : ""} />
              <span className="hidden sm:inline">Refresh data</span>
            </button>
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-rose-100 text-xs font-bold text-rose-700" data-testid="header-user-avatar">AM</div>
          </div>
        </header>

        <div className="mx-auto max-w-[1440px] px-5 py-7 sm:px-8 sm:py-9">
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35 }}>
            <Outlet />
          </motion.div>
        </div>
      </main>

      <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
        <SheetContent side="left" className="w-[290px] p-0" data-testid="mobile-navigation-panel">
          <SheetHeader className="border-b border-slate-100 p-5 text-left"><SheetTitle className="font-heading text-base" data-testid="mobile-navigation-title">Razorpay AI</SheetTitle><SheetDescription data-testid="mobile-navigation-description">Financial Copilot workspace</SheetDescription></SheetHeader>
          <nav className="space-y-1 p-4" aria-label="Mobile navigation" data-testid="mobile-primary-navigation">{navItems.map(({ to, label, icon: Icon }) => <NavLink key={to} to={to} end={to === "/"} onClick={() => setMobileOpen(false)} className={navClass} data-testid={`mobile-nav-${label.toLowerCase().replaceAll(" ", "-")}`}><Icon size={17} /><span>{label}</span><ChevronRight size={14} className="ml-auto" /></NavLink>)}</nav>
        </SheetContent>
      </Sheet>

      <Dialog open={demoOpen} onOpenChange={(open) => { if (!scenarioMutation.isPending) setDemoOpen(open); }}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl" data-testid="demo-mode-dialog">
          <DialogHeader><DialogTitle className="flex items-center gap-2 font-heading text-xl" data-testid="demo-mode-title"><Presentation size={19} className="text-rose-600" />Demo Mode</DialogTitle><DialogDescription data-testid="demo-mode-description">Choose a financial situation to regenerate the shared synthetic dataset. Every dashboard and engine will respond through the same backend calculation pipeline.</DialogDescription></DialogHeader>
          <div className="grid gap-3 py-3 sm:grid-cols-2" data-testid="demo-scenario-grid">{demoQuery.data?.scenarios.map((scenario) => { const selected = selectedScenario === scenario.id; return <button key={scenario.id} type="button" onClick={() => setSelectedScenario(scenario.id)} disabled={scenarioMutation.isPending} className={`relative rounded-lg border p-4 text-left transition-[border-color,background-color,transform] hover:-translate-y-0.5 ${selected ? "border-rose-400 bg-rose-50" : "border-slate-200 bg-white hover:border-slate-300"}`} data-testid={`demo-scenario-${scenario.id}`}><div className="flex items-start justify-between gap-3"><div><p className="font-heading text-sm font-bold text-slate-900" data-testid={`demo-scenario-${scenario.id}-name`}>{scenario.name}</p><p className="mt-1 text-[10px] font-bold uppercase tracking-[0.12em] text-rose-600" data-testid={`demo-scenario-${scenario.id}-signal`}>{scenario.signal}</p></div><span className={`flex h-5 w-5 items-center justify-center rounded-full border ${selected ? "border-rose-600 bg-rose-600 text-white" : "border-slate-300 text-transparent"}`}><Check size={12} /></span></div><p className="mt-3 text-xs leading-5 text-slate-500" data-testid={`demo-scenario-${scenario.id}-description`}>{scenario.description}</p><div className="mt-3 flex flex-wrap gap-1.5">{scenario.expected_effects.map((effect) => <span key={effect} className="rounded bg-slate-100 px-2 py-1 text-[9px] font-medium text-slate-500">{effect}</span>)}</div>{scenario.active && <span className="absolute right-3 top-3 rounded-full bg-emerald-50 px-2 py-1 text-[8px] font-bold uppercase text-emerald-700" data-testid={`demo-scenario-${scenario.id}-active`}>Active</span>}</button>; })}</div>
          <div className="rounded-md border border-amber-200 bg-amber-50 p-3" data-testid="demo-mode-confirmation-note"><p className="text-xs font-bold text-amber-900">Confirm presentation switch</p><p className="mt-1 text-[11px] leading-5 text-amber-800">Activating replaces only synthetic merchant tables for this shared prototype. No production records or credentials are involved.</p></div>
          <DialogFooter className="mt-2"><Button type="button" variant="outline" onClick={() => setDemoOpen(false)} disabled={scenarioMutation.isPending} data-testid="demo-mode-cancel-button">Cancel</Button><Button type="button" onClick={() => selectedScenario && scenarioMutation.mutate(selectedScenario)} disabled={!selectedScenario || selectedScenario === demoQuery.data?.active_scenario_id || scenarioMutation.isPending} className="bg-rose-600 text-white hover:bg-rose-700" data-testid="demo-mode-activate-button">{scenarioMutation.isPending ? <><LoaderCircle size={14} className="animate-spin" />Switching scenario…</> : selectedScenario === demoQuery.data?.active_scenario_id ? "Already active" : "Activate scenario"}</Button></DialogFooter>
        </DialogContent>
      </Dialog>
      <Toaster richColors position="bottom-right" />
    </div>
  );
}