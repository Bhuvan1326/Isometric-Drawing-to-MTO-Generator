"""MTO retrieval routes.

- GET /api/mto/{job_id}          -> job status + MTO JSON when ready
- GET /api/mto/{job_id}/csv      -> MTO as CSV download
"""

from __future__ import annotations

import csv
import io

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.models.api import JobResponse, JobState
from app.services.job_store import get_job_store

router = APIRouter()


@router.get("/api/mto/{job_id}", response_model=JobResponse)
def get_mto(job_id: str) -> JobResponse:
    job = get_job_store().get(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"detail": f"Job '{job_id}' not found", "code": "NOT_FOUND"},
        )
    return JobResponse(
        job_id=job.job_id,
        state=job.state,
        message=job.message,
        filename=job.filename,
        created_at=job.created_at,
        updated_at=job.updated_at,
        mto=job.mto,
    )


@router.get("/api/mto/{job_id}/csv")
def get_mto_csv(job_id: str) -> StreamingResponse:
    job = get_job_store().get(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"detail": f"Job '{job_id}' not found", "code": "NOT_FOUND"},
        )
    if job.state != JobState.DONE or job.mto is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "detail": f"Job is {job.state.value}, not ready for CSV",
                "code": "NOT_READY",
            },
        )

    csv_text = _mto_to_csv(job.mto)
    filename = f"mto_{job_id[:8]}.csv"
    return StreamingResponse(
        iter([csv_text]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# CSV column order — matches the MTOItem field order, with drawing meta and
# summary as separate sections. Excel opens this cleanly.
_CSV_COLUMNS = [
    "item_no", "category", "description", "size_nps", "schedule_rating",
    "material_spec", "end_type", "quantity", "unit", "length_m",
    "confidence", "remarks",
]


def _mto_to_csv(mto) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)

    # Drawing metadata header
    meta = mto.drawing_meta
    writer.writerow(["# Drawing Metadata"])
    writer.writerow(["drawing_no", meta.drawing_no or ""])
    writer.writerow(["revision", meta.revision or ""])
    writer.writerow(["line_number", meta.line_number or ""])
    writer.writerow(["nps", meta.nps or ""])
    writer.writerow(["material_class", meta.material_class or ""])
    writer.writerow(["service", meta.service or ""])
    writer.writerow([])

    # Items
    writer.writerow(_CSV_COLUMNS)
    for item in mto.items:
        writer.writerow([
            item.item_no, item.category.value, item.description,
            item.size_nps or "", item.schedule_rating or "",
            item.material_spec or "", item.end_type.value if item.end_type else "",
            item.quantity, item.unit, item.length_m if item.length_m is not None else "",
            item.confidence if item.confidence is not None else "",
            item.remarks or "",
        ])
    writer.writerow([])

    # Summary
    s = mto.summary
    writer.writerow(["# Summary"])
    writer.writerow(["total_pipe_length_m", s.total_pipe_length_m])
    writer.writerow(["fittings", s.fittings])
    writer.writerow(["flanges", s.flanges])
    writer.writerow(["valves", s.valves])
    writer.writerow(["gaskets", s.gaskets])
    writer.writerow(["bolt_sets", s.bolt_sets])
    writer.writerow(["field_welds", s.field_welds])
    writer.writerow([])
    writer.writerow(["# Source", mto.source])

    return buf.getvalue()
