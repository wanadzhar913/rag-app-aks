"""
Docling pipeline: download a PDF from S3, extract text & tables,
generate embeddings, and ingest into PostgreSQL.
"""

import json
import logging
import os
import re
from datetime import UTC, datetime
from pathlib import Path

import psycopg2
from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.pipeline.threaded_standard_pdf_pipeline import ThreadedStandardPdfPipeline
from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
from docling.datamodel.pipeline_options import ThreadedPdfPipelineOptions
from openai import OpenAI

from pipeline.config import settings
from pipeline.storage import download_to_tempfile

# Configure accelerator options for GPU
accelerator_options = AcceleratorOptions(
    device=AcceleratorDevice.AUTO,
)

pipeline_options = ThreadedPdfPipelineOptions(
    accelerator_options=accelerator_options,
    ocr_batch_size=4,
    layout_batch_size=32,
    table_batch_size=4,
)
pipeline_options.do_ocr = False # We are not using OCR as our PDFs have a selectable text layer (not scanned e.g., docling-project/docling#2726)

logger = logging.getLogger(__name__)


def _pg_config() -> dict:
    return {
        "host": settings.POSTGRES_HOST,
        "port": settings.POSTGRES_PORT,
        "dbname": settings.POSTGRES_DB,
        "user": settings.POSTGRES_USER,
        "password": settings.POSTGRES_PASSWORD,
    }


def _openai_client() -> OpenAI:
    return OpenAI(
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL,
    )


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    client = _openai_client()
    all_embeddings: list[list[float]] = []
    for i in range(0, len(texts), settings.EMBEDDING_BATCH_SIZE):
        batch = texts[i : i + settings.EMBEDDING_BATCH_SIZE]
        batch = [t[:8000] if t else " " for t in batch]
        response = client.embeddings.create(model=settings.EMBEDDING_MODEL, input=batch)
        all_embeddings.extend([d.embedding for d in response.data])
    return all_embeddings


def extract_tables_from_result(result) -> list[dict]:
    doc = result.document
    tables = []
    for table_item in doc.tables:
        try:
            table_data = table_item.export_to_dataframe(doc=doc)
        except TypeError:
            table_data = table_item.export_to_dataframe()
        tables.append({
            "headers": list(table_data.columns),
            "rows": table_data.values.tolist(),
            "num_rows": len(table_data),
            "num_cols": len(table_data.columns),
        })
    return tables


def build_page_text_map(result) -> dict[int, str]:
    doc = result.document
    page_texts: dict[int, list[str]] = {}
    for item, _level in doc.iterate_items():
        prov_pages = set()
        if hasattr(item, "prov") and item.prov:
            for prov in item.prov:
                prov_pages.add(prov.page_no)

        text = ""
        if hasattr(item, "text") and item.text:
            text = item.text
        else:
            try:
                text = item.export_to_markdown(doc=doc)
            except (TypeError, AttributeError):
                continue

        if not text:
            continue

        if prov_pages:
            for pg in sorted(prov_pages):
                page_texts.setdefault(pg, []).append(text)
        else:
            page_texts.setdefault(0, []).append(text)

    return {pg: "\n\n".join(parts) for pg, parts in page_texts.items()}


def build_metadata(result, pdf_path: Path, s3_key: str) -> dict:
    num_pages = result.document.num_pages() if hasattr(result.document, "num_pages") else None
    return {
        "source_file": pdf_path.name,
        "s3_key": s3_key,
        "num_pages": num_pages,
        "num_tables": len(result.document.tables),
        "input_format": "pdf",
    }


def parse_date_from_filename(name: str) -> str | None:
    match = re.match(r"(\d{8})", name)
    if match:
        raw = match.group(1)
        return f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"
    return None


def insert_rows(conn, rows: list[dict]):
    with conn.cursor() as cur:
        for row in rows:
            embedding_str = (
                f"[{','.join(str(v) for v in row['embedding'])}]"
                if row.get("embedding")
                else None
            )
            cur.execute(
                """
                INSERT INTO document_extractions
                    (created_at, document_name, page_number, raw_text, tables, metadata, embedding)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    row.get("created_at") or datetime.now(UTC),
                    row["document_name"],
                    row["page_number"],
                    row["raw_text"],
                    json.dumps(row["tables"]),
                    json.dumps(row["metadata"]),
                    embedding_str,
                ),
            )
    conn.commit()


def process_file(s3_key: str, original_filename: str | None = None) -> dict:
    """Download a PDF from S3, extract, embed, and insert into Postgres.

    Args:
        s3_key: Object key in the S3 bucket.
        original_filename: The name the user uploaded under (used as
            document_name).  Falls back to the S3 key basename.
    """
    doc_name = original_filename or Path(s3_key).name
    logger.info("processing: %s (s3_key=%s)", doc_name, s3_key)

    local_path = download_to_tempfile(s3_key)
    try:
        converter = DocumentConverter(
            allowed_formats=[InputFormat.PDF],  
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_cls=ThreadedStandardPdfPipeline,
                    pipeline_options=pipeline_options,
                )
            }
        )
        result = converter.convert(str(local_path))

        full_markdown = result.document.export_to_markdown()
        tables = extract_tables_from_result(result)
        page_text_map = build_page_text_map(result)
        base_meta = build_metadata(result, local_path, s3_key)
        base_meta["original_filename"] = doc_name

        report_date = parse_date_from_filename(doc_name)
        if report_date:
            base_meta["report_date"] = report_date

        rows: list[dict] = []
        if page_text_map:
            for page_no in sorted(page_text_map.keys()):
                meta = {**base_meta, "level": "page"}
                rows.append({
                    "document_name": doc_name,
                    "page_number": page_no,
                    "raw_text": page_text_map[page_no],
                    "tables": list(tables) if page_no == min(page_text_map.keys()) else [],
                    "metadata": meta,
                })

        doc_meta = {**base_meta, "level": "document"}
        rows.append({
            "document_name": doc_name,
            "page_number": None,
            "raw_text": full_markdown,
            "tables": tables,
            "metadata": doc_meta,
        })

        texts_to_embed = [r["raw_text"] or "" for r in rows]
        logger.info("  generating embeddings for %d chunks …", len(texts_to_embed))
        embeddings = generate_embeddings(texts_to_embed)
        for row, emb in zip(rows, embeddings):
            row["embedding"] = emb

        conn = psycopg2.connect(**_pg_config())
        try:
            insert_rows(conn, rows)
        finally:
            conn.close()

        logger.info(
            "  pages=%d  tables=%d  rows_inserted=%d",
            len(page_text_map),
            len(tables),
            len(rows),
        )

        return {
            "status": "completed",
            "document_name": doc_name,
            "s3_key": s3_key,
            "pages_extracted": len(page_text_map),
            "tables_found": len(tables),
            "rows_inserted": len(rows),
        }
    finally:
        os.unlink(local_path)
