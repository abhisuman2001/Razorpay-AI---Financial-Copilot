from models.why import DriverFinding


def render_why_explanation(
    metric_label: str,
    current_display: str,
    previous_display: str,
    direction: str,
    change_summary: str,
    drivers: list[DriverFinding],
    classification: str,
) -> str:
    """Render only supplied findings; this layer performs no financial calculation."""
    prefix = "Prediction" if classification == "prediction" else "Fact"
    opening = (
        f"{prefix}: {metric_label} {direction} by {change_summary} to {current_display} "
        f"from {previous_display}."
    )
    if not drivers:
        return f"{opening} There is not enough structured data to identify material contributors."
    contributor_text = "; ".join(
        f"{driver.label} {driver.direction} by {driver.change_summary}"
        for driver in drivers
    )
    return (
        f"{opening} The strongest calculated contributors are: {contributor_text}. "
        "These are deterministic data relationships; they are not presented as unproven causes."
    )