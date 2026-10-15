# Network AIOps — Intelligent Network Operations

An end-to-end Network AIOps portfolio project that streams synthetic network telemetry through Apache Kafka, detects anomalies using Isolation Forest and rule-based checks, correlates alerts into incidents, exposes API and application metrics, and visualizes operations through Streamlit and Grafana.

> **Project status:** Local portfolio prototype. Evaluation uses synthetic telemetry, not production network traffic. Reported metrics should not be interpreted as validated performance on a real enterprise network.

## Highlights

- Real-time-style telemetry streaming with Apache Kafka in KRaft mode.
- Python telemetry producer with configurable synthetic anomaly scenarios.
- Unsupervised anomaly detection using scikit-learn Isolation Forest.
- Rule-based checks for high latency, packet loss, and interface errors.
- Incident correlation to group related alerts.
- SQLite persistence for telemetry and incident records.
- FastAPI endpoints for health checks, telemetry, incidents, and metrics.
- Streamlit dashboard for telemetry exploration and incident monitoring.
- Prometheus metrics collection and Grafana visualization.
- MLflow experiment tracking and model artifacts.
- Docker Compose deployment.
- Unit tests for telemetry schema validation.

## Architecture

```text
Synthetic Telemetry Producer
            |
            v
     Apache Kafka
  Topic: network-telemetry
            |
            v
      Kafka Consumer
            |
            +-------------------+
            |                   |
            v                   v
     Isolation Forest      Rule-Based Checks
            |                   |
            +---------+---------+
                      |
                      v
              Alert Correlation
                      |
                      v
                SQLite Storage
                      |
          +-----------+-----------+
          |                       |
          v                       v
      FastAPI API            Streamlit UI
          |
          v
      Prometheus
          |
          v
       Grafana

MLflow: model experiment tracking and model artifacts
Docker Compose: local service orchestration
```

## Technology stack

| Area | Technologies |
|---|---|
| Programming | Python |
| Streaming | Apache Kafka, KRaft |
| Machine learning | scikit-learn, Isolation Forest |
| Data processing | pandas, NumPy |
| Model loading | Joblib, MLflow |
| API | FastAPI, Uvicorn |
| Dashboard | Streamlit |
| Storage | SQLite |
| Monitoring | Prometheus, Grafana |
| Containers | Docker, Docker Compose |
| Testing | Python unittest |

## Telemetry features

The Isolation Forest model uses four numeric features:

- `latency_ms`
- `packet_loss_pct`
- `bandwidth_mbps`
- `interface_errors`

Synthetic events represent normal conditions and injected anomaly scenarios such as high latency, packet loss, and high interface errors.

The current project does not collect telemetry from physical network devices.

## Machine learning evaluation

The evaluation dataset contains 1,000 synthetic events:

- 900 generated normal events
- 100 generated anomalous events

The evaluation script compares Isolation Forest contamination settings using an 80/20 train/test split with `random_state=42`.

The candidate model selected for the consumer used `contamination=0.10`.

| Metric | Recorded value |
|---|---:|
| Accuracy | 0.98 |
| Precision | 0.90 |
| Recall | 0.90 |
| F1 score | 0.90 |
| True positives | 18 |
| False negatives | 2 |
| False positives | 2 |
| True negatives | 178 |

**Important interpretation:** These metrics were recorded on generated data whose anomaly patterns are synthetic. They do not demonstrate equivalent accuracy on real enterprise network telemetry.

The rule-based detector also performed well on generated examples because the injected anomaly ranges were designed to align with configured thresholds. This is not independent evidence of production performance.

Real-world validation would require representative labelled telemetry, careful threshold and model tuning, and analysis of data drift and false-positive rates.

## Prerequisites

- Windows 11, PowerShell, and VS Code, or an equivalent development environment.
- Docker Desktop with Docker Compose.
- Git, if cloning the repository.
- Sufficient memory and disk space for Kafka, the API, dashboard, Prometheus, and Grafana.

This project was developed locally on a machine with 8 GB RAM. Resource usage can be significant when multiple services run together.

## Getting started with Docker

### 1. Clone the repository

```powershell
git clone https://github.com/ashish-wandhare/NetworkAIOps.git
cd NetworkAIOps
```

### 2. Configure the consumer to use Joblib

The repository includes `models/isolation_forest.joblib`, but the local MLflow database and tracking artifacts are intentionally excluded from Git.

For a fresh clone, open `docker-compose.yml` and change the consumer command's model source from:

```yaml
--model-source mlflow
```

to:

```yaml
--model-source joblib
```

Keep the remaining consumer arguments unchanged. The Joblib model-loading path has been tested inside the Docker consumer image.

This change lets the consumer load the committed model without depending on your local MLflow tracking database or model artifacts.

### 3. Start the services

From the project root:

```powershell
docker compose up -d --build
```

Check service status:

```powershell
docker compose ps
```

View logs if a service fails to start:

```powershell
docker compose logs --tail 100
```

Follow a particular service's logs:

```powershell
docker compose logs -f consumer
```

Use `Ctrl+C` to stop following logs. This does not itself stop the containers.

### 4. Generate telemetry

Once Kafka and the consumer are running, open another PowerShell terminal in the project root:

```powershell
docker compose run --rm consumer python src/kafka_producer.py --count 5 --interval 1 --anomaly-every 2
```

The producer publishes synthetic telemetry events to Kafka. The consumer processes events, runs anomaly detection and rule checks, and persists the results.

Refresh the Streamlit dashboard to view the latest data.

### 5. Stop the services

```powershell
docker compose down
```

This stops and removes the Compose containers and network. Named volumes such as the Grafana data volume are normally retained unless explicitly removed.

## Local service URLs

When the corresponding containers are running, these interfaces are available on the local machine:

| Service | URL |
|---|---|
| Streamlit dashboard | http://localhost:8501 |
| FastAPI health | http://127.0.0.1:8000/health |
| FastAPI interactive docs | http://127.0.0.1:8000/docs |
| FastAPI metrics | http://127.0.0.1:8000/metrics |
| Prometheus UI | http://localhost:9090 |
| Prometheus targets | http://localhost:9090/targets |
| Grafana | http://localhost:3000 |

The MLflow UI is not automatically exposed by the current Compose configuration. When running the local MLflow setup with its database and artifacts available, it can be started separately:

```powershell
mlflow ui --backend-store-uri sqlite:///mlflow.db --host 127.0.0.1 --port 5000
```

Local MLflow tracking files are not included in the GitHub repository.

### Grafana login

The current local Compose configuration sets the default Grafana credentials to:

- Username: `admin`
- Password: `admin`

These are development credentials only. Change them before exposing Grafana to any network beyond your local machine.

## Alternative: Local Python workflow

The repository also contains `start_aiops.bat`, which starts the consumer, API, and Streamlit in separate terminal windows.

The local workflow expects the configured Python environment and, when using MLflow mode, the required MLflow database and artifacts.

Activate your environment as appropriate for your machine, then run:

```powershell
.\start_aiops.bat
```

The launcher and Docker workflow are different deployment approaches. Do not start duplicate copies of the same services on the same ports.

## Model loading options

The Kafka consumer supports two model sources.

### Joblib

```powershell
python src/kafka_consumer.py --model-source joblib
```

This loads the model from:

```text
models/isolation_forest.joblib
```

The Joblib model file is included in the repository. This is the simpler option for a fresh clone, assuming the Python dependencies and Kafka service are available.

### MLflow

```powershell
python src/kafka_consumer.py --model-source mlflow
```

This uses the MLflow run and model artifacts configured in the project. It requires the appropriate `mlflow.db` and associated model artifacts, which are excluded from GitHub.

The MLflow configuration demonstrates experiment tracking and model artifact loading, but a fresh clone must separately prepare those files or use the Joblib option.

## API endpoints

| Endpoint | Purpose |
|---|---|
| `GET /health` | Reports API health and database-file availability |
| `GET /telemetry` | Retrieves telemetry records, with supported query filters |
| `GET /incidents` | Retrieves incident records |
| `GET /incidents/{incident_id}` | Retrieves a specific incident |
| `GET /metrics` | Exposes Prometheus-format application metrics |

For interactive API exploration, open http://127.0.0.1:8000/docs.

## Monitoring

FastAPI exposes application metrics including:

- `network_aiops_http_requests_total`
- `network_aiops_http_request_duration_seconds`

The project also exposes network telemetry and operational metrics, including latency, packet loss, bandwidth, interface errors, ML anomalies, rule-based alerts, and active incidents.

Prometheus scrapes the API metrics endpoint, and Grafana visualizes the collected metrics through the Network AIOps monitoring dashboard.

During local verification, the Prometheus target was observed as `UP`, and Grafana panels updated after API requests and fresh telemetry activity.

A browser request for `/favicon.ico` may appear as an HTTP 404 in request metrics. This is typically a missing browser icon rather than an application endpoint failure.

## Run unit tests

Activate the appropriate project Python environment and run:

```powershell
python -m unittest discover -s tests -v
```

At the latest recorded verification checkpoint, all five telemetry schema tests passed:

1. Valid event accepted.
2. Missing field rejected.
3. Negative latency rejected.
4. Invalid packet loss rejected.
5. Invalid interface errors rejected.

These tests cover telemetry schema validation. They do not constitute comprehensive testing of all API, Kafka, database, or recovery behavior.

## Repository structure

```text
NetworkAIOps/
├── data/
│   ├── telemetry_evaluation.jsonl
│   └── telemetry_sample.jsonl
├── models/
│   └── isolation_forest.joblib
├── prometheus/
│   └── prometheus.yml
├── src/
│   ├── api.py
│   ├── dashboard.py
│   ├── evaluate_anomaly_model.py
│   ├── incident_correlator.py
│   ├── kafka_consumer.py
│   ├── kafka_producer.py
│   ├── live_stream.py
│   ├── ml_anomaly_detector.py
│   ├── schemas.py
│   ├── telemetry_consumer.py
│   ├── telemetry_producer.py
│   ├── telemetry_store.py
│   └── verify_mlflow_model.py
├── tests/
│   └── test_schemas.py
├── .dockerignore
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── start_aiops.bat
└── README.md
```

Local databases, backups, virtual environments, and MLflow tracking data are excluded from version control.

## Current limitations and future improvements

- Synthetic telemetry is used; production network devices and traffic have not been validated.
- Model performance and threshold values require evaluation against representative labelled data.
- Additional tests are needed for API routes, malformed Kafka messages, consumer failures, duplicate processing, and restart behavior.
- Persistence should be verified across service restarts.
- Model/version management and data-drift monitoring need further development.
- Dashboard readability and monitoring queries can be refined.
- Dependency locking and a fully reproducible environment setup would improve portability.
- Kubernetes orchestration is intentionally deferred to keep local resource requirements manageable.

## Portfolio summary

Network AIOps demonstrates an end-to-end engineering workflow that combines streaming telemetry, unsupervised ML anomaly detection, rule-based alerting, incident correlation, REST APIs, a dashboard, experiment tracking, and monitoring.

The project is a locally tested portfolio prototype using synthetic telemetry. Production use would require additional reliability, security, scaling, and real-data validation.

GitHub repository: https://github.com/ashish-wandhare/NetworkAIOps
