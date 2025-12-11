FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY serving /app/serving
COPY ingestion /app/ingestion
COPY feature_repo /app/feature_repo

# Expect model and processed data to be mounted at /app/data
EXPOSE 8000

CMD ["python", "-m", "uvicorn", "serving.main:app", "--host", "0.0.0.0", "--port", "8000"]

