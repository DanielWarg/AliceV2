import os
import numpy as np


INTENT_LABELS = {
    "greeting.hello": "hälsa, hej, god morgon, tja",
    "smalltalk.time": "vad är klockan, aktuell tid, nuvarande tid",
    "calendar.create": "boka möte, skapa kalenderhändelse, tid, datum",
    "calendar.move": "flytta möte, ändra tid, omboka",
    "email.send": "skicka e-post, maila, sänd brev",
    "weather.today": "väder idag, prognos idag, temperatur",
    "system.lights": "tända lampor, släcka lampor, ljus i rummet",
    "info.query": "faktafråga, fråga information, sök uppgifter",
}


class NLURegistry:
    def __init__(self):
        # Placeholder: byt till verklig e5-ONNX encoder
        self.intent_labels = INTENT_LABELS
        self.embeddings = {k: self._fake_embed(v) for k, v in self.intent_labels.items()}

    def _fake_embed(self, text: str) -> np.ndarray:
        # Enkel hashbaserad vektor (ersätts av riktig encoder)
        rng = np.random.default_rng(abs(hash(text)) % (2**32))
        v = rng.normal(size=(384,)).astype(np.float32)
        v /= np.linalg.norm(v) + 1e-9
        return v

    def encode(self, text: str) -> np.ndarray:
        return self._fake_embed(text)


