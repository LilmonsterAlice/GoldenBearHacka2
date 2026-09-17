from typing import Annotated

from fastapi import APIRouter, Path, Request

from backend.errors import APIError, ERROR_RESPONSES
from backend.models import JobDetail

router = APIRouter(prefix="/api/jobs", tags=["jobs"], responses=ERROR_RESPONSES)


@router.get("/{job_id}", response_model=JobDetail)
def get_job(job_id: Annotated[int, Path(ge=0)], request: Request) -> dict:
    store = request.app.state.analysis_store
    record = store.get_job(job_id)
    if record is None:
        raise APIError(404, "JOB_NOT_FOUND", "Job not found")
    return {**record, **store.get_pricing()}
