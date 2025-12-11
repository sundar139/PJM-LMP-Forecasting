You want the **real “how do I run this thing end-to-end on my machine” guide**, not another vague cloud-guru pep talk.
Fine. Here is the **actual execution workflow** for your project — **LOCAL MODE first**, then **CLOUD MODE (Terraform + EKS)** once you’re ready.

No fluff. No missing steps. Just the sequence you follow from a fresh Windows machine to “model is predicting LMPs in an API.”

---

# PART 0 — Confirm Your Setup (the bare minimum)

In PowerShell:

```powershell
python --version
pip --version
aws --version
terraform -version
```

Then activate your virtual environment:

```powershell
cd C:\Users\<you>\Documents\Projects\pjm-mlops-lmp-forecasting
.\.venv\Scripts\Activate.ps1
```

If the prompt changes to `(.venv)` → good.

---

# PART 1 — Run the Project LOCALLY (No AWS yet)

This is the part you MUST complete before touching the cloud.

Your local architecture:

```
Fetch PJM Data → ETL → Validate → Feature Engineering → Train Model → Serve via FastAPI
```

### ✔ Step 1 — Ingest sample (test-run mode)

This fetches only 1 day. Safe, fast.

```powershell
python -m ingestion.fetch_pjm_data --test-run
```

You should now see:

```
data/raw/pjm_raw_YYYYMMDD_YYYYMMDD.parquet
```

If you do not see a file → gridstatus API failed or network blocked.

---

### ✔ Step 2 — ETL the raw file

Find your latest raw file:

```powershell
$raw = Get-ChildItem .\data\raw | Sort-Object LastWriteTime | Select-Object -Last 1
python -m ingestion.etl_pipeline --raw-path $raw.FullName
```

Expected output:

```
data/processed/pjm_processed_YYYYMMDD_YYYYMMDD.parquet
```

---

### ✔ Step 3 — Validate processed data (Great Expectations)

```powershell
$proc = Get-ChildItem .\data\processed | Sort-Object LastWriteTime | Select-Object -Last 1
python -m ingestion.validate_data --processed-path $proc.FullName
```

If validation fails → the pipeline stops by design.

---

### ✔ Step 4 — Train the model (quick training)

This uses only 1 processed file and smaller XGBoost params.

```powershell
python -m training.train_xgb --test-run
```

Expected output:

- MLflow logs in `./mlruns/`
- Model saved in:

```
data/models/xgb_rt_lmp.json
```

If this file exists → model training succeeded.

---

### ✔ Step 5 — Run automated tests

```powershell
pytest -q
```

Tests passing means all components are wired properly:

✓ ingestion
✓ ETL
✓ validation
✓ feature engineering
✓ training
✓ serving logic

---

### ✔ Step 6 — Start the FastAPI prediction service

```powershell
uvicorn serving.main:app --reload
```

Open this in the browser:

```
http://127.0.0.1:8000/docs
```

Click:

- `GET /health` → should return `"status": "ok"`
- `POST /predict` → no body → returns predicted LMP for latest timestamp

If this works → the project is **fully operational locally**.

---

# PART 2 — OPTIONAL: Run it ALL again automatically (integration test)

You have a test:

```powershell
pytest tests/test_integration_pipeline.py
```

This verifies:

1. Ingestion
2. ETL
3. Feature building
4. Training
5. Model file creation

All in one go.

If this passes, your local MLOps pipeline is stable.

---

# PART 3 — CLOUD MODE (Only AFTER local success)

Now that the local version works, you can enable AWS.

### ✔ Step 1 — Switch `.env` to cloud mode

Open `.env` and change:

```
USE_S3=0
```

to:

```
USE_S3=1
```

Also set your S3 bucket names you created with Terraform.

---

### ✔ Step 2 — Provision cloud infra with Terraform

Go to:

```powershell
cd infrastructure\terraform
```

Then:

```powershell
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

Terraform will create:

- S3 buckets (raw + processed)
- EKS cluster
- Redis cluster
- IAM roles
- VPC and subnets (if included)
- Terraform state backend

---

### ✔ Step 3 — Update your scripts to write/read S3

You already enabled `USE_S3=1`.
The ingestion & ETL will now:

- Upload raw files → `s3://pjm-lake-raw/*`
- Upload processed → `s3://pjm-lake-processed/*`

Run:

```powershell
python -m ingestion.fetch_pjm_data --test-run
```

Then verify in AWS:

```powershell
aws s3 ls s3://pjm-lake-raw
```

---

### ✔ Step 4 — Build Docker images (training + serving)

Training:

```
Dockerfile.training
```

Serving API:

```
Dockerfile.serving
```

Build and push to ECR:

```powershell
aws ecr get-login-password --region us-east-1 `
| docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

docker build -t pjm-training -f Dockerfile.training .
docker tag pjm-training:latest <account>.dkr.ecr.us-east-1.amazonaws.com/pjm-training:latest
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/pjm-training:latest
```

Same for `pjm-serving`.

---

### ✔ Step 5 — Deploy to EKS

After Terraform creates kubeconfig:

```powershell
aws eks update-kubeconfig --region us-east-1 --name pjm-mlops-eks
```

Then deploy:

```powershell
kubectl apply -f k8s/deployment_serving.yaml
kubectl apply -f k8s/service_serving.yaml
```

Check pods:

```powershell
kubectl get pods
```

If it shows:

```
pjm-serving-deployment-xxxxx   Running
```

Your API is now deployed in the cloud.

---

# PART 4 — The EXACT ORDER in which you run the full project

Here is the master checklist you follow every time:

---

## ✔ LOCAL PIPELINE (must pass before going cloud)

1. Create virtual env, install dependencies
2. Run ingestion
3. Run ETL
4. Run validation
5. Run training
6. Run tests
7. Run serving API and manual `/predict` test

If everything works → move to cloud.

---

## ✔ CLOUD PIPELINE (deployable)

1. Install AWS CLI + Terraform
2. Configure AWS credentials
3. Run `terraform apply`
4. Enable S3 mode (`USE_S3=1`)
5. Test ingestion writes to S3
6. Build & push Docker images
7. Deploy training/serving jobs to EKS
8. Verify API on AWS Load Balancer

---

# PART 5 — Add a **single command** to run the entire local pipeline:

I can generate a `Makefile` or `make.ps1` script such as:

```
make run-local
make test
make train
make api
make ingest-test
```

### Cloud Deployment Steps

1. Provision VPC, subnets, NAT, endpoints via Terraform.

   - Set `terraform.tfvars` with `vpc_cidr`, `azs`, `public_subnet_cidrs`, `private_subnet_cidrs`.
   - `terraform init -reconfigure && terraform plan -out=tfplan && terraform apply tfplan`

2. Create S3 buckets (raw, processed) and Redis (Elasticache) with Terraform.

   - Outputs provide Redis endpoint and bucket names.

3. Create EKS and configure kubectl.

   - Use EKS module outputs for cluster name/endpoint.
   - Tag subnets for Kubernetes per module defaults.

4. Build and push container images.

   - Serving: `serving/Dockerfile`
   - Training: `training/Dockerfile`

5. Deploy workloads.

   - `kubectl apply -f infrastructure/k8s/serving.yaml`
   - `kubectl apply -f infrastructure/k8s/training-job.yaml`

6. Configure AWS Load Balancer Controller if using ALB Ingress.

   - Install via Helm and IRSA; annotate services/ingresses as needed.

7. Wire CI/CD.
   - GitHub Actions `.github/workflows/ci.yml` runs tests on PR/push.
   - Extend with build/push and kubectl/helm steps gated by environment.
