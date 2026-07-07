"""API request/response models — separate from the domain MTO models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from app.models.mto import MTO


class JobState(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    ERROR = "error"


class JobStatus(BaseModel):
    """Polled job state."""

    job_id: str
    state: JobState
    message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class UploadResponse(BaseModel):
    job_id: str
    state: JobState
    filename: str


class JobResponse(BaseModel):
    """Full job envelope returned by GET /api/mto/{job_id}."""

    job_id: str
    state: JobState
    message: Optional[str] = None
    filename: str
    created_at: datetime
    updated_at: datetime
    mto: Optional[MTO] = None


class ErrorResponse(BaseModel):
    """Typed error envelope — every error response uses this shape."""

    detail: str
    code: str = Field(
        ...,
        description="Stable error code: BAD_FILE | OVERSIZED | UNREADABLE | LLM_TIMEOUT | LLM_FAILURE | NOT_FOUND | INTERNAL",
    )
    job_id: Optional[str] = None
