import finnhub
import os
from dotenv import load_dotenv

load_dotenv()

client = finnhub.Client(api_key=os.getenv("FINNHUB_API_KEY"))

# subscribe to stock price


#https://pypi.org/project/websocket_client/
import websocket

class FinnhubWebSocketClient:
    def __init__(self):
        self.subscriptions = [
            "AAPL",
            "AMZN",
            "BINANCE:BTCUSDT",
            "IC MARKETS:1",
        ]

    def on_message(self, ws, message):
        print(message)

    def on_error(self, ws, error):
        print(error)

    def on_close(self, ws, close_status_code, close_msg):
        print("### closed ###")

    def on_open(self, ws):
        for symbol in self.subscriptions:
            ws.send(f'{{"type":"subscribe","symbol":"{symbol}"}}')

if __name__ == "__main__":
    websocket.enableTrace(True)
    socket_client = FinnhubWebSocketClient()
    ws = websocket.WebSocketApp(
                              f"wss://ws.finnhub.io?token={os.getenv('FINNHUB_API_KEY')}",
                              on_message=socket_client.on_message,
                              on_error=socket_client.on_error,
                              on_close=socket_client.on_close)
    ws.on_open = socket_client.on_open
    ws.run_forever()