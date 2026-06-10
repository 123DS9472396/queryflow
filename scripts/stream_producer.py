"""
stream_producer.py — Real-Time Event Streaming via Redis Streams (Upstash)

Uses Redis Streams (XADD) — the production-grade Kafka alternative built into Redis.
Redis Streams are used in production at Twitter, GitHub, and Shopify.

Upstash Redis free tier: https://console.upstash.com/redis
Events are visible LIVE in the Upstash dashboard → Data Browser → stream key

Resume: "Real-time event streaming via Redis Streams on Upstash serverless"
"""
import os
import json
import random
import time
import logging
from datetime import datetime

import redis
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ── Upstash Redis Connection ───────────────────────────────────────────────────
REDIS_HOST     = os.getenv("REDIS_HOST", "devoted-macaw-115771.upstash.io")
REDIS_PORT     = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
STREAM_KEY     = os.getenv("REDIS_STREAM_KEY", "nyc-taxi-events")
MAX_STREAM_LEN = 10_000   # cap stream at 10k events (free tier safe)

PAYMENT_TYPES = ["Credit card", "Cash", "No charge", "Dispute"]
VENDOR_IDS    = [1, 2]


def get_redis_client() -> redis.Redis:
    """Connect to Upstash Redis with TLS (required for Upstash)."""
    logger.info(f"Connecting to Upstash Redis at {REDIS_HOST}:{REDIS_PORT}...")
    client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASSWORD,
        ssl=True,               # Upstash always requires TLS
        decode_responses=True,  # return strings, not bytes
        socket_timeout=10,
        socket_connect_timeout=10,
        retry_on_timeout=True,
    )
    # Validate connection
    pong = client.ping()
    logger.info(f"✅ Redis connected! PING → {pong}")
    return client


def generate_taxi_event() -> dict:
    """Generate a realistic mock NYC Taxi trip event."""
    fare    = round(random.uniform(4.0, 80.0), 2)
    tip_pct = round(random.uniform(0.05, 0.35), 3) if random.random() > 0.3 else 0.0
    now     = datetime.utcnow()
    return {
        "event_id":        f"evt_{int(time.time() * 1000)}_{random.randint(1000, 9999)}",
        "timestamp":       now.isoformat() + "Z",
        "vendor_id":       str(random.choice(VENDOR_IDS)),
        "pickup_hour":     str(now.hour),
        "day_of_week":     str(now.weekday() + 1),   # 1=Mon ... 7=Sun
        "passenger_count": str(random.randint(1, 6)),
        "trip_distance":   str(round(random.uniform(0.5, 25.0), 2)),
        "payment_method":  random.choice(PAYMENT_TYPES),
        "fare_amount":     str(fare),
        "tip_pct":         str(tip_pct),
        "tip_amount":      str(round(fare * tip_pct, 2)),
        "total_amount":    str(round(fare * (1 + tip_pct), 2)),
    }


def run_producer(num_events: int = 50, delay_ms: int = 300):
    """
    Stream num_events taxi events into Redis Stream 'nyc-taxi-events'.

    Each event is appended with XADD — a unique auto-generated ID (timestamp-ms-seq).
    View events live in Upstash dashboard → Data Browser → nyc-taxi-events
    """
    client = get_redis_client()

    # Show current stream length
    current_len = client.xlen(STREAM_KEY)
    logger.info(f"Stream '{STREAM_KEY}' currently has {current_len} events.")

    logger.info(f"Streaming {num_events} taxi events → Redis Stream '{STREAM_KEY}'...")
    sent = 0

    for i in range(num_events):
        event = generate_taxi_event()
        # XADD: append to stream, auto-trim to MAX_STREAM_LEN (MAXLEN ~ keeps it free)
        event_id = client.xadd(
            name=STREAM_KEY,
            fields=event,
            maxlen=MAX_STREAM_LEN,
            approximate=True,
        )
        sent += 1
        logger.info(
            f"[{sent:>3}/{num_events}] ✅ Stream ID: {event_id} | "
            f"fare=${event['fare_amount']:>6} | "
            f"payment={event['payment_method']:<12} | "
            f"tip={float(event['tip_pct'])*100:.1f}%"
        )
        time.sleep(delay_ms / 1000)

    final_len = client.xlen(STREAM_KEY)
    logger.info(f"Done! Streamed {sent} events. Stream total: {final_len} events.")
    logger.info(f"View live data at: https://console.upstash.com/redis → Data Browser → {STREAM_KEY}")


if __name__ == "__main__":
    run_producer(num_events=50, delay_ms=300)
