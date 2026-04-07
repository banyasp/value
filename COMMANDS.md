# Commands Reference

## First-time setup

```bash
# Copy the example env file and fill in your Finnhub API key
cp .env.example .env
# Edit .env and set FINNHUB_API_KEY to your key
```

## Start the pipeline

```bash
# Build images and start Postgres + trade producer
docker compose up --build

# Run in the background (detached)
docker compose up --build -d
```

## Stop the pipeline

```bash
# Stop containers (keeps data)
docker compose down

# Stop containers AND wipe the database
docker compose down -v
```

## Watch logs

```bash
# All services
docker compose logs -f

# Just the trade producer
docker compose logs -f trade-producer

# Just Postgres
docker compose logs -f postgres
```

## Query the database

```bash
# Open a psql shell inside the container
docker compose exec postgres psql -U postgres trades

# One-off query from the command line
docker compose exec postgres psql -U postgres trades -c "SELECT COUNT(*) FROM raw_trades;"

# Connect from your host machine (port 5433 to avoid conflict with local Postgres)
psql -h localhost -p 5433 -U postgres trades
```

## Useful queries

```sql
-- Total trades collected
SELECT COUNT(*) FROM raw_trades;

-- Trades per symbol
SELECT symbol, COUNT(*) AS trades,
       MIN(TO_TIMESTAMP(trade_timestamp/1000.0)) AS earliest,
       MAX(TO_TIMESTAMP(trade_timestamp/1000.0)) AS latest
FROM raw_trades GROUP BY symbol ORDER BY trades DESC;

-- 10 most recent trades
SELECT symbol, price, volume, TO_TIMESTAMP(trade_timestamp/1000.0) AS trade_time
FROM raw_trades ORDER BY id DESC LIMIT 10;

-- Trades in the last 5 minutes
SELECT symbol, price, volume, TO_TIMESTAMP(trade_timestamp/1000.0) AS trade_time
FROM raw_trades
WHERE TO_TIMESTAMP(trade_timestamp/1000.0) > NOW() - INTERVAL '5 minutes'
ORDER BY trade_timestamp DESC;
```

## Rebuild after code changes

```bash
# Rebuild the trade producer image and restart
docker compose up --build -d trade-producer

# Force a full rebuild (no cache)
docker compose build --no-cache trade-producer
docker compose up -d
```

## Inspect container state

```bash
# See running containers
docker compose ps

# Check the trade queue buffer (look at "Queue size=" in logs)
docker compose logs --tail 20 trade-producer

# Check Postgres disk usage
docker compose exec postgres psql -U postgres trades -c "SELECT pg_size_pretty(pg_database_size('trades'));"
```

## Full reset (nuclear option)

```bash
# Stop everything, delete volumes, remove images
docker compose down -v --rmi local
```
