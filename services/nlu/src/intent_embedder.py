from dataclasses import dataclass
import numpy as np


@dataclass
class SimResult:
    label: str
    score: float
    second_label: str
    second_score: float
    accepted: bool


class IntentEmbedder:
    def __init__(self, registry, sim_thresh: float = 0.62, margin_min: float = 0.06):
        self.registry = registry
        self.sim_thresh = float(sim_thresh)
        self.margin_min = float(margin_min)

    def match_intent(self, text: str) -> SimResult:
        q = self.registry.encode(text)
        labels = list(self.registry.embeddings.keys())
        embs = np.stack([self.registry.embeddings[l] for l in labels], axis=0)
        sims = (embs @ q)  # cos om vektorer är normaliserade
        top_idx = np.argsort(-sims)[:2]
        l1, l2 = labels[top_idx[0]], labels[top_idx[1]]
        s1, s2 = float(sims[top_idx[0]]), float(sims[top_idx[1]])
        margin = s1 - s2
        accept = (s1 >= self.sim_thresh) and (margin >= self.margin_min)
        return SimResult(label=l1, score=s1, second_label=l2, second_score=s2, accepted=accept)


