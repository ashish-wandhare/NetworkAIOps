
import argparse
import json
import time

from kafka import KafkaProducer
from telemetry_producer import DEVICES, generate_event


def main():
    parser = argparse.ArgumentParser(
        description="Publish synthetic network telemetry to Kafka."
    )
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--devices", type=int, default=5)
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--anomaly-every", type=int, default=10)
    parser.add_argument(
        "--bootstrap-servers", default="127.0.0.1:9092"
    )
    parser.add_argument("--topic", default="network-telemetry")
    args = parser.parse_args()

    if args.interval <= 0:
        parser.error("--interval must be greater than zero")
    if not 1 <= args.devices <= len(DEVICES):
        parser.error("--devices must be between 1 and 5")
    if args.count < 1 or args.anomaly_every < 0:
        parser.error(
            "--count must be positive and --anomaly-every non-negative"
        )

    producer = KafkaProducer(
        bootstrap_servers=args.bootstrap_servers,
        value_serializer=lambda event: json.dumps(
            event, allow_nan=False
        ).encode("utf-8"),
        acks="all",
        retries=3,
    )

    event_number = 0

    try:
        while event_number < args.count:
            device = DEVICES[event_number % args.devices]
            event_number += 1

            inject_anomaly = (
                args.anomaly_every > 0
                and event_number % args.anomaly_every == 0
            )

            event = generate_event(
                device, anomaly=inject_anomaly
            )

            metadata = producer.send(
                args.topic, value=event
            ).get(timeout=10)

            print(
                f"Published event {event_number}/{args.count} | "
                f"device={event['device_id']} | "
                f"anomaly={event['anomaly_type']} | "
                f"partition={metadata.partition}",
                flush=True,
            )

            if event_number < args.count:
                time.sleep(args.interval)

        producer.flush()
        print(f"Finished publishing {event_number} events.")

    except KeyboardInterrupt:
        print("\nProducer stopped.")
    finally:
        producer.close()


if __name__ == "__main__":
    main()
