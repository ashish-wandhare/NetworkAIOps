
import argparse
import json
import sys
from pathlib import Path

from schemas import validate_event


def detect_anomalies(event):
    """Apply simple network-health rules."""
    alerts = []

    if event["latency_ms"] > 100:
        alerts.append("HIGH_LATENCY")

    if event["packet_loss_pct"] > 2:
        alerts.append("HIGH_PACKET_LOSS")

    if event["interface_errors"] > 10:
        alerts.append("HIGH_INTERFACE_ERRORS")

    return alerts


def process_event(event):
    """Validate a telemetry event and report network health."""
    validate_event(event)
    alerts = detect_anomalies(event)

    if alerts:
        print(
            f"ALERT | Device: {event['device_id']} | "
            f"Site: {event['site']} | "
            f"Issues: {', '.join(alerts)}"
        )
    else:
        print(
            f"OK    | Device: {event['device_id']} | "
            f"Site: {event['site']} | "
            f"Latency: {event['latency_ms']} ms"
        )


def main():
    parser = argparse.ArgumentParser(
        description="Process network telemetry events from a JSONL file."
    )
    parser.add_argument(
        "--input",
        default="data/telemetry_sample.jsonl",
        help="Path to the JSONL telemetry file",
    )
    args = parser.parse_args()

    input_path = Path(args.input)

    if not input_path.is_file():
        print(f"ERROR: File not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    processed = 0
    alerts_count = 0
    invalid = 0

    # utf-8-sig also handles a possible UTF-8 BOM from PowerShell.
    with input_path.open("r", encoding="utf-8-sig") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue

            try:
                event = json.loads(line)
                if not isinstance(event, dict):
                    raise ValueError("Each JSONL line must be an object")

                process_event(event)
                processed += 1

                if detect_anomalies(event):
                    alerts_count += 1

            except (json.JSONDecodeError, ValueError) as exc:
                invalid += 1
                print(
                    f"INVALID | Line {line_number}: {exc}",
                    file=sys.stderr,
                )

    print("\n--- Processing Summary ---")
    print(f"Events processed: {processed}")
    print(f"Events with alerts: {alerts_count}")
    print(f"Invalid events: {invalid}")


if __name__ == "__main__":
    main()
