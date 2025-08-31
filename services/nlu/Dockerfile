FROM python:3.11-slim
WORKDIR /app
COPY services/nlu/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY services/nlu/src /app/src
ENV NLU_LANG=sv
EXPOSE 9002
CMD ["uvicorn","src.app:app","--host","0.0.0.0","--port","9002","--lifespan","on"]

