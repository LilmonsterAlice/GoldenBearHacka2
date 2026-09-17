from typing import Annotated

from fastapi import APIRouter, Query, Request

from backend.errors import APIError, ERROR_RESPONSES
from backend.models import OpportunityDetail, OpportunityList

router = APIRouter(prefix="/api/opportunities", tags=["opportunities"], responses=ERROR_RESPONSES)


@router.get("", response_model=OpportunityList)
def list_opportunities(request: Request) -> dict:
    store = request.app.state.analysis_store
    metadata = store.get_pricing()
    return {"opportunities": [
        {**record, **metadata} for record in store.list_opportunity_cards()
    ]}


@router.get("/{id}", response_model=OpportunityDetail)
def get_opportunity(
    id: str,
    request: Request,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict:
    store = request.app.state.analysis_store
    record = store.get_opportunity_page(id, offset, limit)
    if record is None:
        raise APIError(404, "OPPORTUNITY_NOT_FOUND", "Opportunity not found")
    return {**record, **store.get_pricing()}
