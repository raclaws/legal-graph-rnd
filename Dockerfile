FROM python:3.12-slim AS base

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY backend/ backend/
COPY src/ src/
COPY scripts/seed_sqlite.py scripts/seed_sqlite.py
COPY corpus/raw/ corpus/raw/

# Seed the SQLite DB at build time
RUN mkdir -p data && python -m scripts.seed_sqlite --force

# Move DB to a location the volume mount won't hide
RUN mv data/legal.db /app/_seed_legal.db && rm -rf corpus/raw scripts/seed_sqlite.py

COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
