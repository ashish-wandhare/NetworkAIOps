
from pathlib import Path

import mlflow
import pandas as pd

# Locate the project and MLflow database
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_ROOT / "mlflow.db"

tracking_uri = DATABASE_PATH.resolve().as_uri()
tracking_uri = tracking_uri.replace("file:", "sqlite:", 1)

mlflow.set_tracking_uri(tracking_uri)

# Find the experiment
experiment = mlflow.get_experiment_by_name(
    "NetworkAIOps-Anomaly-Detection"
)

if experiment is None:
    raise RuntimeError("MLflow experiment not found.")

# Find the latest run with contamination 0.10
runs = mlflow.search_runs(
    experiment_ids=[experiment.experiment_id],
    filter_string=(
        "tags.mlflow.runName = "
        "'isolation-forest-contamination-0.10'"
    ),
    order_by=["start_time DESC"],
    max_results=1,
)

if runs.empty:
    raise RuntimeError("The 0.10 experiment run was not found.")

run_id = runs.iloc[0]["run_id"]
model_uri = f"runs:/{run_id}/isolation_forest_model"

print("Loading model from MLflow...")
print("Run ID:", run_id)

# Load the saved model
model = mlflow.sklearn.load_model(model_uri)

# Prepare two telemetry examples
sample = pd.DataFrame(
    [
        {
            "latency_ms": 25.0,
            "packet_loss_pct": 0.2,
            "bandwidth_mbps": 450.0,
            "interface_errors": 1,
        },
        {
            "latency_ms": 250.0,
            "packet_loss_pct": 10.0,
            "bandwidth_mbps": 100.0,
            "interface_errors": 100,
        },
    ]
)

# Predict
predictions = model.predict(sample)

print("\nPredictions:")

for index, prediction in enumerate(predictions):
    label = "ANOMALY" if prediction == -1 else "NORMAL"
    print(f"Sample {index + 1}: {label} (raw prediction: {prediction})")

print("\nMLflow model loaded and predictions completed successfully.")
