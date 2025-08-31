# ASGI-middleware: mäter verklig latens + status och matar METRICS
from starlette.middleware.base import BaseHTTPMiddleware
from time import perf_counter
from .metrics import METRICS

class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        t0 = perf_counter()
        resp = await call_next(request)
        ms = (perf_counter() - t0) * 1000.0
        # route klass hämtas från svarshuvud satt av din handler, annars infer
        route = resp.headers.get("X-Route") or \
                ("planner" if request.url.path.startswith("/api/orchestrator/ingest") else "other")
        METRICS.observe_latency(route, ms)
        METRICS.observe_status(resp.status_code)
        return resp