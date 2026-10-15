
from datetime import datetime
import math


REQUIRED_FIELDS = {
    "event_id",
    "timestamp",
    "device_id",
    "site",
    "latency_ms",
    "packet_loss_pct",
    "bandwidth_mbps",
    "interface_errors",
    "anomaly_type",
}


def validate_event(event: dict) -> None:
    """Validate a network telemetry event."""

    missing = REQUIRED_FIELDS - event.keys()
    if missing:
        raise ValueError(f"Missing fields: {sorted(missing)}")

    for field in ("event_id", "device_id", "site"):
        if not isinstance(event[field], str) or not event[field]:
            raise ValueError(f"{field} must be a non-empty string")

    if not isinstance(event["timestamp"], str):
        raise ValueError("timestamp must be a string")

    try:
        timestamp = datetime.fromisoformat(
            event["timestamp"].replace("Z", "+00:00")
        )
        if timestamp.tzinfo is None:
            raise ValueError("Timestamp must include timezone")
    except ValueError as exc:
        raise ValueError("Invalid ISO-8601 timestamp") from exc

    for field in (
        "latency_ms",
        "packet_loss_pct",
        "bandwidth_mbps",
        "interface_errors",
    ):
        value = event[field]

        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{field} must be numeric")

        if not math.isfinite(value):
            raise ValueError(f"{field} must be finite")

    if event["latency_ms"] < 0:
        raise ValueError("Latency cannot be negative")

    if not 0 <= event["packet_loss_pct"] <= 100:
        raise ValueError("Packet loss must be between 0 and 100")

    if event["bandwidth_mbps"] < 0:
        raise ValueError("Bandwidth cannot be negative")

    errors = event["interface_errors"]
    if isinstance(errors, bool) or not isinstance(errors, int) or errors < 0:
        raise ValueError("Interface errors must be a non-negative integer")

    if not isinstance(event["anomaly_type"], str):
        raise ValueError("anomaly_type must be a string")
