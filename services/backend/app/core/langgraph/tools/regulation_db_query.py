"""SQL query tool for the document_extractions table.

Provides a LangChain tool that lets the agent run read-only SQL queries
against the document_extractions table in PostgreSQL.
"""

import json
from typing import Optional

import psycopg2
from langchain_core.tools import tool
from openai import OpenAI

from app.core.config import get_postgres_connection_kwargs, settings


ALLOWED_TABLE = "document_extractions"

SCHEMA_DESCRIPTION = """The document_extractions table has the following columns:
- id (SERIAL PRIMARY KEY)
- document_name (TEXT NOT NULL) — name of the source document
- page_number (INTEGER) — page within the document
- raw_text (TEXT) — extracted plain text from that page
- tables (JSONB, default []) — any tabular data extracted as JSON
- metadata (JSONB, default {}) — arbitrary key/value metadata
- embedding (vector(1536)) — text-embedding-3-small vector for semantic search
- created_at (TIMESTAMPTZ) — when the row was inserted

Useful indexes exist on document_name, metadata (GIN), and embedding (HNSW cosine).

For semantic similarity search use:
  ORDER BY embedding <=> '[...]' LIMIT k
"""


def _get_connection():
    return psycopg2.connect(**get_postgres_connection_kwargs())


def _get_openai_client() -> OpenAI:
    api_key = settings.OPENAI_API_KEY
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    base_url = settings.OPENAI_BASE_URL
    if base_url:
        return OpenAI(api_key=api_key, base_url=base_url)
    return OpenAI(api_key=api_key)


def _embed_text(text: str) -> list[float]:
    model = settings.LONG_TERM_MEMORY_EMBEDDER_MODEL
    client = _get_openai_client()
    response = client.embeddings.create(model=model, input=text)
    return response.data[0].embedding


@tool
def query_document_extractions(sql_query: str) -> str:
    """Execute a READ-ONLY SQL query against the document_extractions table.

    Use this tool to search, filter, and aggregate data from the
    document_extractions table which stores extracted text, tables, and
    metadata from processed documents.

    The table schema:
        id              SERIAL PRIMARY KEY
        document_name   TEXT NOT NULL
        page_number     INTEGER
        raw_text        TEXT
        tables          JSONB DEFAULT '[]'
        metadata        JSONB DEFAULT '{}'
        created_at      TIMESTAMPTZ DEFAULT NOW()

    Only SELECT statements are allowed. Do NOT issue INSERT, UPDATE, DELETE,
    DROP, or any DDL. The query MUST reference only document_extractions.

    Args:
        sql_query: A valid PostgreSQL SELECT statement.

    Returns:
        JSON-formatted query results (list of row dicts) or an error message.
    """
    normalized = sql_query.strip().rstrip(";").upper()

    forbidden = {"INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "CREATE", "GRANT", "REVOKE"}
    first_keyword = normalized.split()[0] if normalized.split() else ""
    if first_keyword in forbidden:
        return f"Error: Only SELECT queries are allowed. Got: {first_keyword}"

    if ALLOWED_TABLE not in sql_query.lower():
        return (
            f"Error: Query must reference the '{ALLOWED_TABLE}' table. "
            "No other tables are accessible."
        )

    try:
        conn = _get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(sql_query)
                columns = [desc[0] for desc in cur.description]
                rows = cur.fetchall()
                results = [dict(zip(columns, row)) for row in rows]
                return json.dumps(results, default=str, indent=2)
        finally:
            conn.close()
    except Exception as e:
        return f"SQL Error: {e}"


@tool
def vector_search_document_extractions(
    query: str,
    limit: int = 5,
    document_name: Optional[str] = None,
) -> str:
    """Run semantic search on document_extractions using embedding similarity.

    Args:
        query: Natural-language query text to search for.
        limit: Number of results to return (1-50).
        document_name: Optional exact document name filter.

    Returns:
        JSON-formatted top-k matches with similarity distance.
    """
    if not query or not query.strip():
        return "Error: query cannot be empty."

    if limit < 1 or limit > 50:
        return "Error: limit must be between 1 and 50."

    try:
        query_embedding = _embed_text(query.strip())
        embedding_literal = "[" + ",".join(str(value) for value in query_embedding) + "]"

        sql = """
            SELECT
                id,
                document_name,
                page_number,
                raw_text,
                tables,
                metadata,
                created_at,
                embedding <=> %s::vector AS cosine_distance
            FROM document_extractions
            WHERE (%s IS NULL OR document_name = %s)
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """

        conn = _get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, (embedding_literal, document_name, document_name, embedding_literal, limit))
                columns = [desc[0] for desc in cur.description]
                rows = cur.fetchall()
                results = [dict(zip(columns, row)) for row in rows]
                return json.dumps(results, default=str, indent=2)
        finally:
            conn.close()
    except Exception as e:
        return f"Vector search error: {e}"
