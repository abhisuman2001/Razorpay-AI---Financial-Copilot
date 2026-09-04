"""
Tests for financial health score and alerts.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from services.alerts import detect_alerts
from services.health_score import calculate_health_score


@pytest.mark.asyncio
async def test_health_score_calculation(session: AsyncSession):
    """Test that health score calculation returns valid results."""
    health_score = await calculate_health_score(session)
    
    assert "overall_score" in health_score
    assert 0 <= health_score["overall_score"] <= 100
    assert health_score["overall_status"] in ["excellent", "good", "fair", "poor"]
    assert len(health_score["components"]) == 6
    
    # Verify all components have required fields
    for component in health_score["components"]:
        assert "name" in component
        assert "score" in component
        assert "weight" in component
        assert "explanation" in component
        assert "status" in component
        assert 0 <= component["score"] <= 100
        assert 0 <= component["weight"] <= 1
    
    # Verify weights sum to 1.0
    total_weight = sum(c["weight"] for c in health_score["components"])
    assert abs(total_weight - 1.0) < 0.01


@pytest.mark.asyncio
async def test_alerts_detection(session: AsyncSession):
    """Test that alerts detection returns valid results."""
    alerts = await detect_alerts(session)
    
    assert isinstance(alerts, list)
    
    # Verify alert structure if any alerts exist
    for alert in alerts:
        assert "id" in alert
        assert "severity" in alert
        assert "category" in alert
        assert "title" in alert
        assert "metric_label" in alert
        assert "metric_value" in alert
        assert "explanation" in alert
        assert "recommended_action" in alert
        assert "detected_at" in alert
        assert "source" in alert
        assert alert["severity"] in ["critical", "high", "medium", "low"]
    
    # Verify alerts are sorted by severity
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    for i in range(len(alerts) - 1):
        assert severity_order[alerts[i]["severity"]] <= severity_order[alerts[i + 1]["severity"]]
