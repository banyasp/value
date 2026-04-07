import logging
import os
import time
from typing import Any, TypeAlias

import psycopg2
from psycopg2 import OperationalError


LOGGER = logging.getLogger("trade_producer")
DEFAULT_SUBSCRIPTIONS = [
    "AAPL",
    "AMZN",
    "BINANCE:BTCUSDT",
    "IC MARKETS:1",
]
INSERT_SQL = """
    INSERT INTO raw_trades (symbol, price, volume, trade_timestamp, conditions)
    VALUES %s
"""
TradeRow: TypeAlias = tuple[str, str, str, int, Any]


def get_env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    return int(value)


def get_env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    return float(value)


def get_subscriptions() -> list[str]:
    value = os.getenv("FINNHUB_SUBSCRIPTIONS")
    if not value:
        return DEFAULT_SUBSCRIPTIONS
    return [symbol.strip() for symbol in value.split(",") if symbol.strip()]


def build_postgres_connection():
    host = os.getenv("POSTGRES_HOST", "postgres")
    port = get_env_int("POSTGRES_PORT", 5432)
    dbname = os.getenv("POSTGRES_DB", "trades")
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "password")
    retry_seconds = get_env_int("POSTGRES_CONNECT_RETRY_SECONDS", 2)

    while True:
        try:
            connection = psycopg2.connect(
                host=host,
                port=port,
                dbname=dbname,
                user=user,
                password=password,
            )
            connection.autocommit = False
            LOGGER.info("Connected to Postgres at %s:%s/%s", host, port, dbname)
            return connection
        except OperationalError as exc:
            LOGGER.warning(
                "Postgres not ready yet: %s. Retrying in %s seconds.",
                exc,
                retry_seconds,
            )
            time.sleep(retry_seconds)


def close_connection(connection) -> None:
    if connection is None:
        return

    try:
        connection.close()
    except Exception:  # noqa: BLE001
        LOGGER.exception("Failed to close Postgres connection cleanly.")


def rollback_connection(connection) -> None:
    if connection is None:
        return

    try:
        connection.rollback()
    except Exception:  # noqa: BLE001
        LOGGER.exception("Failed to roll back Postgres transaction cleanly.")
