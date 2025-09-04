FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_NO_CACHE_DIR=off

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY services/nlu/requirements.txt ./requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY services/nlu/src /app/src
ENV NLU_LANG=sv

EXPOSE 9002
HEALTHCHECK --interval=10s --timeout=3s --retries=10 \
    CMD curl -fsS http://localhost:9002/healthz || exit 1

CMD ["uvicorn","src.app:app","--host","0.0.0.0","--port","9002","--lifespan","on"]

