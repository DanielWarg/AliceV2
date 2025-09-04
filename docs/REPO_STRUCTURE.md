# Repository Structure Policy

Goal: Tight, scalable codebase.

## Approved Top-Level Directories

- `services/` – backend services
- `apps/` – frontend/desktop
- `packages/` – shared packages (api/ui/types)
- `monitoring/` – HUD/observability
- `scripts/` – automation scripts
- `data/` – artifacts/telemetry (non-versioned data)
- `config/` – policies/configuration
- `docs/` – documentation

## Rules

- No binaries in repo. Large files (>10MB) only under `models/`.
- No `node_modules`/`__pycache__`/build output in repo.
- Shared code → `packages/` (public API), not cross-import between services.
- Each service has `Dockerfile`, `requirements.txt/pyproject`, `main.py`, `src/`.
- Test code lies under respective service `src/tests/` or `tests/`.
- All new functionality must have DoD and gate in `ROADMAP.md`.

## Owners

See `.github/CODEOWNERS`.
