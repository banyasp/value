import logging
import os
import queue
import threading
import time

from dotenv import load_dotenv
import websocket
from websocket import WebSocketApp

from config import LOGGER, TradeRow, get_env_float, get_env_int, get_subscriptions
from finnhub_producer import FinnhubTradeProducer
from trade_writer import TradeWriter


load_dotenv()


def main() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    api_key = os.getenv("FINNHUB_API_KEY")
    if not api_key:
        raise ValueError("FINNHUB_API_KEY must be set.")

    websocket.enableTrace(os.getenv("WEBSOCKET_TRACE", "").lower() in {"1", "true", "yes"})

    stop_event = threading.Event()
    trade_queue: queue.Queue[TradeRow] = queue.Queue(
        maxsize=get_env_int("WRITE_QUEUE_MAXSIZE", 20000)
    )
    writer = TradeWriter(
        trade_queue=trade_queue,
        stop_event=stop_event,
        batch_size=get_env_int("WRITE_BATCH_SIZE", 250),
        flush_interval_seconds=get_env_float("WRITE_FLUSH_SECONDS", 1.0),
        retry_seconds=get_env_int("WRITE_RETRY_SECONDS", 2),
    )
    writer.start()

    producer = FinnhubTradeProducer(
        trade_queue=trade_queue,
        queue_put_timeout=get_env_float("WRITE_QUEUE_PUT_TIMEOUT", 1.0),
        subscriptions=get_subscriptions(),
    )
    reconnect_seconds = get_env_int("FINNHUB_RECONNECT_SECONDS", 5)
    ws_app: WebSocketApp | None = None

    try:
        while True:
            if not writer.is_alive():
                raise RuntimeError("Trade writer thread stopped unexpectedly.")

            LOGGER.info("Connecting to Finnhub WebSocket feed.")
            ws_app = websocket.WebSocketApp(
                f"wss://ws.finnhub.io?token={api_key}",
                on_message=producer.on_message,
                on_error=producer.on_error,
                on_close=producer.on_close,
            )
            ws_app.on_open = producer.on_open
            ws_app.run_forever(ping_interval=20, ping_timeout=10)

            LOGGER.info(
                "WebSocket disconnected. Reconnecting in %s seconds.",
                reconnect_seconds,
            )
            time.sleep(reconnect_seconds)
    finally:
        stop_event.set()
        if ws_app is not None:
            try:
                ws_app.close()
            except Exception:  # noqa: BLE001
                LOGGER.exception("Failed to close WebSocket cleanly.")
        writer.join(timeout=10)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        LOGGER.info("Trade producer stopped by user.")
