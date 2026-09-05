import { AlertCircle, ArrowRight, CircleAlert, DollarSign, Info, XCircle } from "lucide-react";
import { Link } from "react-router-dom";
import type { Alert } from "@/lib/types";

interface AlertsCardProps {
  alerts: Alert[];
}

export default function AlertsCard({ alerts }: AlertsCardProps) {
  const severityConfig = {
    critical: {
      color: "bg-rose-50 text-rose-700 border-rose-200",
      icon: <XCircle size={14} />,
    },
    high: {
      color: "bg-amber-50 text-amber-700 border-amber-200",
      icon: <AlertCircle size={14} />,
    },
    medium: {
      color: "bg-amber-50 text-amber-600 border-amber-200",
      icon: <CircleAlert size={14} />,
    },
    low: {
      color: "bg-emerald-50 text-emerald-700 border-emerald-200",
      icon: <Info size={14} />,
    },
  };

  if (alerts.length === 0) {
    return (
      <div
        className="rounded-lg border border-emerald-200 bg-emerald-50 p-6"
        data-testid="no-alerts-card"
      >
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-emerald-100 text-emerald-600">
            <Info size={20} />
          </div>
          <div>
            <h3
              className="font-heading text-base font-bold text-emerald-900"
              data-testid="no-alerts-title"
            >
              No critical alerts
            </h3>
            <p
              className="mt-1 text-sm text-emerald-700"
              data-testid="no-alerts-message"
            >
              All financial health indicators are within normal ranges.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3" data-testid="alerts-list">
      {alerts.slice(0, 5).map((alert) => {
        const config = severityConfig[alert.severity];

        return (
          <article
            key={alert.id}
            className="rounded-lg border border-slate-200 bg-white p-4 transition-transform hover:-translate-y-0.5 hover:shadow-md"
            data-testid={`alert-${alert.id}`}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1">
                {/* Severity + category badges */}
                <div className="flex items-center gap-2">
                  <span
                    className={`inline-flex items-center gap-1 rounded-full border px-2 py-1 text-[9px] font-bold uppercase tracking-wide ${config.color}`}
                    data-testid={`alert-${alert.id}-severity`}
                  >
                    {config.icon}
                    {alert.severity}
                  </span>
                  <span
                    className="text-[9px] font-semibold uppercase tracking-wide text-slate-400"
                    data-testid={`alert-${alert.id}-category`}
                  >
                    {alert.category}
                  </span>
                </div>

                {/* Title */}
                <h3
                  className="mt-3 font-heading text-sm font-bold text-slate-900"
                  data-testid={`alert-${alert.id}-title`}
                >
                  {alert.title}
                </h3>

                {/* What happened */}
                <div className="mt-3">
                  <p
                    className="text-[9px] font-bold uppercase tracking-wide text-slate-400"
                    data-testid={`alert-${alert.id}-what-happened-label`}
                  >
                    What happened
                  </p>
                  <p
                    className="mt-1 text-xs leading-5 text-slate-600"
                    data-testid={`alert-${alert.id}-what-happened`}
                  >
                    {alert.what_happened}
                  </p>
                </div>

                {/* Why it matters */}
                <div className="mt-2">
                  <p
                    className="text-[9px] font-bold uppercase tracking-wide text-slate-400"
                    data-testid={`alert-${alert.id}-why-it-matters-label`}
                  >
                    Why it matters
                  </p>
                  <p
                    className="mt-1 text-xs leading-5 text-slate-500"
                    data-testid={`alert-${alert.id}-why-it-matters`}
                  >
                    {alert.why_it_matters}
                  </p>
                </div>

                {/* Financial impact + metric */}
                <div className="mt-3 flex items-start gap-4">
                  <div className="flex-1">
                    <p
                      className="text-[9px] font-bold uppercase tracking-wide text-slate-400"
                      data-testid={`alert-${alert.id}-financial-impact-label`}
                    >
                      Financial impact
                    </p>
                    <p
                      className="mt-0.5 text-xs font-medium text-rose-700"
                      data-testid={`alert-${alert.id}-financial-impact`}
                    >
                      {alert.financial_impact}
                    </p>
                  </div>
                  <div className="text-right">
                    <p
                      className="text-[9px] uppercase tracking-wide text-slate-400"
                      data-testid={`alert-${alert.id}-metric-label`}
                    >
                      {alert.metric_label}
                    </p>
                    <p
                      className="mt-0.5 font-mono text-sm font-medium text-slate-900"
                      data-testid={`alert-${alert.id}-metric-value`}
                    >
                      {alert.metric_value}
                    </p>
                  </div>
                </div>

                {/* Recommended action + CTA */}
                <div className="mt-4 border-t border-slate-100 pt-3">
                  <p
                    className="text-[10px] font-semibold uppercase tracking-wide text-rose-600"
                    data-testid={`alert-${alert.id}-action-label`}
                  >
                    Recommended action
                  </p>
                  <p
                    className="mt-1 text-xs text-slate-600"
                    data-testid={`alert-${alert.id}-action`}
                  >
                    {alert.recommended_action}
                  </p>
                  <Link
                    to={alert.cta_path}
                    className="mt-2 inline-flex items-center gap-1.5 rounded-md bg-rose-50 px-3 py-1.5 text-[10px] font-bold text-rose-700 transition-all hover:bg-rose-100 hover:translate-x-0.5"
                    data-testid={`alert-${alert.id}-cta`}
                  >
                    {alert.cta_label}
                    <ArrowRight size={12} />
                  </Link>
                </div>
              </div>
            </div>
          </article>
        );
      })}
    </div>
  );
}
