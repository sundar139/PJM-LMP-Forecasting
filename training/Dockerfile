FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY training /app/training
COPY ingestion /app/ingestion
COPY feature_repo /app/feature_repo

# Expect input data mounted at /app/data; outputs written to /app/data/models
CMD ["python", "-m", "training.train_xgb", "--test-run"]

