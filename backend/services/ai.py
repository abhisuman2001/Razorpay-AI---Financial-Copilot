from models.financial import CfoResponse, ForecastResponse, Insight, ReconciliationSummary


class StaticInsightGenerator:
    """Deterministic insight provider; designed to be replaced by an Ollama adapter."""

    def generate(self, reconciliation: ReconciliationSummary, forecast: ForecastResponse) -> CfoResponse:
        insights = [
            Insight(
                id="exception-review",
                priority="high",
                title="Review payment exceptions first",
                body=f"{reconciliation.exception_count} transactions need attention, representing ₹{reconciliation.exception_value:,.0f} in variance.",
                metric_label="Exception value",
                metric_value=f"₹{reconciliation.exception_value:,.0f}",
                action="Open reconciliation queue",
                source="Deterministic reconciliation rules",
            ),
            Insight(
                id="cash-outlook",
                priority="medium",
                title="Cash position is trending upward",
                body=f"The six-week model points to ₹{forecast.ending_cash:,.0f} in ending cash, a {forecast.change_percent:.1f}% change from today.",
                metric_label="6-week outlook",
                metric_value=f"₹{forecast.ending_cash:,.0f}",
                action="Review forecast assumptions",
                source="Holt trend forecast",
            ),
            Insight(
                id="operating-rhythm",
                priority="low",
                title="Keep a weekly cash review rhythm",
                body="A short weekly review of settlements, vendor outflows, and open exceptions will keep the forecast explainable.",
                metric_label="Recommended cadence",
                metric_value="Weekly",
                action="Add to operating checklist",
                source="CFO operating guidance",
            ),
        ]
        return CfoResponse(
            generated_by="Razorpay AI rules engine",
            disclaimer="Prototype insights are based on synthetic data and deterministic calculations. No LLM or paid API is connected.",
            insights=insights,
        )