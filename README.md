# ETL for Open Data Philippines Datasets

An automated ETL (Extract, Transform, Load) pipeline framework that integrates heterogeneous datasets from Philippine government open data sources (PSA), standardizes data formats and schemas, validates data quality, and provides unified programmatic access through a RESTful API.

Built to help researchers, policymakers, and developers access clean, integrated government statistics without manual data wrangling.

## Architecture

```text
PSA OpenSTAT API
  → PsaExtractor (Downloads 200+ CSVs)
    → PsaTransformer (Melts wide data to unified long schema)
      → DataValidator (Quality scores & anomaly detection)
        → PostgresLoader (Bulk insert to PostgreSQL)
          → Flask REST API (Filtered queries & pagination)
```

## How to Run (Using Docker - Recommended)

The easiest way to run the entire project (Database + API) is using Docker Compose. This ensures you don't need to manually configure Python, PostgreSQL, or system dependencies.

### Requirements

- Docker
- Docker Compose

### 1. Build and Start the Services

```bash
docker-compose up --build -d
```

This will spin up a PostgreSQL 16 database and start the Flask API on `http://localhost:5000`.

### 2. Verify the API is Running

```bash
curl http://localhost:5000/api/v1/health
```

### 3. Run the ETL Pipeline (Optional)

If you want to run the full extraction, transformation, validation, and loading process inside the docker container (this will download fresh data from the PSA API and load it into your local containerized database):

Extraction

```bash
docker-compose exec api python scripts/run_psa_extraction.py
```

Transformation

```bash
docker-compose exec api python scripts/run_transformers.py
```

Validation

```bash
docker-compose exec api python scripts/run_validation.py
```

Loading

```bash
docker-compose exec api python scripts/run_loader.py
```

### 4. Stop the Services

```bash
docker-compose down
```

---

## Local Development (Without Docker)

If you prefer to run things locally without Docker:

### 1. Set up the virtual environment:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Start the local PostgreSQL database (using mise):

```bash
mise exec -- pg_ctl -D .pgdata -l .pgdata/logfile start
```

### 3. Run the API server:

```bash
python main.py
```

## API Documentation

Once running, the API is available at `http://localhost:5000/api/v1/`.

| Endpoint            | Description                                                                     |
| :------------------ | :------------------------------------------------------------------------------ |
| `GET /datasets`     | List all unique datasets                                                        |
| `GET /categories`   | List all categories                                                             |
| `GET /observations` | Query data points. Supports `?category=...`, `?year=...`, `?page=1&per_page=50` |

## Note

Only 4 categories are included to prevent API overusage

"2E": "Agriculture_Forestry_Fisheries"

"3A": "Environment"

"1A": "Population_and_Vital_Statistics"

"2G": "Mining_Manufacturing_Construction"
