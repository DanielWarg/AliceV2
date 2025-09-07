#!/usr/bin/env python3
# Thompson Sampling för route-val (baseline vs adapter)
import random
class BetaBandit:
    def __init__(self, a=1.0, b=1.0):
        self.a=a; self.b=b
    def sample(self): 
        # Python stdlib saknar beta → approximera med Gamma
        import random
        x = random.gammavariate(self.a, 1.0)
        y = random.gammavariate(self.b, 1.0)
        return x/(x+y)
    def update(self, reward): 
        self.a += reward; self.b += 1-reward