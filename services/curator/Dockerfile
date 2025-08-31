FROM python:3.11-slim
WORKDIR /app
COPY services/curator/requirements.txt .
RUN pip install -r requirements.txt --no-cache-dir
COPY services/curator/curate.py curate.py
ENV LOG_DIR=/data/telemetry DATASETS_DIR=/data/datasets
ENTRYPOINT ["python","/app/curate.py"]

