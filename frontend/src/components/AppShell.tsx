import type { ReactNode } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { motion } from "motion/react";
import { NavLink, Outlet } from "react-router-dom";
import { Activity, ArrowDownLeft, ArrowUpRight, Bot, ChartNoAxesCombined, ChevronRight, CircleHelp, LayoutDashboard, ListChecks, RefreshCw, Sparkles } from "lucide-react";

import { apiGet } from "@/lib/api";
import { formatINR } from "@/lib/format";
import type { DashboardResponse } from "@/lib/types";

const navItems = [
  { to: "/", label: "Overview", icon: LayoutDashboard },
  { to: "/reconciliation", label: "Reconciliation", icon: ListChecks },
  { to: "/forecast", label: "Cash forecast", icon: ChartNoAxesCombined },
  { to: "/cfo", label: "AI CFO", icon: Bot },
];

const navClass = ({ isActive }: { isActive: boolean }) =>
  `group flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition-colors ${
    isActive ? "bg-rose-50 text-rose-700" : "text-slate-500 hover:bg-slate-50 hover:text-slate-900"
  }`;

export default function AppShell() {
  const queryClient = useQueryClient();
  const dashboard = useQuery({
    queryKey: ["dashboard"],
    queryFn: () => apiGet<DashboardResponse>("/dashboard"),
    retry: false,
  });
  const summary = dashboard.data?.summary;

  const refresh = async () => {
    await queryClient.invalidateQueries({ queryKey: ["dashboard"] });
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
            <div className="flex h-8 w-8 items-center justify-center rounded-md bg-rose-50 text-sm font-bold text-rose-600 lg:hidden">R</div>
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
            <button type="button" onClick={refresh} className="inline-flex items-center gap-2 rounded-md border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-600 transition-colors hover:border-slate-300 hover:bg-slate-50 active:scale-[0.98]" data-testid="header-refresh-button">
              <RefreshCw size={14} className={dashboard.isFetching ? "animate-spin" : ""} />
              <span className="hidden sm:inline">Refresh data</span>
            </button>
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-rose-100 text-xs font-bold text-rose-700" data-testid="header-user-avatar">AM</div>
          </div>
        </header>

        <div className="mx-auto max-w-[1440px] px-5 py-7 sm:px-8 sm:py-9">
          <div className="mb-7 grid grid-cols-2 gap-3 xl:grid-cols-4" data-testid="quick-metrics-strip">
            <QuickMetric label="Cash balance" value={summary ? formatINR(summary.cash_balance, true) : "—"} icon={<ArrowUpRight size={14} />} tone="red" testId="quick-metric-cash" />
            <QuickMetric label="Incoming · 30d" value={summary ? formatINR(summary.incoming_30d, true) : "—"} icon={<ArrowDownLeft size={14} />} tone="green" testId="quick-metric-incoming" />
            <QuickMetric label="Outgoing · 30d" value={summary ? formatINR(summary.outgoing_30d, true) : "—"} icon={<ArrowUpRight size={14} />} tone="slate" testId="quick-metric-outgoing" />
            <QuickMetric label="Open exceptions" value={summary ? String(summary.open_exceptions) : "—"} icon={<Sparkles size={14} />} tone="amber" testId="quick-metric-exceptions" />
          </div>
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35 }}>
            <Outlet />
          </motion.div>
        </div>
      </main>
    </div>
  );
}

function QuickMetric({ label, value, icon, tone, testId }: { label: string; value: string; icon: ReactNode; tone: "red" | "green" | "slate" | "amber"; testId: string }) {
  const tones = { red: "bg-rose-50 text-rose-600", green: "bg-emerald-50 text-emerald-600", slate: "bg-slate-100 text-slate-500", amber: "bg-amber-50 text-amber-600" };
  return (
    <div className="border-b border-slate-200 pb-3" data-testid={testId}>
      <div className="mb-2 flex items-center gap-2 text-[11px] font-medium text-slate-400"><span className={`flex h-5 w-5 items-center justify-center rounded ${tones[tone]}`}>{icon}</span><span data-testid={`${testId}-label`}>{label}</span></div>
      <p className="font-mono text-lg font-medium tracking-tight text-slate-900" data-testid={`${testId}-value`}>{value}</p>
    </div>
  );
}