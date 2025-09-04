import os
from typing import Optional

import numpy as np

try:
    import onnxruntime as ort  # type: ignore
except Exception:  # pragma: no cover
    ort = None

try:
    from transformers import AutoTokenizer  # type: ignore
except Exception:  # pragma: no cover
    AutoTokenizer = None  # type: ignore


class IntentValidator:
    def __init__(self, registry, enabled: bool = True):
        self.registry = registry
        self.enabled = enabled and (
            os.getenv("NLU_XNLI_ENABLE", "false").lower() == "true"
        )
        self._sess: Optional["ort.InferenceSession"] = None
        self._tokenizer = None
        self._ent_thresh = float(os.getenv("NLU_XNLI_ENT_THRESH", "0.3"))
        print(f"XNLI INIT: enabled={self.enabled}, ort={ort is not None}")
        self._init_xnli()
        print(
            f"XNLI INIT DONE: sess={self._sess is not None}, tokenizer={self._tokenizer}"
        )
        # Force keyword fallback for now (skip transformers issues)
        self._tokenizer = "keyword_fallback"
        print(f"XNLI FORCE KEYWORD: tokenizer={self._tokenizer}")

    def _init_xnli(self) -> None:
        if not self.enabled:
            return
        # Try ONNX first
        path = os.getenv("XNLI_ONNX_PATH")
        if path and os.path.exists(path) and ort is not None:
            try:
                self._sess = ort.InferenceSession(
                    path, providers=["CPUExecutionProvider"]
                )
            except Exception:
                self._sess = None

        # Skip transformers due to XLM-RoBERTa tokenizer issues
        # Go directly to keyword fallback for reliable validation
        if self._sess is None:
            self._tokenizer = "keyword_fallback"
            print(f"XNLI INIT: Using keyword fallback, tokenizer={self._tokenizer}")

    def _softmax(self, x: np.ndarray) -> np.ndarray:
        x = x - np.max(x, axis=-1, keepdims=True)
        e = np.exp(x)
        return e / (np.sum(e, axis=-1, keepdims=True) + 1e-9)

    def _entailment_prob(self, premise: str, hypothesis: str) -> Optional[float]:
        if self._tokenizer is None:
            return None

        # Keyword fallback
        if self._tokenizer == "keyword_fallback":
            premise_lower = premise.lower()
            hypothesis_lower = hypothesis.lower()

            # Enhanced keyword matching for Swedish
            weather_keywords = [
                "väder",
                "weather",
                "temperatur",
                "temperature",
                "prognos",
                "forecast",
                "vädret",
                "vad är vädret",
            ]
            time_keywords = [
                "klockan",
                "tid",
                "datum",
                "time",
                "date",
                "när",
                "when",
                "hur mycket är klockan",
            ]
            calendar_keywords = [
                "boka",
                "skapa",
                "kalender",
                "calendar",
                "möte",
                "meeting",
                "event",
            ]
            email_keywords = [
                "mail",
                "email",
                "e-post",
                "skicka",
                "send",
                "meddelande",
                "message",
            ]
            memory_keywords = [
                "kom ihåg",
                "remember",
                "minne",
                "memory",
                "spara",
                "save",
                "glöm",
                "forget",
            ]

            # Weather intent
            if any(kw in premise_lower for kw in weather_keywords):
                if any(kw in hypothesis_lower for kw in weather_keywords):
                    return 0.9  # Very high confidence for weather match
                elif any(kw in hypothesis_lower for kw in time_keywords):
                    return 0.1  # Very low confidence for time mismatch
                else:
                    return 0.3  # Low confidence for other intents

            # Time intent
            if any(kw in premise_lower for kw in time_keywords):
                if any(kw in hypothesis_lower for kw in time_keywords):
                    return 0.9  # Very high confidence for time match
                elif any(kw in hypothesis_lower for kw in weather_keywords):
                    return 0.1  # Very low confidence for weather mismatch
                else:
                    return 0.3  # Low confidence for other intents

            # Calendar intent
            if any(kw in premise_lower for kw in calendar_keywords):
                if any(kw in hypothesis_lower for kw in calendar_keywords):
                    return 0.9  # Very high confidence for calendar match
                else:
                    return 0.2  # Low confidence for other intents

            # Email intent
            if any(kw in premise_lower for kw in email_keywords):
                if any(kw in hypothesis_lower for kw in email_keywords):
                    return 0.9  # Very high confidence for email match
                else:
                    return 0.2  # Low confidence for other intents

            # Memory intent
            if any(kw in premise_lower for kw in memory_keywords):
                if any(kw in hypothesis_lower for kw in memory_keywords):
                    return 0.9  # Very high confidence for memory match
                else:
                    return 0.2  # Low confidence for other intents

            return 0.4  # Neutral confidence for unknown intents
        try:
            enc = self._tokenizer(
                premise, hypothesis, return_tensors="np", truncation=True, padding=True
            )
            inputs = {
                "input_ids": enc["input_ids"].astype(np.int64),
                "attention_mask": enc["attention_mask"].astype(np.int64),
            }
            # Some models may accept token_type_ids
            if "token_type_ids" in enc:
                inputs["token_type_ids"] = enc["token_type_ids"].astype(np.int64)
            outs = self._sess.run(None, inputs)
            logits = outs[0][0]  # shape (3,) -> [contradiction, neutral, entailment]
            probs = self._softmax(logits)
            entail_prob = float(probs[2]) if probs.shape[-1] >= 3 else float(probs[-1])
            return entail_prob
        except Exception:
            return None

    def validate(self, text: str, labels: list[str]) -> tuple[bool, str]:
        print(
            f"XNLI VALIDATE: enabled={self.enabled}, sess={self._sess is not None}, tokenizer={self._tokenizer is not None}, labels={labels}"
        )
        if (
            not self.enabled
            or self._sess is None
            or self._tokenizer is None
            or len(labels) < 1
        ):
            print("XNLI VALIDATE: Early return - missing components")
            return False, labels[0] if labels else "info.query"
        # Use Swedish descriptions from registry as hypotheses
        label_to_desc = getattr(self.registry, "intent_labels", {}) or {}
        # Score top-1; if provided, also check second best
        best_label = labels[0]
        second_label = labels[1] if len(labels) > 1 else labels[0]
        hyp1 = label_to_desc.get(best_label, best_label)
        hyp2 = label_to_desc.get(second_label, second_label)
        p1 = self._entailment_prob(text, hyp1) or 0.0
        p2 = self._entailment_prob(text, hyp2) or 0.0
        # Debug: print entailment probabilities
        print(
            f"XNLI DEBUG: text='{text}', best='{best_label}' (p1={p1:.3f}), second='{second_label}' (p2={p2:.3f}), thresh={self._ent_thresh}"
        )
        # Accept best if entailment prob passes threshold and beats second
        if p1 >= self._ent_thresh and p1 >= p2:
            return True, best_label
        if p2 >= self._ent_thresh and p2 > p1:
            return True, second_label
        return False, best_label
