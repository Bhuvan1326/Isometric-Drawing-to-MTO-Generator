"""Health check — liveness probe."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/api/health")
def health() -> dict[str, str]:
    # Report the active provider so the frontend can show a "mock mode" badge.
    from app.config import settings

    return {"status": "ok", "provider": settings.vision_provider}
