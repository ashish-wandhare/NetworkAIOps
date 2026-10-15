
from pathlib import Path
import sqlite3
import time

from fastapi import FastAPI, HTTPException, Query, Request
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from starlette.responses import Response

from src.telemetry_store import get_telemetry

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_FILE = PROJECT_ROOT / "data" / "incidents.db"

app = FastAPI(
    title="Network AIOps API",
    description="Network telemetry, anomaly detection, incidents, and Prometheus metrics.",
    version="1.3.0",
)

# Existing API monitoring metrics
HTTP_REQUESTS_TOTAL = Counter(
    "network_aiops_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

HTTP_REQUEST_DURATION = Histogram(
    "network_aiops_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
)

# Network telemetry gauges: latest stored reading per device
NETWORK_LATENCY = Gauge(
    "network_aiops_latency_ms",
    "Latest recorded network latency in milliseconds",
    ["device_id", "site"],
)

NETWORK_PACKET_LOSS = Gauge(
    "network_aiops_packet_loss_pct",
    "Latest recorded packet loss percentage",
    ["device_id", "site"],
)

NETWORK_BANDWIDTH = Gauge(
    "network_aiops_bandwidth_mbps",
    "Latest recorded bandwidth in Mbps",
    ["device_id", "site"],
)

NETWORK_INTERFACE_ERRORS = Gauge(
    "network_aiops_interface_errors",
    "Latest recorded interface error count",
    ["device_id", "site"],
)

# Database-derived totals are gauges, not process-lifetime counters
ML_ANOMALIES = Gauge(
    "network_aiops_ml_anomalies_total",
    "Number of stored telemetry events flagged as ML anomalies",
)

RULE_ALERTS = Gauge(
    "network_aiops_rule_alerts_total",
    "Number of stored telemetry events with rule-based alerts",
)

ACTIVE_INCIDENTS = Gauge(
    "network_aiops_active_incidents",
    "Number of incidents currently marked OPEN",
)


@app.middleware("http")
async def record_http_metrics(request: Request, call_next):
    if request.url.path == "/metrics":
        return await call_next(request)

    start_time = time.perf_counter()
    status_code = 500

    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        duration = time.perf_counter() - start_time
        route = request.scope.get("route")
        endpoint = getattr(route, "path", request.url.path)

        HTTP_REQUESTS_TOTAL.labels(
            request.method, endpoint, str(status_code)
        ).inc()

        HTTP_REQUEST_DURATION.labels(
            request.method, endpoint
        ).observe(duration)


def read_incidents():
    if not DATABASE_FILE.exists():
        return []

    with sqlite3.connect(DATABASE_FILE) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT incident_id, device_id, issue, alert_count,
                   first_seen, last_seen, status
            FROM incidents
            ORDER BY last_seen DESC, incident_id
            """
        ).fetchall()

    return [dict(row) for row in rows]


def refresh_network_metrics():
    """Refresh Prometheus gauges from the persistent telemetry database."""
    if not DATABASE_FILE.exists():
        return

    with sqlite3.connect(DATABASE_FILE) as connection:
        connection.row_factory = sqlite3.Row

        # Latest telemetry reading for each device
        rows = connection.execute(
            """
            SELECT t.*
            FROM telemetry AS t
            INNER JOIN (
                SELECT device_id, MAX(timestamp) AS latest_timestamp
                FROM telemetry
                GROUP BY device_id
            ) AS latest
            ON t.device_id = latest.device_id
            AND t.timestamp = latest.latest_timestamp
            """
        ).fetchall()

        anomaly_count = connection.execute(
            """
            SELECT COUNT(*) FROM telemetry
            WHERE UPPER(CAST(ml_prediction AS TEXT)) = 'ANOMALY'
               OR CAST(ml_prediction AS TEXT) = '1'
            """
        ).fetchone()[0]

        rule_alert_count = connection.execute(
            """
            SELECT COUNT(*) FROM telemetry
            WHERE rule_alert = 1
            """
        ).fetchone()[0]

        active_incident_count = connection.execute(
            """
            SELECT COUNT(*) FROM incidents
            WHERE UPPER(status) = 'OPEN'
            """
        ).fetchone()[0]

    # Clear old device label sets so removed devices don't remain visible.
    NETWORK_LATENCY.clear()
    NETWORK_PACKET_LOSS.clear()
    NETWORK_BANDWIDTH.clear()
    NETWORK_INTERFACE_ERRORS.clear()

    for row in rows:
        device = str(row["device_id"])
        site = str(row["site"] or "unknown")

        values = (
            (NETWORK_LATENCY, row["latency_ms"]),
            (NETWORK_PACKET_LOSS, row["packet_loss_pct"]),
            (NETWORK_BANDWIDTH, row["bandwidth_mbps"]),
            (NETWORK_INTERFACE_ERRORS, row["interface_errors"]),
        )

        for metric, value in values:
            if value is not None:
                metric.labels(device_id=device, site=site).set(float(value))

    ML_ANOMALIES.set(anomaly_count)
    RULE_ALERTS.set(rule_alert_count)
    ACTIVE_INCIDENTS.set(active_incident_count)


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "Network AIOps API",
        "database_exists": DATABASE_FILE.exists(),
    }


@app.get("/metrics", include_in_schema=False)
def metrics():
    refresh_network_metrics()
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


@app.get("/incidents")
def list_incidents():
    incidents = read_incidents()
    return {"count": len(incidents), "incidents": incidents}


@app.get("/incidents/{incident_id}")
def get_incident(incident_id: str):
    for incident in read_incidents():
        if incident["incident_id"] == incident_id:
            return incident

    raise HTTPException(status_code=404, detail="Incident not found")


@app.get("/telemetry")
def list_telemetry(
    limit: int = Query(default=100, ge=1, le=1000),
    device_id: str | None = None,
    anomaly_only: bool = False,
):
    events = get_telemetry(
        limit=limit,
        device_id=device_id,
        anomaly_only=anomaly_only,
    )

    return {"count": len(events), "events": events}
