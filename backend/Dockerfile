FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app
RUN apt-get update && apt-get install -y --no-install-recommends curl libpq-dev gcc gdal-bin libgdal-dev libgeos-dev && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml .
RUN python -m pip install --no-cache-dir .
COPY app/ ./app/
COPY migrations/ ./migrations/
COPY alembic.ini .
COPY data/ ./data/
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
