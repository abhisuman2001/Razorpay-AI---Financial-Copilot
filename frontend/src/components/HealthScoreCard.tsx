import { useState } from "react";
import { ChevronDown, ChevronUp, Shield, TrendingDown, TrendingUp } from "lucide-react";
import type { HealthScore } from "@/lib/types";

interface HealthScoreCardProps {
  healthScore: HealthScore;
}

export default function HealthScoreCard({ healthScore }: HealthScoreCardProps) {
  const [showCalculation, setShowCalculation] = useState(false);

  const statusColors = {
    excellent: "text-emerald-600 bg-emerald-50 border-emerald-200",
    good: "text-emerald-600 bg-emerald-50 border-emerald-200",
    fair: "text-amber-600 bg-amber-50 border-amber-200",
    poor: "text-rose-600 bg-rose-50 border-rose-200",
  };

  const scoreColor =
    healthScore.overall_score >= 85
      ? "text-emerald-600"
      : healthScore.overall_score >= 70
      ? "text-emerald-600"
      : healthScore.overall_score >= 50
      ? "text-amber-600"
      : "text-rose-600";

  const componentScoreColor = (score: number) =>
    score >= 70
      ? "text-emerald-600"
      : score >= 50
      ? "text-amber-600"
      : "text-rose-600";

  const barColor = (score: number) =>
    score >= 70 ? "bg-emerald-500" : score >= 50 ? "bg-amber-400" : "bg-rose-500";

  return (
    <div className="rounded-lg border border-slate-200 bg-white" data-testid="health-score-card">
      {/* Header */}
      <div className="border-b border-slate-100 p-5 sm:p-6">
        <div className="flex items-start justify-between">
          <div>
            <p
              className="text-[10px] font-bold uppercase tracking-[0.14em] text-slate-400"
              data-testid="health-score-eyebrow"
            >
              Financial Health
            </p>
            <h2
              className="mt-2 font-heading text-lg font-bold text-slate-900"
              data-testid="health-score-title"
            >
              Overall Score
            </h2>
          </div>
          <Shield className="text-slate-300" size={18} />
        </div>

        <div className="mt-6 flex items-end justify-between">
          <div>
            <div className="flex items-baseline gap-2">
              <p
                className={`font-mono text-4xl font-medium ${scoreColor}`}
                data-testid="health-score-value"
              >
                {healthScore.overall_score}
              </p>
              <span className="text-sm text-slate-400">/100</span>
            </div>
            <span
              className={`mt-2 inline-block rounded-full border px-2 py-1 text-[9px] font-bold uppercase tracking-wide ${statusColors[healthScore.overall_status]}`}
              data-testid="health-score-status"
            >
              {healthScore.overall_status}
            </span>
          </div>
        </div>

        <p className="mt-4 text-xs text-slate-500" data-testid="health-score-explanation">
          {healthScore.overall_explanation}
        </p>

        {/* "How is this calculated?" toggle */}
        <button
          type="button"
          onClick={() => setShowCalculation((prev) => !prev)}
          className="mt-4 inline-flex items-center gap-1.5 text-[10px] font-bold text-rose-700 transition-colors hover:text-rose-800"
          data-testid="health-score-calculation-toggle"
          aria-expanded={showCalculation}
        >
          How is this calculated?
          {showCalculation ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
        </button>

        {showCalculation && (
          <div
            className="mt-4 rounded-lg border border-slate-100 bg-slate-50 p-4 text-xs"
            data-testid="health-score-calculation-panel"
          >
            <p className="font-bold text-slate-700">
              Score = weighted sum of {healthScore.components.length} components
            </p>

            {/* Component breakdown table */}
            <div className="mt-3 space-y-2" data-testid="health-score-calculation-components">
              {healthScore.components.map((c) => (
                <div
                  key={c.name}
                  className="flex items-center gap-2"
                  data-testid={`calc-component-${c.name.toLowerCase().replace(/ /g, "-")}`}
                >
                  <span className="w-36 shrink-0 text-[10px] font-medium text-slate-600">
                    {c.name}
                  </span>
                  <div className="flex-1 overflow-hidden rounded-full bg-slate-200 h-1.5">
                    <div
                      className={`h-full rounded-full ${barColor(c.score)}`}
                      style={{ width: `${c.score}%` }}
                    />
                  </div>
                  <span
                    className={`w-8 text-right font-mono text-[10px] font-medium ${componentScoreColor(c.score)}`}
                  >
                    {c.score}
                  </span>
                  <span className="w-10 text-right text-[10px] text-slate-400">
                    ×{Math.round(c.weight * 100)}%
                  </span>
                  <span className="w-10 text-right font-mono text-[10px] font-bold text-slate-700">
                    {c.contribution.toFixed(1)}
                  </span>
                </div>
              ))}
            </div>

            {/* Total */}
            <div className="mt-3 flex items-center justify-between border-t border-slate-200 pt-2">
              <span className="text-[10px] font-bold text-slate-600">Overall score</span>
              <span
                className={`font-mono text-sm font-bold ${scoreColor}`}
                data-testid="calc-overall-total"
              >
                {healthScore.overall_score} / 100
              </span>
            </div>

            {/* Strongest contributors */}
            <div className="mt-3 grid grid-cols-2 gap-2">
              <div
                className="rounded-md border border-emerald-100 bg-emerald-50 p-2"
                data-testid="calc-strongest-positive"
              >
                <div className="flex items-center gap-1 text-emerald-700">
                  <TrendingUp size={11} />
                  <span className="text-[9px] font-bold uppercase tracking-wide">
                    Strongest positive
                  </span>
                </div>
                <p className="mt-1 text-[10px] font-medium text-emerald-800">
                  {healthScore.strongest_positive}
                </p>
              </div>
              <div
                className="rounded-md border border-rose-100 bg-rose-50 p-2"
                data-testid="calc-strongest-negative"
              >
                <div className="flex items-center gap-1 text-rose-700">
                  <TrendingDown size={11} />
                  <span className="text-[9px] font-bold uppercase tracking-wide">
                    Needs most attention
                  </span>
                </div>
                <p className="mt-1 text-[10px] font-medium text-rose-800">
                  {healthScore.strongest_negative}
                </p>
              </div>
            </div>

            <p
              className="mt-3 text-[9px] text-slate-400"
              data-testid="calc-no-llm-note"
            >
              {healthScore.calculation_method} · All values sourced directly from the financial database.
            </p>
          </div>
        )}
      </div>

      {/* Component rows */}
      <div className="divide-y divide-slate-100" data-testid="health-score-components">
        {healthScore.components.map((component) => (
          <div
            key={component.name}
            className="p-4"
            data-testid={`component-${component.name.toLowerCase().replace(/ /g, "-")}`}
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <p
                  className="text-xs font-medium text-slate-700"
                  data-testid={`component-${component.name.toLowerCase().replace(/ /g, "-")}-name`}
                >
                  {component.name}
                </p>
                <p
                  className="mt-1 text-[10px] leading-4 text-slate-400"
                  data-testid={`component-${component.name.toLowerCase().replace(/ /g, "-")}-explanation`}
                >
                  {component.explanation}
                </p>
              </div>
              <div className="ml-3 text-right">
                <p
                  className={`font-mono text-lg font-medium ${componentScoreColor(component.score)}`}
                  data-testid={`component-${component.name.toLowerCase().replace(/ /g, "-")}-score`}
                >
                  {component.score}
                </p>
                <p
                  className="text-[9px] text-slate-400"
                  data-testid={`component-${component.name.toLowerCase().replace(/ /g, "-")}-weight`}
                >
                  {Math.round(component.weight * 100)}% weight
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div
        className="border-t border-slate-100 px-5 py-3 text-[10px] text-slate-400"
        data-testid="health-score-method"
      >
        {healthScore.calculation_method}
      </div>
    </div>
  );
}
