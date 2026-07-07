"""Upload route — POST /api/upload.

We chose a single synchronous-ish flow: upload kicks off a background task
(via FastAPI's BackgroundTasks) and returns a job_id immediately. The client
polls GET /api/mto/{job_id} until state is DONE or ERROR.

An alternative would be a single synchronous POST /api/extract that blocks
until the MTO is ready. We rejected that because vision LLM calls can take
10-60s, and a synchronous endpoint would hit typical proxy/Netlify timeouts
and give a poor UX (no progress feedback). The async job pattern is barely
more code and degrades gracefully.
"""

from __future__ import annotations

import traceback

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from app.models.api import JobState, UploadResponse
from app.pipeline import get_pipeline
from app.pipeline.base import PipelineError
from app.services.file_service import FileService, FileValidationError, verify_magic_bytes
from app.services.job_store import get_job_store

router = APIRouter()


@router.post(
    "/api/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
) -> UploadResponse:
    # --- Server-side validation (never trust the client) ---
    content = await file.read()
    try:
        FileService().validate(
            filename=file.filename or "upload",
            content_type=file.content_type or "",
            size=len(content),
        )
        verify_magic_bytes(content)
    except FileValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"detail": str(e), "code": e.code},
        )

    # --- Persist the file ---
    path = FileService().save(filename=file.filename or "upload", content=content)

    # --- Create the job ---
    store = get_job_store()
    job = store.create(file.filename or "upload")
    store.update(job.job_id, state=JobState.PROCESSING, message="Queued")

    # --- Kick off the pipeline in the background ---
    background_tasks.add_task(_run_pipeline, job_id=job.job_id, file_path=path)

    return UploadResponse(job_id=job.job_id, state=JobState.PROCESSING, filename=job.filename)


def _run_pipeline(*, job_id: str, file_path: str) -> None:
    """Background task: run the pipeline and update the job store."""
    from pathlib import Path

    store = get_job_store()
    try:
        pipeline = get_pipeline()
        mto = pipeline.extract(Path(file_path), filename=Path(file_path).name)
        store.update(job_id, state=JobState.DONE, message=f"Extracted via {pipeline.name}", mto=mto)
    except PipelineError as e:
        store.update(job_id, state=JobState.ERROR, message=f"{e.code}: {e}")
    except Exception as e:  # noqa: BLE001 — last-resort guard so the job isn't stuck in PROCESSING
        store.update(
            job_id,
            state=JobState.ERROR,
            message=f"INTERNAL: {e.__class__.__name__}: {e}",
        )
        traceback.print_exc()
    finally:
        # Clean up the uploaded file — we don't need it after extraction.
        try:
            Path(file_path).unlink()
        except FileNotFoundError:
            pass
