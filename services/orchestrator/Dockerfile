FROM python:3.11-slim
WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

ENV LOG_DIR=/data/telemetry
EXPOSE 8000

CMD ["uvicorn","main:app","--host","0.0.0.0","--port","8000","--lifespan","on"]

