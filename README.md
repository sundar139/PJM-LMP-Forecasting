PJM LMP Forecasting — Local to Cloud MLOps

Forecast PJM locational marginal prices (LMP) with an end‑to‑end pipeline that runs locally and scales to AWS. The stack includes XGBoost, MLflow, Feast, FastAPI, Terraform, and Kubernetes.

## Features

- Complete workflow: ingestion, ETL, validation, feature engineering, training, serving
- Modern MLOps: XGBoost modeling, MLflow experiment tracking, Feast feature store
- Local → Cloud: parquet outputs under `data/`, S3 in cloud mode, deployable to EKS
- CI ready: automated tests via GitHub Actions

## Repository Layout

- `ingestion/` – data fetch, ETL, validation
- `training/` – model training and MLflow logging
- `serving/` – FastAPI app and runtime
- `feature_repo/` – Feast feature definitions/config
- `infrastructure/k8s/` – Kubernetes manifests (serving, training job)
- `infrastructure/terraform/` – Terraform modules for VPC/EKS/S3/etc.
- `data/` – local artifacts (`raw`, `processed`, `features`, `models`)

## Prerequisites

- Python 3.10+
- Docker (for container builds)
- AWS CLI and permissions for EKS/ECR/S3/IAM
- Terraform CLI and `kubectl`

## Quickstart (Local)

1. Create a virtual environment and install dependencies:

```
python -m venv .venv
./.venv/Scripts/Activate.ps1
pip install -r requirements.txt
```

2. Download raw PJM data (one‑day test run):

```
python -m ingestion.fetch_pjm_data --test-run
```

3. Run ETL on the latest raw file:

```
$raw = Get-ChildItem .\data\raw | Sort-Object LastWriteTime | Select-Object -Last 1
python -m ingestion.etl_pipeline --raw-path $raw.FullName
```

4. Validate processed data:

```
$proc = Get-ChildItem .\data\processed | Sort-Object LastWriteTime | Select-Object -Last 1
python -m ingestion.validate_data --processed-path $proc.FullName
```

5. Train an XGBoost model (small test run):

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

Open `http://127.0.0.1:8000/docs` to view `GET /health` and `POST /predict`.

## Cloud Deployment (AWS EKS)

1. Enable cloud mode in `.env`:

```
USE_S3=1
```

2. Provision infrastructure:

```
cd infrastructure/terraform
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

3. Build container images:

```
docker build -t ghcr.io/your-org/pjm-serving:latest -f serving/Dockerfile .
docker build -t ghcr.io/your-org/pjm-training:latest -f training/Dockerfile .
```

4. Deploy to Kubernetes (PVC `pjm-data-pvc` mounted at `/app/data`):

```
kubectl apply -f infrastructure/k8s/serving.yaml
kubectl apply -f infrastructure/k8s/training-job.yaml
```

The service exposes a LoadBalancer on port `80` forwarding to container port `8000`.

## API

- `GET /health` – basic status
- `POST /predict` – returns the latest LMP prediction

## Testing and CI

- Run tests locally: `pytest -q`
- CI: `.github/workflows/ci.yml` executes tests on push/PR

## Roadmap

- GPU training node group (Spot or On‑Demand)
- VPC peering for data platform integration
- Full Feast integration (offline + online store)
- Glue Catalog + Athena ETL lakehouse
- Argo Workflows for scheduled retraining pipelines
- Canary/blue‑green deployment (ALB weighted routing)
- S3 optimization (partitioning, compaction jobs)
- Prefect / Dagster orchestration layer
- SOC2 logging, IAM hardening, zero‑trust config
