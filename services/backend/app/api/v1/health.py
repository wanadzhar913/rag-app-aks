"""Health-check endpoint."""

from fastapi import APIRouter, Depends

from app.api.v1.dependencies import get_db
from app.services.database import DatabaseService

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health(db: DatabaseService = Depends(get_db)):
    pg_ok = await db.health_check()
    return {
        "status": "healthy" if pg_ok else "degraded",
        "postgres": pg_ok,
    }
