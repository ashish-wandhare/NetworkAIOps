
import sys
import unittest
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from schemas import validate_event


def valid_event():
    return {
        "event_id": "test-event-001",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "device_id": "router-01",
        "site": "HYD-DC1",
        "latency_ms": 20.0,
        "packet_loss_pct": 0.2,
        "bandwidth_mbps": 450.0,
        "interface_errors": 0,
        "anomaly_type": "none",
    }


class TestTelemetrySchema(unittest.TestCase):

    def test_valid_event(self):
        validate_event(valid_event())

    def test_missing_field(self):
        event = valid_event()
        del event["device_id"]

        with self.assertRaises(ValueError):
            validate_event(event)

    def test_invalid_packet_loss(self):
        event = valid_event()
        event["packet_loss_pct"] = 101

        with self.assertRaises(ValueError):
            validate_event(event)

    def test_negative_latency(self):
        event = valid_event()
        event["latency_ms"] = -1

        with self.assertRaises(ValueError):
            validate_event(event)

    def test_invalid_interface_errors(self):
        event = valid_event()
        event["interface_errors"] = -1

        with self.assertRaises(ValueError):
            validate_event(event)


if __name__ == "__main__":
    unittest.main()
