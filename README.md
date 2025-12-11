# PJM LMP Forecasting — Local to Cloud MLOps

Production‑ready pipeline to forecast PJM Locational Marginal Prices (LMP) using XGBoost, logged with MLflow, feature managed via Feast, and served through FastAPI. Runs end‑to‑end locally first, then deploys to AWS EKS via Terraform and Kubernetes.

## Overview

- Ingestion → ETL → Validation → Feature Engineering → Training → Serving (API)
- Local runs produce parquet files under `data/` and a model at `data/models/xgb_rt_lmp.json`.
- Cloud runs switch storage to S3, containerize training/serving, and deploy on EKS.

## Quickstart (Local)

1. Create and activate a virtual environment, then install deps:

```
python -m venv .venv
./.venv/Scripts/Activate.ps1
pip install -r requirements.txt
```

2. Ingest one day of PJM data:

```
python -m ingestion.fetch_pjm_data --test-run
```

3. ETL the latest raw file:

```
$raw = Get-ChildItem .\data\raw | Sort-Object LastWriteTime | Select-Object -Last 1
python -m ingestion.etl_pipeline --raw-path $raw.FullName
```

4. Validate processed data:

```
$proc = Get-ChildItem .\data\processed | Sort-Object LastWriteTime | Select-Object -Last 1
python -m ingestion.validate_data --processed-path $proc.FullName
```

5. Train a small XGBoost model:

```
python -m training.train_xgb --test-run
```

6. Run tests:

```
pytest -q
```

7. Start the API:

```
uvicorn serving.main:app --reload
```

Open `http://127.0.0.1:8000/docs` and verify `GET /health` and `POST /predict`.

## Cloud Deployment (AWS EKS)

1. Switch `.env` to cloud mode:

```
USE_S3=1
```

2. Provision infra:

```
cd infrastructure/terraform
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

3. Build and push images:

```
docker build -t ghcr.io/your-org/pjm-serving:latest -f serving/Dockerfile .
docker build -t ghcr.io/your-org/pjm-training:latest -f training/Dockerfile .
```

4. Deploy to Kubernetes (requires PVC `pjm-data-pvc` mounting `/app/data`):

```
kubectl apply -f infrastructure/k8s/serving.yaml
kubectl apply -f infrastructure/k8s/training-job.yaml
```

Service exposes a LoadBalancer on port 80 forwarded to container port 8000.

## API

- `GET /health` → status check
- `POST /predict` → returns latest LMP prediction using the saved model

## CI

- GitHub Actions at `.github/workflows/ci.yml` runs `pytest` on push/PR.

## Roadmap

- GPU training node group (Spot or On‑Demand)
- VPC peering for data platform integration
- Full Feast integration (offline + online store)
- Glue Catalog + Athena ETL lakehouse
- Argo Workflows for scheduled retraining pipelines
- Canary/blue‑green deployment (ALB weighted routing)
- S3 optimization (partitioning, compaction jobs)
- Prefect or Dagster orchestration layer
- SOC2 logging, IAM hardening, zero‑trust configuration
