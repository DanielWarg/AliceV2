FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install fastapi uvicorn psutil

# Copy application
COPY main.py .

# Health check
# Healthcheck via curl (endpoint implementerad i app)
HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8787/health || exit 1

# Expose port
EXPOSE 8787

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8787"]