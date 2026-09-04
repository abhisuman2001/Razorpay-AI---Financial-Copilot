import { Shield, TrendingDown, TrendingUp } from "lucide-react";
import type { HealthScore } from "@/lib/types";

interface HealthScoreCardProps {
  healthScore: HealthScore;
}

export default function HealthScoreCard({ healthScore }: HealthScoreCardProps) {
  const statusColors = {
    excellent: "text-emerald-600 bg-emerald-50 border-emerald-200",
    good: "text-emerald-600 bg-emerald-50 border-emerald-200",
    fair: "text-amber-600 bg-amber-50 border-amber-200",
    poor: "text-rose-600 bg-rose-50 border-rose-200",
  };

  const scoreColor = healthScore.overall_score >= 85
    ? "text-emerald-600"
    : healthScore.overall_score >= 70
    ? "text-emerald-600"
    : healthScore.overall_score >= 50
    ? "text-amber-600"
    : "text-rose-600";

  return (
    <div className="rounded-lg border border-slate-200 bg-white" data-testid="health-score-card">
      <div className="border-b border-slate-100 p-5 sm:p-6">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-slate-400" data-testid="health-score-eyebrow">
              Financial Health
            </p>
            <h2 className="mt-2 font-heading text-lg font-bold text-slate-900" data-testid="health-score-title">
              Overall Score
            </h2>
          </div>
          <Shield className="text-slate-300" size={18} />
        </div>

        <div className="mt-6 flex items-end justify-between">
          <div>
            <div className="flex items-baseline gap-2">
              <p className={`font-mono text-4xl font-medium ${scoreColor}`} data-testid="health-score-value">
                {healthScore.overall_score}
              </p>
              <span className="text-slate-400 text-sm">/100</span>
            </div>
            <span
              className={`mt-2 inline-block rounded-full px-2 py-1 text-[9px] font-bold uppercase tracking-wide ${statusColors[healthScore.overall_status]}`}
              data-testid="health-score-status"
            >
              {healthScore.overall_status}
            </span>
          </div>
        </div>

        <p className="mt-4 text-xs text-slate-500" data-testid="health-score-explanation">
          {healthScore.overall_explanation}
        </p>
      </div>

      <div className="divide-y divide-slate-100" data-testid="health-score-components">
        {healthScore.components.map((component) => (
          <div key={component.name} className="p-4" data-testid={`component-${component.name.toLowerCase().replace(/ /g, '-')}`}>
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <p className="text-xs font-medium text-slate-700" data-testid={`component-${component.name.toLowerCase().replace(/ /g, '-')}-name`}>
                  {component.name}
                </p>
                <p className="mt-1 text-[10px] leading-4 text-slate-400" data-testid={`component-${component.name.toLowerCase().replace(/ /g, '-')}-explanation`}>
                  {component.explanation}
                </p>
              </div>
              <div className="ml-3 text-right">
                <p className={`font-mono text-lg font-medium ${component.score >= 70 ? 'text-emerald-600' : component.score >= 50 ? 'text-amber-600' : 'text-rose-600'}`} data-testid={`component-${component.name.toLowerCase().replace(/ /g, '-')}-score`}>
                  {component.score}
                </p>
                <p className="text-[9px] text-slate-400" data-testid={`component-${component.name.toLowerCase().replace(/ /g, '-')}-weight`}>
                  {Math.round(component.weight * 100)}% weight
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="border-t border-slate-100 px-5 py-3 text-[10px] text-slate-400" data-testid="health-score-method">
        {healthScore.calculation_method}
      </div>
    </div>
  );
}
