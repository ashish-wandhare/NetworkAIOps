
import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.model_selection import train_test_split


# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = PROJECT_ROOT / "data" / "telemetry_sample.jsonl"
MODEL_FILE = PROJECT_ROOT / "models" / "isolation_forest.joblib"

# Network metrics used by ML
FEATURES = [
    "latency_ms",
    "packet_loss_pct",
    "bandwidth_mbps",
    "interface_errors",
]

# Existing rule-based alert thresholds
LATENCY_THRESHOLD = 100
PACKET_LOSS_THRESHOLD = 2
INTERFACE_ERRORS_THRESHOLD = 10


def main():
    # Load network telemetry events
    events = []

    with open(DATA_FILE, "r", encoding="utf-8-sig") as file:
        for line in file:
            if line.strip():
                events.append(json.loads(line))

    df = pd.DataFrame(events)

    if df.empty:
        print("No telemetry events found.")
        return

    required = FEATURES + ["anomaly_type", "device_id"]
    missing = [column for column in required if column not in df.columns]

    if missing:
        print(f"Missing required columns: {missing}")
        return

    # Prepare features and known labels
    X = df[FEATURES].astype(float)
    y = (df["anomaly_type"] != "none").astype(int)

    # Split into training and testing data
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=42,
        stratify=y,
    )

    # Train Isolation Forest
    model = IsolationForest(
        n_estimators=100,
        contamination=0.10,
        random_state=42,
    )
    model.fit(X_train)

    # Save the trained model
    MODEL_FILE.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_FILE)
    print(f"ML model saved to: {MODEL_FILE}")

    # Predict anomalies in the test data
    ml_predictions = model.predict(X_test)
    ml_anomaly = ml_predictions == -1

    # Apply existing rule-based detection to the same test events
    test_data = df.loc[X_test.index]

    rule_anomaly = (
        (test_data["latency_ms"] > LATENCY_THRESHOLD)
        | (test_data["packet_loss_pct"] > PACKET_LOSS_THRESHOLD)
        | (test_data["interface_errors"] > INTERFACE_ERRORS_THRESHOLD)
    ).to_numpy()

    # Actual injected anomaly labels are used only for evaluation
    actual_anomaly = y_test.to_numpy() == 1

    def calculate_metrics(predicted, actual):
        return {
            "correctly_detected": int((predicted & actual).sum()),
            "missed": int((~predicted & actual).sum()),
            "false_alarms": int((predicted & ~actual).sum()),
            "correctly_normal": int((~predicted & ~actual).sum()),
        }

    ml_results = calculate_metrics(ml_anomaly, actual_anomaly)
    rule_results = calculate_metrics(rule_anomaly, actual_anomaly)

    print(f"\nTotal events: {len(df)}")
    print(f"Training events: {len(X_train)}")
    print(f"Testing events: {len(X_test)}")
    print(f"Actual anomalies in test set: {int(actual_anomaly.sum())}")

    print("\n--- ML: Isolation Forest ---")
    for name, value in ml_results.items():
        print(f"{name.replace('_', ' ').title()}: {value}")

    print("\n--- Rule-Based Detection ---")
    for name, value in rule_results.items():
        print(f"{name.replace('_', ' ').title()}: {value}")

    # Display test-event predictions
    report = test_data[
        [
            "device_id",
            "latency_ms",
            "packet_loss_pct",
            "interface_errors",
            "anomaly_type",
        ]
    ].copy()

    report["actual"] = [
        "ANOMALY" if value else "NORMAL"
        for value in actual_anomaly
    ]
    report["ml_prediction"] = [
        "ANOMALY" if value else "NORMAL"
        for value in ml_anomaly
    ]
    report["rule_prediction"] = [
        "ANOMALY" if value else "NORMAL"
        for value in rule_anomaly
    ]

    print("\n--- Predictions on Test Events ---")
    print(report.to_string(index=False))


if __name__ == "__main__":
    main()
