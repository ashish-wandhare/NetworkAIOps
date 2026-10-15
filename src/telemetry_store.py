
import json
import sqlite3
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_FILE = PROJECT_ROOT / "data" / "incidents.db"


def initialize_telemetry_table():
    """Create persistent telemetry storage in the existing database."""
    DATABASE_FILE.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DATABASE_FILE) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS telemetry (
                event_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                device_id TEXT NOT NULL,
                site TEXT,
                latency_ms REAL,
                packet_loss_pct REAL,
                bandwidth_mbps REAL,
                interface_errors INTEGER,
                anomaly_type TEXT,
                ml_prediction TEXT,
                ml_score REAL,
                rule_alert INTEGER NOT NULL DEFAULT 0,
                raw_event TEXT NOT NULL
            )
            """
        )


def save_telemetry(event, ml_prediction, ml_score, rule_alert):
    """Persist one processed event and its detection results."""
    initialize_telemetry_table()

    with sqlite3.connect(DATABASE_FILE) as connection:
        connection.execute(
            """
            INSERT INTO telemetry (
                event_id, timestamp, device_id, site,
                latency_ms, packet_loss_pct, bandwidth_mbps,
                interface_errors, anomaly_type, ml_prediction,
                ml_score, rule_alert, raw_event
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(event_id) DO UPDATE SET
                ml_prediction = excluded.ml_prediction,
                ml_score = excluded.ml_score,
                rule_alert = excluded.rule_alert
            """,
            (
                str(event["event_id"]),
                str(event["timestamp"]),
                str(event["device_id"]),
                event.get("site"),
                event.get("latency_ms"),
                event.get("packet_loss_pct"),
                event.get("bandwidth_mbps"),
                event.get("interface_errors"),
                event.get("anomaly_type"),
                ml_prediction,
                float(ml_score),
                int(bool(rule_alert)),
                json.dumps(event),
            ),
        )


def get_telemetry(limit=100, device_id=None, anomaly_only=False):
    """Return recent stored events, newest first."""
    initialize_telemetry_table()

    query = "SELECT * FROM telemetry WHERE 1=1"
    parameters = []

    if device_id:
        query += " AND device_id = ?"
        parameters.append(device_id)

    if anomaly_only:
        query += " AND (ml_prediction = 'ANOMALY' OR rule_alert = 1)"

    query += " ORDER BY timestamp DESC LIMIT ?"
    parameters.append(limit)

    with sqlite3.connect(DATABASE_FILE) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(query, parameters).fetchall()

    results = []
    for row in rows:
        item = dict(row)
        item["rule_alert"] = bool(item["rule_alert"])
        item.pop("raw_event", None)
        results.append(item)

    return results
