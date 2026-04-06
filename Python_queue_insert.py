import uuid
from psycopg_pool import ConnectionPool   #handles multiple connections as a pool. Enhances performance
import psycopg

#https://pypi.org/project/websocket_client/
import websocket
from websocket import WebSocketApp
from websocket import enableTrace

def on_message(ws, message):
    print(message)

def on_error(ws, error):
    print(error)

def on_close(ws):
    print("### closed ###")

def on_open(ws):
    ws.send('{"type":"subscribe","symbol":"AAPL"}')
    ws.send('{"type":"subscribe","symbol":"AMZN"}')
    ws.send('{"type":"subscribe","symbol":"BINANCE:BTCUSDT"}')
    ws.send('{"type":"subscribe","symbol":"IC MARKETS:1"}')

if __name__ == "__main__":
    websocket.enableTrace(True)
    ws = websocket.WebSocketApp("wss://ws.finnhub.io?token=d765t19r01qm4b7t3a00d765t19r01qm4b7t3a0g",
                              on_message = on_message,
                              on_error = on_error,
                              on_close = on_close)
    ws.on_open = on_open
    ws.run_forever()

DATABASE_URL = "insert_url_for_sql_db"

pool = ConnectionPool(conninfo=DATABASE_URL)


stocks_ingested = []
#throw in the list dictionaries "trades"

for item in stocks_ingested:
    item["UID"] = uuid.uuid4()

#columns = stocks_ingested[0].keys() #for when the table for trade does not already exist in SQL DB

#then assume table exist, insert
sql = """INSERT INTO all_trades (UID, s, t, p, v)
        VALUE (%(UID)s, %(s)s, %(t)s, %(p)s, %(v)s)"""

with pool.connection() as conn:
    with conn.cursor() as cursor:
        for item in stocks_ingested:
            cursor.execute(sql, 
                           {'UID':item.get("UID"),'s':item.get("s"), 't':item.get("t"), 
                            'p':item.get("p"), 'v':item.get("v")}
                            )
