# Backend (`services/backend`)

## a) System architecture
- FastAPI app exposes HTTP endpoints (`/api/v1`).
- Startup wires DB, Redis cache, LangGraph agent, RabbitMQ publisher, and object storage bucket checks.
- Uses PostgreSQL (+ pgvector) for relational + vector-aware retrieval workflows.
- Publishes ingestion jobs to RabbitMQ for async document processing.

Sample interaction flow:

```mermaid
flowchart LR
  UI[Web Frontend] -->|HTTP /api/v1| API[FastAPI Backend]
  API -->|read/write| PG[(PostgreSQL + pgvector)]
  API -->|upload document| S3[(S3/MinIO Blob Storage)]
  API -->|cache/session| REDIS[(Redis)]
  API -->|publish job| MQ[(RabbitMQ)]
  MQ -->|consume job| INGEST[Ingestion Worker]
  S3[(S3/MinIO Blob Storage)] -->|read/write files| INGEST
  INGEST -->|update status + extractions| PG
  API -->|query agent/tools| LGRAPH[LangGraph Agent]
```

## b) Setup commands
```bash
# From repo root: start dependencies + backend container
make up

# Stream backend logs
make backend-logs

# Run DB migrations
make migrate
```

## c) Why these technologies
- **FastAPI**: fast async API development with type-driven request/response handling.
- **PostgreSQL + pgvector**: one data store for transactional and embedding search needs.
- **RabbitMQ**: reliable queueing to decouple user requests from heavy ingestion work.
- **Redis**: low-latency caching/session support for responsive APIs.
- **LangGraph/LangChain stack**: structured orchestration for multi-step agent behavior.
