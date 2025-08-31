class IntentValidator:
    def __init__(self, registry, enabled: bool = True):
        self.registry = registry
        self.enabled = enabled

    def validate(self, text: str, labels: list[str]) -> tuple[bool, str]:
        if not self.enabled or len(labels) < 2:
            return False, labels[0] if labels else "info.query"
        # Placeholder: här kör vi egentligen XNLI ONNX med entailment-score
        # Heuristik: välj första etiketten
        return True, labels[0]


