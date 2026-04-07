FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN python - <<'PY'
from pathlib import Path

requirements = Path("requirements.txt").read_text().splitlines()
filtered = [line for line in requirements if line and not line.startswith("apache-airflow")]
Path("producer-requirements.txt").write_text("\n".join(filtered) + "\n")
PY
RUN pip install --no-cache-dir -r producer-requirements.txt

COPY ingest/trades/ ./
