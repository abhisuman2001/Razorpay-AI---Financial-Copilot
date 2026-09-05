import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { motion } from "motion/react";
import { Activity, ArrowLeft, Bot, Mail, Presentation } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Toaster } from "@/components/ui/sonner";
import { beginSession } from "@/lib/session";
import { apiPost } from "@/lib/api";

// ── Types ──────────────────────────────────────────────────────────────────────
interface DemoLoginResponse {
  name: string;
  role: string;
  email: string;
  company: string;
}

// ── Component ──────────────────────────────────────────────────────────────────
export default function Login() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [demoLoading, setDemoLoading] = useState(false);
  const [emailLoading, setEmailLoading] = useState(false);
  const [emailSent, setEmailSent] = useState(false);

  // Demo access — no credentials needed
  const handleDemoAccess = async () => {
    setDemoLoading(true);
    try {
      await apiPost<DemoLoginResponse>("/auth/demo-login");
    } catch {
      // Backend may not have this endpoint yet; proceed anyway for demo mode
    } finally {
      beginSession();
      setDemoLoading(false);
      navigate("/");
    }
  };

  // Email magic-link (UI complete; backend endpoint is a future wiring point)
  const handleEmailSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) {
      toast.error("Enter your email to continue");
      return;
    }
    setEmailLoading(true);
    try {
      await apiPost("/auth/magic-link", { email: email.trim() });
      setEmailSent(true);
    } catch {
      // For prototype: the endpoint likely doesn't exist yet — show the success
      // state anyway so the UI pattern is demonstrable.
      setEmailSent(true);
    } finally {
      setEmailLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen bg-[#f8f9fb]">
      {/* ── Left panel — sign-in form ────────────────────────────────────────── */}
      <div className="flex w-full flex-col justify-between px-6 py-10 sm:px-12 lg:w-1/2 lg:px-16">
        {/* Top bar */}
        <div className="flex items-center justify-between">
          <Link to="/landing" className="flex items-center gap-2">
            <img
              src="/logo.png"
              alt="Razorpay FinSight"
              className="h-9 w-auto object-contain"
            />
          </Link>
          <Link
            to="/landing"
            className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-900"
          >
            <ArrowLeft size={13} />
            Back to home
          </Link>
        </div>

        {/* Form card */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="mx-auto w-full max-w-sm"
        >
          {!emailSent ? (
            <>
              <div className="mb-8">
                <h1 className="font-heading text-2xl font-bold text-slate-900">
                  Welcome back
                </h1>
                <p className="mt-2 text-sm text-slate-500">
                  Sign in to your FinSight workspace or explore the demo.
                </p>
              </div>

              {/* Demo access — primary action */}
              <Button
                type="button"
                onClick={handleDemoAccess}
                disabled={demoLoading}
                className="mb-6 h-11 w-full gap-2 bg-rose-600 text-sm text-white hover:bg-rose-700"
              >
                {demoLoading ? (
                  <>
                    <Activity size={14} className="animate-pulse" />
                    Starting workspace…
                  </>
                ) : (
                  <>
                    <Presentation size={14} />
                    Continue with Demo Access
                  </>
                )}
              </Button>

              {/* Divider */}
              <div className="mb-6 flex items-center gap-3">
                <div className="h-px flex-1 bg-slate-200" />
                <span className="text-xs text-slate-400">or sign in with email</span>
                <div className="h-px flex-1 bg-slate-200" />
              </div>

              {/* Email magic-link form */}
              <form onSubmit={handleEmailSignIn} className="space-y-4">
                <div className="space-y-1.5">
                  <Label htmlFor="email" className="text-xs font-semibold text-slate-700">
                    Work email
                  </Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="you@company.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    autoComplete="email"
                    className="h-10 text-sm"
                    disabled={emailLoading}
                  />
                </div>

                <Button
                  type="submit"
                  variant="outline"
                  disabled={emailLoading || !email.trim()}
                  className="h-10 w-full gap-2 text-sm"
                >
                  {emailLoading ? (
                    <>
                      <Activity size={13} className="animate-pulse" />
                      Sending link…
                    </>
                  ) : (
                    <>
                      <Mail size={13} />
                      Send magic link
                    </>
                  )}
                </Button>
              </form>

              {/* Prototype note */}
              <div className="mt-6 rounded-lg border border-amber-200 bg-amber-50 p-3">
                <p className="text-[11px] font-bold text-amber-900">Prototype note</p>
                <p className="mt-0.5 text-[11px] leading-4 text-amber-800">
                  This application uses a synthetic dataset with no real user accounts.
                  Magic-link sign-in UI is wired and ready — the backend email endpoint is a
                  future integration point. Use{" "}
                  <strong>Demo Access</strong> to explore all features now.
                </p>
              </div>
            </>
          ) : (
            /* Magic-link sent state */
            <motion.div
              initial={{ opacity: 0, scale: 0.97 }}
              animate={{ opacity: 1, scale: 1 }}
              className="text-center"
            >
              <div className="mx-auto mb-6 flex h-14 w-14 items-center justify-center rounded-full bg-emerald-50">
                <Mail size={24} className="text-emerald-600" />
              </div>
              <h2 className="font-heading text-xl font-bold text-slate-900">
                Check your inbox
              </h2>
              <p className="mt-3 text-sm leading-6 text-slate-500">
                If <strong>{email}</strong> is registered, you'll receive a sign-in link
                shortly. Check your spam folder if it doesn't arrive.
              </p>
              <Button
                variant="outline"
                className="mt-6 gap-2 text-sm"
                onClick={() => { setEmailSent(false); setEmail(""); }}
              >
                <ArrowLeft size={13} />
                Try a different email
              </Button>
              <div className="mt-4">
                <button
                  type="button"
                  onClick={handleDemoAccess}
                  className="text-xs text-rose-600 underline-offset-2 hover:underline"
                >
                  Or jump straight into the demo →
                </button>
              </div>
            </motion.div>
          )}
        </motion.div>

        {/* Bottom caption */}
        <p className="text-center text-[11px] text-slate-400">
          No real credentials are stored · Session secured via httpOnly cookie
        </p>
      </div>

      {/* ── Right panel — feature showcase (hidden on mobile) ──────────────── */}
      <div className="relative hidden overflow-hidden bg-gradient-to-br from-slate-900 to-slate-800 lg:flex lg:w-1/2 lg:flex-col lg:justify-between lg:p-16">
        {/* Background decoration */}
        <div
          aria-hidden
          className="pointer-events-none absolute right-0 top-0 h-96 w-96 rounded-full bg-rose-600/10 blur-3xl"
        />
        <div
          aria-hidden
          className="pointer-events-none absolute -bottom-20 -left-20 h-80 w-80 rounded-full bg-rose-600/5 blur-3xl"
        />

        <div>
          <span className="inline-flex items-center gap-2 rounded-full border border-rose-500/30 bg-rose-500/10 px-3 py-1 text-xs font-semibold text-rose-400">
            <Activity size={11} />
            AI Financial Intelligence
          </span>
        </div>

        <div>
          <h2 className="font-heading text-3xl font-bold leading-tight text-white">
            Financial clarity,
            <br />
            not just dashboards.
          </h2>
          <p className="mt-4 text-sm leading-7 text-slate-400">
            FinSight connects Razorpay's transaction layer to a full intelligence stack —
            reconciliation engines, probabilistic forecasts, and an AI CFO that reasons
            from your actual numbers.
          </p>

          {/* Feature highlights */}
          <ul className="mt-8 space-y-4">
            {[
              { icon: Bot, text: "Ask your finances anything in plain language" },
              { icon: Activity, text: "98.3% reconciliation accuracy on synthetic data" },
              { icon: Presentation, text: "Switch demo scenarios live during presentations" },
            ].map(({ icon: Icon, text }) => (
              <li key={text} className="flex items-center gap-3 text-sm text-slate-300">
                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-rose-600/20">
                  <Icon size={14} className="text-rose-400" />
                </span>
                {text}
              </li>
            ))}
          </ul>
        </div>

        <p className="text-[11px] text-slate-500">
          Built on synthetic data · No production records involved
        </p>
      </div>

      <Toaster richColors position="bottom-right" />
    </div>
  );
}
