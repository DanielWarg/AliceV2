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
        self.enabled = enabled and (os.getenv("NLU_XNLI_ENABLE", "false").lower() == "true")
        self._sess: Optional["ort.InferenceSession"] = None
        self._tokenizer = None
        self._ent_thresh = float(os.getenv("NLU_XNLI_ENT_THRESH", "0.55"))
        self._init_xnli()

    def _init_xnli(self) -> None:
        if not self.enabled or ort is None:
            return
        path = os.getenv("XNLI_ONNX_PATH")
        if not path or not os.path.exists(path):
            return
        try:
            self._sess = ort.InferenceSession(path, providers=["CPUExecutionProvider"])
        except Exception:
            self._sess = None
        # Tokenizer: prefer local dir if provided
        tok_dir = os.getenv("XNLI_TOKENIZER_DIR")
        try:
            if AutoTokenizer is not None:
                if tok_dir and os.path.exists(tok_dir):
                    self._tokenizer = AutoTokenizer.from_pretrained(tok_dir)
                else:
                    # Fallback: try to fetch by name (requires internet)
                    self._tokenizer = AutoTokenizer.from_pretrained("joeddav/xlm-roberta-large-xnli")
        except Exception:
            self._tokenizer = None

    def _softmax(self, x: np.ndarray) -> np.ndarray:
        x = x - np.max(x, axis=-1, keepdims=True)
        e = np.exp(x)
        return e / (np.sum(e, axis=-1, keepdims=True) + 1e-9)

    def _entailment_prob(self, premise: str, hypothesis: str) -> Optional[float]:
        if self._sess is None or self._tokenizer is None:
            return None
        try:
            enc = self._tokenizer(premise, hypothesis, return_tensors="np", truncation=True, padding=True)
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
        if not self.enabled or self._sess is None or self._tokenizer is None or len(labels) < 1:
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
        # Accept best if entailment prob passes threshold and beats second
        if p1 >= self._ent_thresh and p1 >= p2:
            return True, best_label
        if p2 >= self._ent_thresh and p2 > p1:
            return True, second_label
        return False, best_label


