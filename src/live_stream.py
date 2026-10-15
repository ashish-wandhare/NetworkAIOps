
import argparse
import time

from telemetry_producer import DEVICES, generate_event
from telemetry_consumer import process_event


def main():
    parser = argparse.ArgumentParser(
        description="Run a lightweight live Network AIOps stream."
    )
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--anomaly-every", type=int, default=10)
    args = parser.parse_args()

    if args.interval <= 0:
        parser.error("--interval must be greater than zero")

    if args.anomaly_every < 0:
        parser.error("--anomaly-every cannot be negative")

    event_number = 0

    print("Live Network AIOps stream started.")
    print("Press Ctrl+C to stop.\n")

    try:
        while True:
            for device in DEVICES:
                event_number += 1

                inject_anomaly = (
                    args.anomaly_every > 0
                    and event_number % args.anomaly_every == 0
                )

                event = generate_event(device, anomaly=inject_anomaly)
                process_event(event)

                if args.interval:
                    time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\nLive stream stopped.")


if __name__ == "__main__":
    main()
