from __future__ import annotations

import logging
import time
from collections import defaultdict

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Track request latency, status codes, and token usage."""

    def __init__(self, app):
        super().__init__(app)
        self.request_count: int = 0
        self.error_count: int = 0
        self.total_latency: float = 0.0
        self.status_counts: dict[int, int] = defaultdict(int)
        self.endpoint_latency: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        self.request_count += 1

        try:
            response = await call_next(request)
        except Exception:
            self.error_count += 1
            raise

        latency = time.perf_counter() - start
        self.total_latency += latency
        self.status_counts[response.status_code] += 1

        path = request.url.path
        self.endpoint_latency[path].append(latency)
        # Keep only last 100 measurements per endpoint
        if len(self.endpoint_latency[path]) > 100:
            self.endpoint_latency[path] = self.endpoint_latency[path][-100:]

        # Log slow requests
        if latency > 5.0:
            logger.warning(
                "Slow request: %s %s took %.2fs", request.method, path, latency
            )

        response.headers["X-Response-Time"] = f"{latency:.4f}"
        return response

    def get_metrics(self) -> dict:
        avg_latency = self.total_latency / max(self.request_count, 1)
        endpoint_stats = {}
        for path, latencies in self.endpoint_latency.items():
            if latencies:
                endpoint_stats[path] = {
                    "count": len(latencies),
                    "avg_ms": round(sum(latencies) / len(latencies) * 1000, 2),
                    "p95_ms": round(
                        sorted(latencies)[int(len(latencies) * 0.95)] * 1000, 2
                    ),
                    "max_ms": round(max(latencies) * 1000, 2),
                }

        return {
            "total_requests": self.request_count,
            "error_count": self.error_count,
            "avg_latency_ms": round(avg_latency * 1000, 2),
            "status_codes": dict(self.status_counts),
            "endpoints": endpoint_stats,
        }
