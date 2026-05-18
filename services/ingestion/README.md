# Ingestion (`services/ingestion`)

## a) System architecture
- Worker process consumes RabbitMQ `document_ingestion` jobs.
- Fetches source files from S3-compatible storage and runs extraction pipeline.
- Writes ingestion status/results back to PostgreSQL so backend can track progress.
- Runs independently from API service for isolated scaling and retries.

## b) Setup commands
```bash
# From repo root: start full local stack (includes ingestion worker)
make up

# Stream ingestion worker logs
make ingestion-logs

# Trigger an ingestion job via backend upload endpoint
make upload PDF=path/to/file.pdf
```

## c) Why these technologies
- **RabbitMQ (pika)**: durable, explicit ack/nack semantics for background job reliability.
- **Docling**: document parsing pipeline suited for mixed PDF/text extraction.
- **PostgreSQL**: persistent source of truth for ingestion job lifecycle state.
- **S3-compatible storage (MinIO/Azure-backed)**: simple object storage interface across local and cloud.
