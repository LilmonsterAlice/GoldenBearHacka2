from typing import Annotated

from fastapi import APIRouter, Query, Request

from backend.errors import APIError, ERROR_RESPONSES
from backend.models import OpportunityDetail, OpportunityList, OpportunitySummary

router = APIRouter(prefix="/api/opportunities", tags=["opportunities"], responses=ERROR_RESPONSES)


@router.get("", response_model=OpportunityList)
def list_opportunities(request: Request) -> dict:
    store = request.app.state.analysis_store
    metadata = store.get_pricing()
    fields = OpportunitySummary.model_fields
    return {"opportunities": [
        {**{key: record[key] for key in fields}, **metadata}
        for record in store.list_opportunities()
    ]}


@router.get("/{id}", response_model=OpportunityDetail)
def get_opportunity(
    id: str,
    request: Request,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict:
    store = request.app.state.analysis_store
    record = store.get_opportunity(id)
    if record is None:
        raise APIError(404, "OPPORTUNITY_NOT_FOUND", "Opportunity not found")
    total = len(record["jobs"])
    record["jobs"] = record["jobs"][offset:offset + limit]
    return {**record, **store.get_pricing(), "jobs_pagination": {"total": total, "offset": offset, "limit": limit}}
