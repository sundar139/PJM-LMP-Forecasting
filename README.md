# PJM Energy Forecasting ⚡️

This project focuses on predicting Locational Marginal Prices (LMP) in the PJM (Pennsylvania-New Jersey-Maryland Interconnection) electricity market. It encompasses data ingestion from the PJM API, data transformation and cleaning, feature engineering, model training using XGBoost, and a FastAPI-based serving layer for real-time predictions. The goal is to provide accurate LMP forecasts to aid in energy trading and grid management decisions.

## 🚀 Key Features

- **Data Ingestion:** Fetches raw LMP, load forecasts, and metered load data from the PJM API using the `gridstatus` library.
- **Data Transformation:** Cleans, transforms, and prepares raw data for model training, including handling timestamps, renaming columns, and clipping outliers.
- **Feature Engineering:** Creates lag, rolling, and cyclical time features to capture temporal patterns in the data.
- **Model Training:** Trains an XGBoost regression model to predict LMP, leveraging MLflow for experiment tracking and model management.
- **API Serving:** Provides a FastAPI endpoint to serve real-time LMP predictions based on the latest processed data and the trained XGBoost model.
- **Configuration Management:** Uses a centralized configuration system to manage file paths, environment variables, and other project settings.
- **Feature Store Integration (Planned):** Includes a basic feature store configuration, suggesting future integration with a more comprehensive feature store system.

## 🛠️ Tech Stack

- **Frontend:** N/A (API-focused)
- **Backend:** Python
- **API Framework:** FastAPI
- **Data Science:**
  - pandas
  - numpy
  - xgboost
  - scikit-learn (implicitly, via xgboost)
- **Data Ingestion:** gridstatus
- **Data Storage:** Parquet files
- **MLOps:** MLflow
- **Cloud (Optional):** AWS S3 (for data storage)
- **Configuration:** dataclasses, python-dotenv
- **Other:**
  - pathlib
  - datetime
  - argparse
  - typing
  - boto3 (conditional)

## 📦 Getting Started

### Prerequisites

- Python 3.8+
- Poetry (recommended) or pip
- An AWS account (if using S3)
- MLflow (for experiment tracking)

### Installation

1.  **Clone the repository:**

    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```

2.  **Install dependencies using Poetry (recommended):**

    ```bash
    poetry install
    ```

    Or, install dependencies using pip:

    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure environment variables:**

    Create a `.env` file in the project root directory and add the necessary environment variables. Example:

    ```
    AWS_ACCESS_KEY_ID=<your_aws_access_key_id>
    AWS_SECRET_ACCESS_KEY=<your_aws_secret_access_key>
    AWS_REGION=<your_aws_region>
    S3_BUCKET_NAME=<your_s3_bucket_name>
    USE_S3=False # Set to True if you want to use S3
    ```

### Running Locally

1.  **Fetch PJM Data:**

    ```bash
    python ingestion/fetch_pjm_data.py --start_date 2023-01-01 --end_date 2023-01-05
    ```

2.  **Run the ETL Pipeline:**

    ```bash
    python ingestion/etl_pipeline.py
    ```

3.  **Train the XGBoost Model:**

    ```bash
    python training/train_xgb.py
    ```

4.  **Start the FastAPI Server:**

    ```bash
    uvicorn serving.main:app --reload
    ```

    Access the API at `http://127.0.0.1:8000/docs` to view the interactive API documentation.

## 📂 Project Structure

```
├── ingestion
│   ├── __init__.py
│   ├── config.py
│   ├── etl_pipeline.py
│   └── fetch_pjm_data.py
├── serving
│   ├── __init__.py
│   ├── main.py
│   └── model_loader.py
├── training
│   ├── __init__.py
│   └── train_xgb.py
├── feature_repo
│   ├── __init__.py
│   ├── feature_definitions.py
│   └── feature_store.yaml
├── data
│   ├── models
│   │   └── xgb_rt_lmp.json
│   ├── processed
│   └── raw
├── .env
├── README.md
├── requirements.txt
└── poetry.lock
```
