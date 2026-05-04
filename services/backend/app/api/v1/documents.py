"""Endpoints for uploading documents and browsing extractions."""

import uuid
from typing import Optional

import psycopg2
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile

from app.api.v1.dependencies import get_db, get_rabbitmq
from app.core.config import get_postgres_connection_kwargs
from app.schemas.documents import (
    DocumentExtractionResponse,
    IngestionJobResponse,
    DocumentSummary,
    PaginatedResponse,
)
from app.services.database import DatabaseService
from app.services.rabbitmq import RabbitMQPublisher
from app.services.storage import upload_file

router = APIRouter(prefix="/documents", tags=["Document Ingestion"])

ALLOWED_CONTENT_TYPES = {"application/pdf"}


def _get_connection():
    return psycopg2.connect(**get_postgres_connection_kwargs())


def _rows_to_dicts(cursor) -> list[dict]:
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _to_ingestion_job_response(job) -> IngestionJobResponse:
    return IngestionJobResponse(
        id=job.id,
        s3_key=job.s3_key,
        original_filename=job.original_filename,
        status=job.status,
        error_message=job.error_message,
        created_at=str(job.created_at) if job.created_at else None,
        started_at=str(job.started_at) if job.started_at else None,
        completed_at=str(job.completed_at) if job.completed_at else None,
    )

# ── Upload ───────────────────────────────────────────────────────────

@router.post("/upload", status_code=202)
async def upload_document(
    file: UploadFile,
    rmq: RabbitMQPublisher = Depends(get_rabbitmq),
    db: DatabaseService = Depends(get_db),
):
    """Accept a PDF, store it in S3/MinIO, and queue it for ingestion.
    Returns 202 immediately."""
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{file.content_type}'. Only PDF is accepted.",
        )

    contents = await file.read()
    filename = file.filename or "document.pdf"

    s3_key = upload_file(contents, filename, content_type=file.content_type)
    job_id = str(uuid.uuid4())
    await db.create_ingestion_job(job_id=job_id, s3_key=s3_key, original_filename=filename)

    try:
        await rmq.publish_file_ingestion(job_id=job_id, s3_key=s3_key, original_filename=filename)
    except Exception as exc:
        await db.update_ingestion_job_status(
            job_id,
            "failed",
            error_message=str(exc),
            completed=True,
        )
        raise

    return {
        "job_id": job_id,
        "status": "accepted",
        "filename": filename,
        "s3_key": s3_key,
        "size_bytes": len(contents),
    }


@router.post("/upload/batch", status_code=202)
async def upload_documents_batch(
    files: list[UploadFile],
    rmq: RabbitMQPublisher = Depends(get_rabbitmq),
    db: DatabaseService = Depends(get_db),
):
    """Upload multiple PDFs in one request.  Each file is stored in S3
    and queued as a separate ingestion job."""
    results = []
    for file in files:
        if file.content_type not in ALLOWED_CONTENT_TYPES:
            results.append({
                "filename": file.filename,
                "status": "rejected",
                "reason": f"Unsupported type '{file.content_type}'",
            })
            continue

        contents = await file.read()
        filename = file.filename or "document.pdf"

        s3_key = upload_file(contents, filename, content_type=file.content_type)
        job_id = str(uuid.uuid4())
        await db.create_ingestion_job(job_id=job_id, s3_key=s3_key, original_filename=filename)

        try:
            await rmq.publish_file_ingestion(job_id=job_id, s3_key=s3_key, original_filename=filename)
        except Exception as exc:
            await db.update_ingestion_job_status(
                job_id,
                "failed",
                error_message=str(exc),
                completed=True,
            )
            results.append({
                "job_id": job_id,
                "filename": filename,
                "status": "failed",
                "reason": str(exc),
                "s3_key": s3_key,
                "size_bytes": len(contents),
            })
            continue

        results.append({
            "job_id": job_id,
            "filename": filename,
            "status": "accepted",
            "s3_key": s3_key,
            "size_bytes": len(contents),
        })

    accepted = sum(1 for r in results if r["status"] == "accepted")
    return {"queued": accepted, "total": len(files), "files": results}


# ── Read endpoints ───────────────────────────────────────────────────

@router.get("", response_model=list[DocumentSummary])
async def list_documents():
    """List all unique documents with summary info."""
    conn = _get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    document_name,
                    COUNT(*) FILTER (WHERE page_number IS NOT NULL) AS total_pages,
                    COUNT(*) AS total_rows,
                    BOOL_OR(tables != '[]'::jsonb) AS has_tables,
                    MIN(metadata->>'report_date') AS report_date,
                    MIN(created_at) AS created_at
                FROM document_extractions
                GROUP BY document_name
                ORDER BY MIN(created_at) DESC
            """)
            rows = _rows_to_dicts(cur)
            return [
                DocumentSummary(
                    document_name=r["document_name"],
                    total_pages=r["total_pages"],
                    total_rows=r["total_rows"],
                    has_tables=r["has_tables"] or False,
                    report_date=r["report_date"],
                    created_at=str(r["created_at"]) if r["created_at"] else None,
                )
                for r in rows
            ]
    finally:
        conn.close()


@router.get("/jobs/{job_id}", response_model=IngestionJobResponse)
async def get_ingestion_job(job_id: str, db: DatabaseService = Depends(get_db)):
    job = await db.get_ingestion_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Ingestion job not found")
    return _to_ingestion_job_response(job)


@router.get("/extractions", response_model=PaginatedResponse)
async def list_extractions(
    document_name: Optional[str] = Query(None, description="Filter by document name"),
    page_number: Optional[int] = Query(None, description="Filter by page number"),
    search: Optional[str] = Query(None, description="Full-text search in raw_text"),
    limit: int = Query(20, ge=1, le=100, description="Max items to return"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
):
    """Paginated listing of document extractions with optional filters."""
    conn = _get_connection()
    try:
        conditions: list[str] = []
        params: list = []

        if document_name:
            conditions.append("document_name = %s")
            params.append(document_name)
        if page_number is not None:
            conditions.append("page_number = %s")
            params.append(page_number)
        if search:
            conditions.append("raw_text ILIKE %s")
            params.append(f"%{search}%")

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM document_extractions {where}", params)
            total = cur.fetchone()[0]

            cur.execute(
                f"""
                SELECT id, document_name, page_number, raw_text, tables, metadata, created_at
                FROM document_extractions
                {where}
                ORDER BY document_name, page_number NULLS LAST
                LIMIT %s OFFSET %s
                """,
                params + [limit, offset],
            )
            rows = _rows_to_dicts(cur)

        items = [
            DocumentExtractionResponse(
                id=r["id"],
                document_name=r["document_name"],
                page_number=r["page_number"],
                raw_text=r["raw_text"],
                tables=r["tables"],
                metadata=r["metadata"],
                created_at=str(r["created_at"]) if r["created_at"] else None,
            )
            for r in rows
        ]
        return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)
    finally:
        conn.close()


@router.get("/extractions/{extraction_id}", response_model=DocumentExtractionResponse)
async def get_extraction(extraction_id: int):
    """Get a single extraction by ID."""
    conn = _get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, document_name, page_number, raw_text, tables, metadata, created_at
                FROM document_extractions
                WHERE id = %s
                """,
                (extraction_id,),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Extraction not found")
            columns = [desc[0] for desc in cur.description]
            r = dict(zip(columns, row))

        return DocumentExtractionResponse(
            id=r["id"],
            document_name=r["document_name"],
            page_number=r["page_number"],
            raw_text=r["raw_text"],
            tables=r["tables"],
            metadata=r["metadata"],
            created_at=str(r["created_at"]) if r["created_at"] else None,
        )
    finally:
        conn.close()


@router.get("/extractions/{extraction_id}/tables")
async def get_extraction_tables(extraction_id: int):
    """Get only the tables from a specific extraction."""
    conn = _get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT document_name, page_number, tables FROM document_extractions WHERE id = %s",
                (extraction_id,),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Extraction not found")

        return {
            "document_name": row[0],
            "page_number": row[1],
            "tables": row[2],
        }
    finally:
        conn.close()
