FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY eval.py .
COPY scenarios.json .

CMD ["python", "eval.py"]
