import argparse
import json
import logging
import sqlite3
from pathlib import Path

import joblib
import mlflow
import mlflow.sklearn
import pandas as pd
from kafka import KafkaConsumer
from kafka.errors import KafkaError

from telemetry_consumer import process_event
from incident_correlator import add_alert, get_incidents
from telemetry_store import save_telemetry


# ---------------------------------------------------------
# Project paths and configuration
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

MODEL_FILE = PROJECT_ROOT / "models" / "isolation_forest.joblib"
MLFLOW_DB = PROJECT_ROOT / "mlflow.db"

MLFLOW_RUN_ID = "216c48c930d5469e8c7a221c291e6e53"

MLFLOW_MODEL_URI = (
    f"runs:/{MLFLOW_RUN_ID}/isolation_forest_model"
)

# Docker-compatible path to the saved MLflow model artifact.
# This model directory contains the run referenced above.
DOCKER_MLFLOW_MODEL_PATH = (
    PROJECT_ROOT
    / "mlruns"
    / "1"
    / "models"
    / "m-3cabaa6a43ed4f7aa1a688ec1368dc59"
    / "artifacts"
)

FEATURES = [
    "latency_ms",
    "packet_loss_pct",
    "bandwidth_mbps",
    "interface_errors",
]

DEFAULT_TOPIC = "network-telemetry"
DEFAULT_GROUP_ID = "network-aiops-consumers"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------
# Model loading
# ---------------------------------------------------------

def load_model(model_source):
    """Load the anomaly detection model from MLflow or joblib."""

    if model_source == "joblib":
        if not MODEL_FILE.exists():
            raise FileNotFoundError(
                f"Joblib model not found: {MODEL_FILE}"
            )

        logger.info("Loading model from joblib: %s", MODEL_FILE)
        model = joblib.load(MODEL_FILE)
        logger.info("Joblib model loaded successfully.")
        return model

    if model_source == "mlflow":
        if not MLFLOW_DB.exists():
            raise FileNotFoundError(
                f"MLflow database not found: {MLFLOW_DB}"
            )

        mlflow.set_tracking_uri(
            f"sqlite:///{MLFLOW_DB.as_posix()}"
        )

        if Path("/.dockerenv").exists():
            if not DOCKER_MLFLOW_MODEL_PATH.exists():
                raise FileNotFoundError(
                    "Docker MLflow model artifact not found: "
                    f"{DOCKER_MLFLOW_MODEL_PATH}"
                )

            logger.info(
                "Loading MLflow model from Docker artifact path: %s",
                DOCKER_MLFLOW_MODEL_PATH,
            )

            model = mlflow.sklearn.load_model(
                str(DOCKER_MLFLOW_MODEL_PATH)
            )
        else:
            logger.info(
                "Loading MLflow model from run URI: %s",
                MLFLOW_MODEL_URI,
            )

            model = mlflow.sklearn.load_model(
                MLFLOW_MODEL_URI
            )

        logger.info("MLflow model loaded successfully.")
        return model

    raise ValueError(
        f"Unsupported model source: {model_source}"
    )


# ---------------------------------------------------------
# Feature preparation and ML prediction
# ---------------------------------------------------------

def prepare_features(event):
    """Convert telemetry fields into a one-row DataFrame."""

    missing_fields = [
        feature
        for feature in FEATURES
        if feature not in event
    ]

    if missing_fields:
        raise ValueError(
            f"Missing telemetry features: {missing_fields}"
        )

    values = {}

    for feature in FEATURES:
        values[feature] = float(event[feature])

    return pd.DataFrame([values], columns=FEATURES)


def predict_anomaly(model, event):
    """
    Predict whether telemetry is anomalous.

    IsolationForest:
        -1 = anomaly
         1 = normal

    Returns:
        ml_prediction: 1 for anomaly, 0 for normal
        ml_score: anomaly score from decision_function
    """

    features = prepare_features(event)

    prediction = int(model.predict(features)[0])
    ml_prediction = 1 if prediction == -1 else 0

    ml_score = None

    if hasattr(model, "decision_function"):
        ml_score = float(
            model.decision_function(features)[0]
        )

    return ml_prediction, ml_score


# ---------------------------------------------------------
# Telemetry processing
# ---------------------------------------------------------

def handle_message(message, model):
    """Validate, analyze, correlate, and store one event."""

    try:
        event = json.loads(message.value.decode("utf-8"))

        if not isinstance(event, dict):
            raise ValueError(
                "Telemetry message must contain a JSON object."
            )

        logger.info(
            "Received telemetry: device=%s site=%s",
            event.get("device_id", "unknown"),
            event.get("site_id", "unknown"),
        )

        # Apply existing rule-based telemetry processing.
        rule_alert = process_event(event)

        # Apply the ML model.
        ml_prediction, ml_score = predict_anomaly(
            model,
            event,
        )

        if ml_prediction == 1:
            logger.warning(
                "ML ANOMALY: device=%s score=%s",
                event.get("device_id", "unknown"),
                ml_score,
            )

        # Record an alert if rule-based or ML detection flags
        # the event. Existing correlation logic determines
        # how alerts are grouped into incidents.
        if rule_alert or ml_prediction == 1:
            alert_details = {
                **event,
                "ml_prediction": ml_prediction,
                "ml_score": ml_score,
                "rule_alert": rule_alert,
            }

            add_alert(alert_details)

        # Persist telemetry using the existing storage function.
        save_telemetry(
            event,
            ml_prediction,
            ml_score,
            rule_alert,
        )

        logger.info(
            "Processed telemetry: device=%s rule_alert=%s "
            "ml_prediction=%s ml_score=%s",
            event.get("device_id", "unknown"),
            rule_alert,
            ml_prediction,
            ml_score,
        )

    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
        logger.error("Invalid telemetry message: %s", exc)

    except sqlite3.Error:
        logger.exception(
            "SQLite error while processing telemetry."
        )
        raise

    except Exception:
        logger.exception(
            "Unexpected error while processing telemetry."
        )
        raise


# ---------------------------------------------------------
# Kafka consumer
# ---------------------------------------------------------

def run_consumer(
    bootstrap_servers,
    topic,
    group_id,
    model_source,
):
    """Connect to Kafka and continuously process telemetry."""

    model = load_model(model_source)

    logger.info(
        "Connecting to Kafka: servers=%s topic=%s group=%s",
        bootstrap_servers,
        topic,
        group_id,
    )

    consumer = None

    try:
        consumer = KafkaConsumer(
            topic,
            bootstrap_servers=bootstrap_servers.split(","),
            group_id=group_id,
            auto_offset_reset="earliest",
            enable_auto_commit=True,
            value_deserializer=None,
        )

        logger.info(
            "Kafka consumer started. Waiting for telemetry..."
        )

        for message in consumer:
            handle_message(message, model)

    except KafkaError:
        logger.exception("Kafka error occurred.")
        raise

    except KeyboardInterrupt:
        logger.info("Consumer stopped by user.")

    finally:
        if consumer is not None:
            consumer.close()
            logger.info("Kafka consumer connection closed.")


# ---------------------------------------------------------
# Command-line arguments
# ---------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Network AIOps Kafka consumer with ML anomaly detection."
        )
    )

    parser.add_argument(
        "--bootstrap-servers",
        default="127.0.0.1:9092",
        help="Kafka bootstrap server address.",
    )

    parser.add_argument(
        "--topic",
        default=DEFAULT_TOPIC,
        help="Kafka telemetry topic.",
    )

    parser.add_argument(
        "--group-id",
        default=DEFAULT_GROUP_ID,
        help="Kafka consumer group ID.",
    )

    parser.add_argument(
        "--model-source",
        choices=["mlflow", "joblib"],
        default="mlflow",
        help="Model source: MLflow or joblib.",
    )

    return parser.parse_args()


def main():
    args = parse_args()

    run_consumer(
        bootstrap_servers=args.bootstrap_servers,
        topic=args.topic,
        group_id=args.group_id,
        model_source=args.model_source,
    )


if __name__ == "__main__":
    main()