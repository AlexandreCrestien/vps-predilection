FROM python:3.12

WORKDIR /app

COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api/ ./api/
COPY scripts/ ./scripts/
COPY data/ ./data/

ENV PYTHONPATH=/app/api

ENV DATABASE_URL=postgresql://postgres:postgres@postgres_container:5432/predilection

CMD ["python", "scripts/ingest.py"]