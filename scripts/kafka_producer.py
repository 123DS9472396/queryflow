"""
kafka_producer.py — Enterprise Streaming Ingestion Layer

Streams mock NYC Taxi events to a REAL Kafka broker.
Supports both:
  - Upstash Kafka (free, serverless, SSL) — set KAFKA_BROKER, KAFKA_USERNAME, KAFKA_PASSWORD
  - Local Kafka — just set KAFKA_BROKER=localhost:9092 with no auth

Setup (Upstash free tier — no credit card):
  1. Sign up at https://console.upstash.com
  2. Create Cluster → name "queryflow-stream", region us-east-1
  3. Copy Bootstrap Server, Username, Password
  4. Add to your .env file
"""

import os
import json
import random
import time
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ── Kafka Config ───────────────────────────────────────────────────────────────
KAFKA_BROKER   = os.getenv("KAFKA_BROKER", "localhost:9092")
KAFKA_USERNAME = os.getenv("KAFKA_USERNAME", "")
KAFKA_PASSWORD = os.getenv("KAFKA_PASSWORD", "")
KAFKA_TOPIC    = os.getenv("KAFKA_TOPIC", "nyc-taxi-events")

PAYMENT_TYPES  = ["Credit card", "Cash", "No charge", "Dispute"]
VENDOR_IDS     = [1, 2]


def generate_taxi_event() -> dict:
    """Generate a realistic mock NYC Taxi trip event."""
    fare    = round(random.uniform(4.0, 80.0), 2)
    tip_pct = round(random.uniform(0.0, 0.35), 3) if random.random() > 0.3 else 0.0
    return {
        "event_id":        f"evt_{int(time.time() * 1000)}_{random.randint(1000, 9999)}",
        "timestamp":       datetime.utcnow().isoformat() + "Z",
        "vendor_id":       random.choice(VENDOR_IDS),
        "pickup_datetime": datetime.utcnow().isoformat(),
        "passenger_count": random.randint(1, 6),
        "trip_distance":   round(random.uniform(0.5, 25.0), 2),
        "payment_method":  random.choice(PAYMENT_TYPES),
        "fare_amount":     fare,
        "tip_pct":         tip_pct,
        "tip_amount":      round(fare * tip_pct, 2),
        "total_amount":    round(fare * (1 + tip_pct), 2),
    }


def build_producer():
    """Build a KafkaProducer — SSL/SASL for Upstash, plain for local."""
    from kafka import KafkaProducer
    from kafka.errors import NoBrokersAvailable

    use_ssl = bool(KAFKA_USERNAME and KAFKA_PASSWORD)

    if use_ssl:
        # Upstash Kafka — SASL_SSL required
        logger.info(f"Connecting to Upstash Kafka at {KAFKA_BROKER} (SSL/SASL)...")
        producer = KafkaProducer(
            bootstrap_servers=[KAFKA_BROKER],
            security_protocol="SASL_SSL",
            sasl_mechanism="SCRAM-SHA-256",
            sasl_plain_username=KAFKA_USERNAME,
            sasl_plain_password=KAFKA_PASSWORD,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
            request_timeout_ms=30000,
            retry_backoff_ms=500,
        )
    else:
        # Local Kafka (dev/testing)
        logger.info(f"Connecting to local Kafka at {KAFKA_BROKER}...")
        producer = KafkaProducer(
            bootstrap_servers=[KAFKA_BROKER],
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
        )

    return producer


def run_producer(num_events: int = 50, delay_ms: int = 200):
    """Stream num_events taxi events to Kafka topic."""
    try:
        producer = build_producer()
    except Exception as e:
        logger.error(f"Kafka connection failed: {e}")
        logger.info("NOTE: Set KAFKA_BROKER + KAFKA_USERNAME + KAFKA_PASSWORD in .env for Upstash Kafka.")
        return

    logger.info(f"Streaming {num_events} events to topic '{KAFKA_TOPIC}'...")
    sent = 0
    try:
        for i in range(num_events):
            event = generate_taxi_event()
            future = producer.send(
                topic=KAFKA_TOPIC,
                key=event["event_id"],
                value=event,
            )
            # Block until confirmed
            record = future.get(timeout=10)
            sent += 1
            logger.info(
                f"[{sent}/{num_events}] ✅ Sent to partition={record.partition} "
                f"offset={record.offset} | fare=${event['fare_amount']} | "
                f"payment={event['payment_method']}"
            )
            time.sleep(delay_ms / 1000)

    except KeyboardInterrupt:
        logger.info("Stream interrupted by user.")
    finally:
        producer.flush()
        producer.close()
        logger.info(f"Done. {sent} events streamed to '{KAFKA_TOPIC}'.")


if __name__ == "__main__":
    run_producer(num_events=50, delay_ms=300)
