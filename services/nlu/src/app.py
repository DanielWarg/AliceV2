import os
import time

import httpx
import structlog
from fastapi import FastAPI, HTTPException

from .intent_embedder import IntentEmbedder
from .intent_validator import IntentValidator
from .model_registry import NLURegistry
from .schema import ParseRequest, ParseResponse
from .slot_sv import extract_slots_sv

app = FastAPI(title="Alice NLU v1", version="1.0.0")

logger = structlog.get_logger()
registry = NLURegistry()
embedder = IntentEmbedder(registry)
logger.info("Creating IntentValidator")
validator = IntentValidator(registry)
logger.info("IntentValidator created")

# Environment variables
NLU_PORT = int(os.getenv("NLU_PORT", "9002"))
OLLAMA = os.getenv("OLLAMA_HOST", "http://ollama:11434")


@app.get("/health")
async def health():
    return {"ok": True, "service": "nlu", "version": "1.0.0"}


@app.get("/healthz")
async def healthz():
    try:
        # Lightweight ping to Ollama
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{OLLAMA}/api/tags", timeout=1.0)
            r.raise_for_status()
        return {"ok": True, "ollama_ok": True, "service": "nlu", "version": "1.0.0"}
    except Exception as e:
        raise HTTPException(503, f"downstream: {e}")


@app.post("/api/nlu/parse", response_model=ParseResponse)
async def parse(req: ParseRequest):
    t0 = time.perf_counter()

    emb_t0 = time.perf_counter()
    sim = embedder.match_intent(req.text)
    emb_ms = (time.perf_counter() - emb_t0) * 1000

    label = sim.label
    conf = sim.score
    validated = False
    xnli_ms = 0.0

    if not sim.accepted:
        val_t0 = time.perf_counter()
        ok, label2 = validator.validate(req.text, [sim.label, sim.second_label])
        xnli_ms = (time.perf_counter() - val_t0) * 1000
        if ok:
            label = label2
            validated = True

    slots_t0 = time.perf_counter()
    slots = extract_slots_sv(req.text)
    slots_ms = (time.perf_counter() - slots_t0) * 1000

    total_ms = (time.perf_counter() - t0) * 1000
    route_hint = (
        "planner"
        if label.startswith("calendar.") or label.startswith("email.")
        else "micro"
    )

    return ParseResponse(
        v="1",
        lang=req.lang or "sv",
        intent={"label": label, "confidence": conf, "validated": validated},
        slots=slots,
        route_hint=route_hint,
        timings_ms={
            "embed": emb_ms,
            "sim": 0.0,
            "xnli": xnli_ms,
            "slots": slots_ms,
            "total": total_ms,
        },
    )
