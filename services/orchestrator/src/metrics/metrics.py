# Metrics aggregator with sliding windows (5-min route latencies + error budget)
from collections import defaultdict, deque
from time import time

WINDOW_S = 300  # 5 min


class SlidingStats:
    def __init__(self):
        # route -> deque[(ts, latency_ms)]
        self.lat = defaultdict(lambda: deque())
        # errors -> deque[(ts, code_class)]
        self.codes = deque()  # store (ts, status_code)

        # Learning metrics
        self.learn_ingest_total = 0
        self.learn_ingest_errors = 0
        self.learn_snapshot_total = 0
        self.learn_snapshot_errors = 0
        self.learn_forget_total = 0
        self.learn_forget_errors = 0
        self.learn_rows_raw = 0
        self.learn_rows_learnable = 0
        self.learn_hard_intent = 0
        self.learn_tool_fail = 0
        self.learn_rag_miss = 0
        self.learn_snapshot_rows = 0

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
        if not vals:
            return None
        vals = sorted(vals)
        k = int(round((p / 100.0) * (len(vals) - 1)))
        return vals[max(0, min(k, len(vals) - 1))]

    def snapshot(self):
        # latencies
        routes = {}
        for r, q in self.lat.items():
            vs = [ms for (_, ms) in q]
            routes[r] = {
                "count": len(vs),
                "p50_ms": self._pxx(vs, 50) if vs else None,
                "p95_ms": self._pxx(vs, 95) if vs else None,
            }
        # error budget (rates)
        tot = len(self.codes)
        r429 = sum(1 for _, c in self.codes if c == 429)
        r5xx = sum(1 for _, c in self.codes if 500 <= c <= 599)
        return {
            "window_s": WINDOW_S,
            "routes": routes,
            "error_budget": {
                "total": tot,
                "r429": r429,
                "r5xx": r5xx,
                "r429_rate": (r429 / tot) if tot else 0.0,
                "r5xx_rate": (r5xx / tot) if tot else 0.0,
            },
            "learning": {
                "ingest_total": self.learn_ingest_total,
                "ingest_errors": self.learn_ingest_errors,
                "snapshot_total": self.learn_snapshot_total,
                "snapshot_errors": self.learn_snapshot_errors,
                "forget_total": self.learn_forget_total,
                "forget_errors": self.learn_forget_errors,
                "rows_raw": self.learn_rows_raw,
                "rows_learnable": self.learn_rows_learnable,
                "hard_intent": self.learn_hard_intent,
                "tool_fail": self.learn_tool_fail,
                "rag_miss": self.learn_rag_miss,
                "snapshot_rows": self.learn_snapshot_rows,
            },
        }


METRICS = SlidingStats()
