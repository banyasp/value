import queue
import threading
import time

from psycopg2 import InterfaceError, OperationalError
from psycopg2.extras import execute_values

from config import (
    INSERT_SQL,
    LOGGER,
    TradeRow,
    build_postgres_connection,
    close_connection,
    rollback_connection,
)


class TradeWriter(threading.Thread):
    def __init__(
        self,
        trade_queue: queue.Queue[TradeRow],
        stop_event: threading.Event,
        batch_size: int,
        flush_interval_seconds: float,
        retry_seconds: int,
    ) -> None:
        super().__init__(daemon=True)
        self.trade_queue = trade_queue
        self.stop_event = stop_event
        self.batch_size = batch_size
        self.flush_interval_seconds = flush_interval_seconds
        self.retry_seconds = retry_seconds
        self.connection = None

    def run(self) -> None:
        self.connection = build_postgres_connection()
        batch: list[TradeRow] = []
        last_flush = time.monotonic()

        while not self.stop_event.is_set() or not self.trade_queue.empty():
            timeout = max(self.flush_interval_seconds - (time.monotonic() - last_flush), 0.1)
            try:
                row = self.trade_queue.get(timeout=timeout)
                batch.append(row)
                if len(batch) >= self.batch_size:
                    self._flush_batch(batch)
                    batch = []
                    last_flush = time.monotonic()
            except queue.Empty:
                if batch:
                    self._flush_batch(batch)
                    batch = []
                    last_flush = time.monotonic()

        if batch:
            self._flush_batch(batch)

        close_connection(self.connection)

    def _flush_batch(self, batch: list[TradeRow]) -> None:
        while True:
            try:
                with self.connection.cursor() as cursor:
                    execute_values(cursor, INSERT_SQL, batch)
                self.connection.commit()
                for _ in batch:
                    self.trade_queue.task_done()
                LOGGER.info(
                    "Inserted %s trade(s) into raw_trades. Queue size=%s",
                    len(batch),
                    self.trade_queue.qsize(),
                )
                return
            except (OperationalError, InterfaceError) as exc:
                LOGGER.warning("Postgres connection lost while writing trades: %s", exc)
                rollback_connection(self.connection)
                close_connection(self.connection)
                time.sleep(self.retry_seconds)
                self.connection = build_postgres_connection()
            except Exception:  # noqa: BLE001
                LOGGER.exception("Unexpected error while writing trade batch. Retrying.")
                rollback_connection(self.connection)
                time.sleep(self.retry_seconds)
