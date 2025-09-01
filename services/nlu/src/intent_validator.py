import os
from typing import Optional

try:
    import onnxruntime as ort  # type: ignore
except Exception:  # pragma: no cover
    ort = None


class IntentValidator:
    def __init__(self, registry, enabled: bool = True):
        self.registry = registry
        self.enabled = enabled and (os.getenv("NLU_XNLI_ENABLE", "true").lower() == "true")
        self._sess = self._init_xnli()

    def _init_xnli(self):
        path = os.getenv("XNLI_ONNX_PATH")
        if not self.enabled or not path or not os.path.exists(path) or ort is None:
            return None
        try:
            return ort.InferenceSession(path, providers=["CPUExecutionProvider"])
        except Exception:
            return None

    def validate(self, text: str, labels: list[str]) -> tuple[bool, str]:
        if not self.enabled or self._sess is None or len(labels) < 2:
            return False, labels[0] if labels else "info.query"
        # Minimal entailment stub: om ONNX finns, föredra topp-1 för nu
        # (Riktig implementering skulle tokenisera (premise=text, hypothesis=label_desc)
        #  och läsa 'entailment' logit; här returnerar vi topp-1 för enkel P95.)
        return True, labels[0]


