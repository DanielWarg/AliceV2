#!/usr/bin/env python3
# Enkel Bradley–Terry fit med iterativ uppdatering för A/B/C-par
def bradley_terry(pairs, iters=50, lr=0.1):
    # pairs: [{"winner":"A","loser":"B"}, ...]
    import collections
    import math

    skills = collections.defaultdict(float)
    for _ in range(iters):
        for p in pairs:
            wa, wb = skills[p["winner"]], skills[p["loser"]]
            pa = 1.0 / (1.0 + math.exp(wb - wa))
            # gradient ascent
            skills[p["winner"]] += lr * (1 - pa)
            skills[p["loser"]] -= lr * (1 - pa)
    return dict(skills)
