# Metrics aggregator with sliding windows (5-min route latencies + error budget)
from collections import deque, defaultdict
from time import time

WINDOW_S = 300  # 5 min

class SlidingStats:
    def __init__(self):
        # route -> deque[(ts, latency_ms)]
        self.lat = defaultdict(lambda: deque())
        # errors -> deque[(ts, code_class)]
        self.codes = deque()  # store (ts, status_code)

    def observe_latency(self, route: str, ms: float):
        now = time()
        q = self.lat[route]
        q.append((now, ms))
        # trim
        cut = now - WINDOW_S
        while q and q[0][0] < cut:
            q.popleft()

    def observe_status(self, status_code: int):
        now = time()
        self.codes.append((now, status_code))
        cut = now - WINDOW_S
        while self.codes and self.codes[0][0] < cut:
            self.codes.popleft()

    @staticmethod
    def _pxx(vals, p):
        if not vals: return None
        vals = sorted(vals)
        k = int(round((p/100.0)*(len(vals)-1)))
        return vals[max(0, min(k, len(vals)-1))]

    def snapshot(self):
        # latencies
        routes = {}
        for r,q in self.lat.items():
            vs = [ms for(_,ms) in q]
            routes[r] = {
                "count": len(vs),
                "p50_ms": self._pxx(vs, 50) if vs else None,
                "p95_ms": self._pxx(vs, 95) if vs else None,
            }
        # error budget (rates)
        tot = len(self.codes)
        r429 = sum(1 for _,c in self.codes if c == 429)
        r5xx = sum(1 for _,c in self.codes if 500 <= c <= 599)
        return {
            "window_s": WINDOW_S,
            "routes": routes,
            "error_budget": {
                "total": tot,
                "r429": r429,
                "r5xx": r5xx,
                "r429_rate": (r429/tot) if tot else 0.0,
                "r5xx_rate": (r5xx/tot) if tot else 0.0
            }
        }

METRICS = SlidingStats()