# Author: Peter Banyas - April 6
import json
import queue
from typing import Any

from psycopg2.extras import Json
from websocket import WebSocketApp

from config import LOGGER, TradeRow


class FinnhubTradeProducer:
    def __init__(
        self,
        trade_queue: queue.Queue[TradeRow],
        queue_put_timeout: float,
        subscriptions: list[str],
    ) -> None:
        self.trade_queue = trade_queue
        self.queue_put_timeout = queue_put_timeout
        self.subscriptions = subscriptions

    @staticmethod
    def _is_valid_trade(trade: dict[str, Any]) -> bool:
        required = ("s", "p", "v", "t")
        for key in required:
            if key not in trade or trade[key] is None:
                return False

        if not str(trade["s"]).strip():
            return False

        try:
            float(trade["p"])
            float(trade["v"])
            int(trade["t"])
        except (TypeError, ValueError):
            return False

        return True

    def publish_trade(self, trade: dict[str, Any]) -> None:
        row: TradeRow = (
            str(trade["s"]),
            str(trade["p"]),
            str(trade["v"]),
            int(trade["t"]),
            Json(trade.get("c")),
        )

        while True:
            try:
                self.trade_queue.put(row, timeout=self.queue_put_timeout)
                return
            except queue.Full:
                LOGGER.warning(
                    "Trade queue is full (%s items). Waiting for database writer to catch up.",
                    self.trade_queue.qsize(),
                )

    def on_message(self, ws: WebSocketApp, message: str) -> None:
        del ws

        try:
            payload = json.loads(message)
        except json.JSONDecodeError:
            LOGGER.warning("Received invalid JSON from Finnhub: %s", message)
            return

        if payload.get("type") != "trade":
            return

        trades = payload.get("data") or []
        queued = 0

        for trade in trades:
            if not self._is_valid_trade(trade):
                LOGGER.warning("Skipping malformed trade payload: %s", trade)
                continue

            self.publish_trade(trade)
            queued += 1

        if queued:
            LOGGER.info(
                "Queued %s trade(s) for database insertion. Queue size=%s",
                queued,
                self.trade_queue.qsize(),
            )

    def on_error(self, ws: WebSocketApp, error: Any) -> None:
        del ws
        LOGGER.error("Finnhub WebSocket error: %s", error)

    def on_close(self, ws: WebSocketApp, close_status_code: int, close_msg: str) -> None:
        del ws
        LOGGER.warning(
            "Finnhub WebSocket closed: status=%s message=%s",
            close_status_code,
            close_msg,
        )

    def on_open(self, ws: WebSocketApp) -> None:
        for symbol in self.subscriptions:
            ws.send(json.dumps({"type": "subscribe", "symbol": symbol}))
            LOGGER.info("Subscribed to %s", symbol)
