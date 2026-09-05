import { AlertCircle, ArrowDown, ArrowUp, Info, TrendingUp } from "lucide-react";
import type { ForecastExplanation } from "@/lib/types";

interface ForecastExplanationProps {
  explanation: ForecastExplanation;
}

export default function ForecastExplanationCard({ explanation }: ForecastExplanationProps) {
  const impactIcons = {
    positive: <ArrowUp className="text-emerald-600" size={14} />,
    negative: <ArrowDown className="text-rose-600" size={14} />,
    neutral: <Info className="text-slate-400" size={14} />,
  };

  const impactColors = {
    positive: "text-emerald-700 bg-emerald-50 border-emerald-200",
    negative: "text-rose-700 bg-rose-50 border-rose-200",
    neutral: "text-slate-600 bg-slate-50 border-slate-200",
  };

  return (
    <div className="space-y-5">
      {/* What's Driving This Forecast */}
      <div className="rounded-lg border border-slate-200 bg-white" data-testid="forecast-drivers-card">
        <div className="border-b border-slate-100 p-5 sm:p-6">
          <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-rose-600" data-testid="drivers-eyebrow">
            Forecast Analysis
          </p>
          <h3 className="mt-2 font-heading text-lg font-bold text-slate-900" data-testid="drivers-title">
            What's driving this forecast?
          </h3>
        </div>

        <div className="divide-y divide-slate-100" data-testid="drivers-list">
          {explanation.drivers.map((driver, index) => (
            <div key={`${driver.category}-${index}`} className="p-5" data-testid={`driver-${index}`}>
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-[9px] font-bold uppercase tracking-wide text-slate-400" data-testid={`driver-${index}-category`}>
                      {driver.category}
                    </span>
                    <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[8px] font-bold uppercase ${impactColors[driver.impact]}`} data-testid={`driver-${index}-impact`}>
                      {impactIcons[driver.impact]}
                      {driver.impact}
                    </span>
                  </div>
                  <p className="mt-2 text-sm font-semibold text-slate-900" data-testid={`driver-${index}-label`}>
                    {driver.label}
                  </p>
                  <p className="mt-1 text-xs leading-5 text-slate-500" data-testid={`driver-${index}-explanation`}>
                    {driver.explanation}
                  </p>
                </div>
                <p className="font-mono text-base font-medium text-slate-900" data-testid={`driver-${index}-value`}>
                  {driver.value}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Forecast Confidence */}
      <div className="rounded-lg border border-slate-200 bg-white" data-testid="forecast-confidence-card">
        <div className="border-b border-slate-100 p-5 sm:p-6">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-slate-400" data-testid="confidence-eyebrow">
                Model Quality
              </p>
              <h3 className="mt-2 font-heading text-lg font-bold text-slate-900" data-testid="confidence-title">
                How confident is this forecast?
              </h3>
            </div>
            <TrendingUp className="text-slate-300" size={18} />
          </div>
          <p className="mt-4 text-sm leading-6 text-slate-600" data-testid="confidence-explanation">
            {explanation.confidence_explanation}
          </p>
        </div>

        <div className="p-5 sm:p-6" data-testid="confidence-factors">
          <p className="text-[10px] font-bold uppercase tracking-[0.13em] text-slate-400" data-testid="confidence-factors-label">
            Confidence factors
          </p>
          <ul className="mt-3 space-y-2" data-testid="confidence-factors-list">
            {explanation.confidence_factors.map((factor, index) => (
              <li key={index} className="flex items-start gap-2 text-xs leading-5 text-slate-600" data-testid={`confidence-factor-${index}`}>
                <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-rose-600" />
                {factor}
              </li>
            ))}
          </ul>
        </div>

        <div className="border-t border-slate-100 bg-amber-50 p-5 sm:p-6" data-testid="uncertainty-range">
          <div className="flex items-start gap-3">
            <AlertCircle className="shrink-0 text-amber-600" size={16} />
            <div>
              <p className="text-xs font-bold text-amber-900" data-testid="uncertainty-range-title">
                Understanding the uncertainty range
              </p>
              <p className="mt-2 text-xs leading-5 text-amber-800" data-testid="uncertainty-range-explanation">
                {explanation.uncertainty_range_explanation}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
