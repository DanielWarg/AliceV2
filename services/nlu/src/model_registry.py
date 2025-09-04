import os
from typing import Optional

import numpy as np

try:
    import onnxruntime as ort  # type: ignore
except Exception:  # pragma: no cover
    ort = None  # fallback

try:
    from tokenizers import Tokenizer  # type: ignore
except Exception:  # pragma: no cover
    Tokenizer = None  # type: ignore


INTENT_LABELS = {
    "greeting.hello": "hälsa, hej, god morgon, tja, hallå",
    "smalltalk.time": "vad är klockan, aktuell tid, nuvarande tid, vilken tid",
    "calendar.create": "boka möte, skapa kalenderhändelse, tid, datum, schedule meeting, book appointment",
    "calendar.move": "flytta möte, ändra tid, omboka, reschedule, change appointment",
    "email.send": "skicka e-post, maila, sänd brev, send email",
    "weather.today": "väder idag, prognos idag, temperatur, weather today",
    "system.lights": "tända lampor, släcka lampor, ljus i rummet, lights on, lights off",
    "info.query": "faktafråga, fråga information, sök uppgifter, what is, how to",
}


class NLURegistry:
    def __init__(self):
        self.intent_labels = INTENT_LABELS
        # Optional ONNX encoder setup
        self._encoder = self._init_onnx_encoder()
        # Precompute label embeddings
        self.embeddings = {
            k: self._encode_label(v) for k, v in self.intent_labels.items()
        }

    def _fake_embed(self, text: str) -> np.ndarray:
        # Förbättrad hashbaserad vektor med keyword-matching
        text_lower = text.lower()

        # Keyword weights för bättre intent-matching
        keywords = {
            "calendar.create": [
                "möte",
                "meeting",
                "boka",
                "book",
                "schedule",
                "appointment",
                "tid",
                "time",
                "datum",
                "date",
            ],
            "calendar.move": [
                "flytta",
                "move",
                "ändra",
                "change",
                "omboka",
                "reschedule",
            ],
            "email.send": [
                "e-post",
                "email",
                "mail",
                "skicka",
                "send",
                "brev",
                "letter",
            ],
            "weather.today": [
                "väder",
                "weather",
                "temperatur",
                "temperature",
                "prognos",
                "forecast",
                "vad är vädret",
                "vädret idag",
                "vad är vädret idag",
                "vad är vädret idag",
            ],
            "system.lights": [
                "lampa",
                "light",
                "tända",
                "turn on",
                "släcka",
                "turn off",
                "ljus",
            ],
            "greeting.hello": [
                "hej",
                "hello",
                "hälsa",
                "god morgon",
                "good morning",
                "tja",
                "hi",
            ],
            "smalltalk.time": [
                "klockan",
                "clock",
                "tid",
                "time",
                "nu",
                "now",
                "aktuell",
                "current",
                "vad är klockan",
                "hur mycket är klockan",
            ],
            "info.query": [
                "vad är",
                "what is",
                "hur",
                "how",
                "när",
                "when",
                "var",
                "where",
                "vem",
                "who",
            ],
        }

        # Beräkna intent-vektor baserat på keywords med längre fraser först
        intent_scores = np.zeros(len(self.intent_labels))
        for i, (intent, keywords_list) in enumerate(keywords.items()):
            score = 0
            # Sortera keywords efter längd (längre först) för bättre matching
            sorted_keywords = sorted(keywords_list, key=len, reverse=True)
            for keyword in sorted_keywords:
                if keyword in text_lower:
                    # Ge högre vikt till längre keywords
                    score += len(keyword) * 0.1
            intent_scores[i] = score

        # Normalisera och konvertera till embedding
        if np.sum(intent_scores) > 0:
            intent_scores = intent_scores / np.sum(intent_scores)
        else:
            intent_scores = np.ones(len(intent_scores)) / len(intent_scores)

        # Skapa 384-dimensionell vektor (paddar med hash-baserad data)
        v = np.zeros(384, dtype=np.float32)
        v[: len(intent_scores)] = intent_scores

        # Fyll resten med hash-baserad data för variation
        rng = np.random.default_rng(abs(hash(text)) % (2**32))
        v[len(intent_scores) :] = rng.normal(size=(384 - len(intent_scores))).astype(
            np.float32
        )

        v /= np.linalg.norm(v) + 1e-9
        return v

    def _init_onnx_encoder(self):
        """Init multilingual-e5-small ONNX session om tillgänglig via env.
        Env:
          E5_ONNX_PATH: sökväg till onnx-modell
          E5_TOKENIZER_JSON: sökväg till tokenizer.json
        """
        onnx_path = os.getenv("E5_ONNX_PATH")
        tok_path = os.getenv("E5_TOKENIZER_JSON")
        if not onnx_path or not os.path.exists(onnx_path):
            return None
        if ort is None:
            return None
        try:
            sess = ort.InferenceSession(onnx_path, providers=["CPUExecutionProvider"])
            tok = None
            if tok_path and os.path.exists(tok_path) and Tokenizer is not None:
                tok = Tokenizer.from_file(tok_path)
            return {"session": sess, "tokenizer": tok}
        except Exception:
            return None

    def _encode_text(self, text: str, prefix: str | None = None) -> np.ndarray:
        """Encode text with ONNX encoder if available, otherwise fake embedding."""
        if prefix:
            text = f"{prefix} {text}".strip()
        if not self._encoder:
            return self._fake_embed(text)
        sess = self._encoder["session"]
        tok: Optional[Tokenizer] = self._encoder.get("tokenizer")
        try:
            if tok is None:
                # Minimal whitespace tokens → ids = hash-based fallback
                return self._fake_embed(text)
            enc = tok.encode(text)
            input_ids = np.array([enc.ids], dtype=np.int64)
            attention_mask = np.ones_like(input_ids, dtype=np.int64)
            # Common E5 ONNX inputs (may vary per export)
            inputs = {
                "input_ids": input_ids,
                "attention_mask": attention_mask,
            }
            # Some exports use token_type_ids
            if any(n.name == "token_type_ids" for n in sess.get_inputs()):
                inputs["token_type_ids"] = np.zeros_like(input_ids, dtype=np.int64)
            outs = sess.run(None, inputs)
            # Use first output; mean-pool if sequence
            out = outs[0]
            vec = out[0]
            if vec.ndim == 2:  # [seq, hidden]
                vec = vec.mean(axis=0)
            vec = vec.astype(np.float32)
            norm = np.linalg.norm(vec) + 1e-9
            return vec / norm
        except Exception:
            return self._fake_embed(text)

    def encode(self, text: str) -> np.ndarray:
        # E5 queries preprended with "query:"
        return self._encode_text(text, prefix="query:")

    def _encode_label(self, text: str) -> np.ndarray:
        # E5 passages (labels) preprended with "passage:"
        return self._encode_text(text, prefix="passage:")
