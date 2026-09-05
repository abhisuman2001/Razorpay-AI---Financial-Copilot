import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "motion/react";
import {
  Activity,
  ArrowRight,
  Bot,
  ChartNoAxesCombined,
  CheckCircle2,
  DatabaseZap,
  ListChecks,
  LayoutDashboard,
  Presentation,
  Shield,
  Sparkles,
  Zap,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { beginSession } from "@/lib/session";
import { apiPost } from "@/lib/api";
import { Toaster } from "@/components/ui/sonner";

// ── Types ──────────────────────────────────────────────────────────────────────
interface DemoLoginResponse {
  name: string;
  role: string;
  email: string;
  company: string;
}

// ── Feature cards ──────────────────────────────────────────────────────────────
const features = [
  {
    icon: LayoutDashboard,
    title: "Executive Dashboard",
    description:
      "Real-time KPIs, cash balance, revenue trends, and AI-generated financial health scores in one glance.",
    accent: "bg-rose-50 text-rose-600",
  },
  {
    icon: ListChecks,
    title: "Smart Reconciliation",
    description:
      "Automatically match payments to settlements, flag mismatches, and surface exceptions with full audit trails.",
    accent: "bg-blue-50 text-blue-600",
  },
  {
    icon: ChartNoAxesCombined,
    title: "Cash Flow Forecasting",
    description:
      "7, 30, and 90-day probabilistic forecasts with confidence bands, risk flags, and driver analysis.",
    accent: "bg-emerald-50 text-emerald-600",
  },
  {
    icon: Bot,
    title: "AI CFO Copilot",
    description:
      "Ask natural-language questions about your finances. Get deterministic, source-cited answers backed by your actual data.",
    accent: "bg-amber-50 text-amber-700",
  },
  {
    icon: DatabaseZap,
    title: "Connect Sources",
    description:
      "Import bank statements, payment gateway exports, and accounting ledgers. Normalize and reconcile in minutes.",
    accent: "bg-violet-50 text-violet-600",
  },
  {
    icon: Shield,
    title: "Audit-ready",
    description:
      "Every calculation is traceable to source records. Export reconciliation reports with a single click.",
    accent: "bg-slate-100 text-slate-600",
  },
];

// ── Stat strip ─────────────────────────────────────────────────────────────────
const stats = [
  { value: "₹2.4Cr+", label: "Transactions analyzed" },
  { value: "98.3%", label: "Reconciliation accuracy" },
  { value: "<2s", label: "Dashboard load time" },
  { value: "7–90d", label: "Forecast horizon" },
];

// ── Main component ─────────────────────────────────────────────────────────────
export default function Landing() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);

  const handleDemoAccess = async () => {
    setLoading(true);
    try {
      // Attempt to call the demo-login endpoint. If backend isn't wired yet,
      // the finally block still proceeds — session cookie is optional for demo mode.
      await apiPost<DemoLoginResponse>("/auth/demo-login");
    } catch {
      // Backend endpoint may not exist yet; proceed to app anyway for prototype.
    } finally {
      beginSession();
      setLoading(false);
      navigate("/");
    }
  };

  const handleSignIn = () => {
    navigate("/login");
  };

  return (
    <div className="min-h-screen bg-[#f8f9fb] text-slate-900">
      {/* ── Nav ─────────────────────────────────────────────────────────────── */}
      <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/95 backdrop-blur-sm">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-5 sm:px-8">
          <div className="flex items-center gap-2">
            <img
              src="/logo.png"
              alt="Razorpay FinSight"
              className="h-20 w-auto object-contain"
            />
          </div>
          <div className="flex items-center gap-3">
            <Button
              variant="ghost"
              className="text-slate-600 hover:text-slate-900"
              onClick={handleSignIn}
            >
              Sign in
            </Button>
            <Button
              onClick={handleDemoAccess}
              disabled={loading}
              className="bg-rose-600 text-white hover:bg-rose-700"
            >
              {loading ? (
                <span className="flex items-center gap-2">
                  <Activity size={14} className="animate-pulse" />
                  Starting…
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  <Presentation size={14} />
                  Try Demo
                </span>
              )}
            </Button>
          </div>
        </div>
      </header>

      {/* ── Hero ────────────────────────────────────────────────────────────── */}
      <section className="relative overflow-hidden px-5 pb-24 pt-20 sm:px-8 sm:pt-28">
        {/* Subtle background gradient */}
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 -z-10 bg-gradient-to-br from-rose-50/60 via-transparent to-blue-50/40"
        />
        <div
          aria-hidden
          className="pointer-events-none absolute -right-32 -top-32 h-[500px] w-[500px] rounded-full bg-rose-100/30 blur-3xl"
        />

        <div className="mx-auto max-w-4xl text-center">
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            <span className="mb-6 inline-flex items-center gap-2 rounded-full border border-rose-200 bg-rose-50 px-4 py-1.5 text-xs font-semibold text-rose-700">
              <Sparkles size={12} />
              AI-powered Financial Intelligence for Razorpay merchants
            </span>

            <h1 className="font-heading text-4xl font-bold tracking-tight text-slate-900 sm:text-5xl lg:text-6xl">
              Your finances,{" "}
              <span className="text-rose-600">understood</span>{" "}
              in real time
            </h1>

            <p className="mx-auto mt-6 max-w-2xl text-lg leading-8 text-slate-500">
              FinSight connects your Razorpay data to a full financial intelligence layer —
              reconciliation, cash flow forecasting, anomaly detection, and an AI CFO
              that answers in plain language.
            </p>

            <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
              <Button
                size="lg"
                onClick={handleDemoAccess}
                disabled={loading}
                className="h-12 gap-2 bg-rose-600 px-8 text-base text-white hover:bg-rose-700"
              >
                {loading ? "Starting demo…" : "Explore Demo Workspace"}
                {!loading && <ArrowRight size={16} />}
              </Button>
              <Button
                size="lg"
                variant="outline"
                onClick={handleSignIn}
                className="h-12 gap-2 px-8 text-base"
              >
                Sign in to your account
              </Button>
            </div>

            <p className="mt-5 text-xs text-slate-400">
              No credit card required · Synthetic data · Safe to explore
            </p>
          </motion.div>
        </div>
      </section>

      {/* ── Stats strip ─────────────────────────────────────────────────────── */}
      <section className="border-y border-slate-200 bg-white py-10">
        <div className="mx-auto grid max-w-4xl grid-cols-2 gap-8 px-5 sm:grid-cols-4 sm:px-8">
          {stats.map((s) => (
            <motion.div
              key={s.label}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.1 }}
              className="text-center"
            >
              <p className="font-heading text-2xl font-bold text-slate-900">{s.value}</p>
              <p className="mt-1 text-xs text-slate-500">{s.label}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* ── Features ────────────────────────────────────────────────────────── */}
      <section className="px-5 py-24 sm:px-8">
        <div className="mx-auto max-w-6xl">
          <div className="mb-14 text-center">
            <h2 className="font-heading text-3xl font-bold text-slate-900 sm:text-4xl">
              Everything a finance team needs
            </h2>
            <p className="mt-4 text-slate-500">
              Built on top of your Razorpay transaction data — no manual exports.
            </p>
          </div>

          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {features.map((feature, i) => (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: i * 0.07 }}
                className="rounded-xl border border-slate-200 bg-white p-6 transition-shadow hover:shadow-md"
              >
                <div className={`mb-4 inline-flex h-10 w-10 items-center justify-center rounded-lg ${feature.accent}`}>
                  <feature.icon size={18} />
                </div>
                <h3 className="font-heading text-sm font-bold text-slate-900">{feature.title}</h3>
                <p className="mt-2 text-sm leading-6 text-slate-500">{feature.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Demo CTA banner ──────────────────────────────────────────────────── */}
      <section className="px-5 pb-24 sm:px-8">
        <div className="mx-auto max-w-3xl overflow-hidden rounded-2xl bg-gradient-to-br from-rose-600 to-rose-700 px-8 py-12 text-center shadow-xl shadow-rose-200">
          <Zap size={28} className="mx-auto mb-4 text-rose-200" />
          <h2 className="font-heading text-2xl font-bold text-white sm:text-3xl">
            Ready to see it in action?
          </h2>
          <p className="mt-3 text-sm leading-7 text-rose-100">
            The demo workspace runs on a fully synthetic Razorpay dataset —
            real calculations, real insights, zero production risk.
          </p>
          <div className="mt-8 flex flex-col items-center justify-center gap-4 sm:flex-row">
            <Button
              size="lg"
              onClick={handleDemoAccess}
              disabled={loading}
              className="h-12 gap-2 bg-white px-8 text-base font-bold text-rose-700 hover:bg-rose-50"
            >
              <Presentation size={16} />
              {loading ? "Starting…" : "Launch Demo"}
            </Button>
            <Button
              size="lg"
              variant="ghost"
              onClick={handleSignIn}
              className="h-12 gap-2 px-8 text-base text-white hover:bg-rose-500 hover:text-white"
            >
              Sign in instead
              <ArrowRight size={16} />
            </Button>
          </div>
        </div>
      </section>

      {/* ── Trust footer ─────────────────────────────────────────────────────── */}
      <footer className="border-t border-slate-200 bg-white px-5 py-10 sm:px-8">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-6 text-xs text-slate-400 sm:flex-row">
          <div className="flex items-center gap-2">
            <img src="/logo.png" alt="Razorpay FinSight" className="h-15 w-auto opacity-70" />
          </div>
          <div className="flex flex-wrap items-center justify-center gap-5">
            {[
              { icon: Shield, text: "httpOnly session cookies" },
              { icon: CheckCircle2, text: "No production data stored" },
              { icon: Activity, text: "Synthetic dataset only" },
            ].map(({ icon: Icon, text }) => (
              <span key={text} className="flex items-center gap-1.5">
                <Icon size={12} className="text-emerald-500" />
                {text}
              </span>
            ))}
          </div>
          <p>© {new Date().getFullYear()} Razorpay FinSight · Demo prototype</p>
        </div>
      </footer>

      <Toaster richColors position="bottom-right" />
    </div>
  );
}
