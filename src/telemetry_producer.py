
import argparse
import json
import random
import time
import uuid
from datetime import datetime, timezone

from schemas import validate_event


DEVICES = [
    {"device_id": "router-01", "site": "HYD-DC1"},
    {"device_id": "router-02", "site": "HYD-DC1"},
    {"device_id": "switch-01", "site": "HYD-DC1"},
    {"device_id": "router-03", "site": "HYD-DC2"},
    {"device_id": "switch-02", "site": "HYD-DC2"},
]


def generate_event(device, anomaly=False):
    latency = max(1.0, random.gauss(20, 3))
    packet_loss = max(0.0, min(100.0, random.gauss(0.2, 0.15)))
    bandwidth = max(1.0, random.gauss(450, 60))
    interface_errors = random.randint(0, 2)
    anomaly_type = "none"

    if anomaly:
        anomaly_type = random.choice(
            ["high_latency", "packet_loss", "interface_errors"]
        )

        if anomaly_type == "high_latency":
            latency = random.uniform(150, 350)
        elif anomaly_type == "packet_loss":
            packet_loss = random.uniform(5, 25)
        else:
            interface_errors = random.randint(50, 200)

    event = {
        "event_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "device_id": device["device_id"],
        "site": device["site"],
        "latency_ms": round(latency, 2),
        "packet_loss_pct": round(packet_loss, 3),
        "bandwidth_mbps": round(bandwidth, 2),
        "interface_errors": interface_errors,
        "anomaly_type": anomaly_type,
    }

    validate_event(event)
    return event


def main():
    parser = argparse.ArgumentParser(
        description="Generate synthetic network telemetry."
    )
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--devices", type=int, default=5)
    parser.add_argument("--count", type=int, default=0)
    parser.add_argument("--anomaly-every", type=int, default=20)
    args = parser.parse_args()

    if args.interval <= 0:
        parser.error("--interval must be greater than zero")
    if not 1 <= args.devices <= len(DEVICES):
        parser.error("--devices must be between 1 and 5")
    if args.count < 0 or args.anomaly_every < 0:
        parser.error("count and anomaly-every cannot be negative")

    event_number = 0

    try:
        while args.count == 0 or event_number < args.count:
            for device in DEVICES[:args.devices]:
                if args.count and event_number >= args.count:
                    break

                event_number += 1
                inject_anomaly = (
                    args.anomaly_every > 0
                    and event_number % args.anomaly_every == 0
                )

                event = generate_event(device, inject_anomaly)
                print(json.dumps(event, allow_nan=False), flush=True)

                if args.count == 0 or event_number < args.count:
                    time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\nProducer stopped.")


if __name__ == "__main__":
    main()
