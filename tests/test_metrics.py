"""Tests for metrics middleware."""
from second_brain.api.metrics import MetricsMiddleware


def test_metrics_initial_state():
    # Create with a dummy app
    from unittest.mock import MagicMock
    middleware = MetricsMiddleware(MagicMock())
    metrics = middleware.get_metrics()
    assert metrics["total_requests"] == 0
    assert metrics["error_count"] == 0
    assert metrics["avg_latency_ms"] == 0.0
