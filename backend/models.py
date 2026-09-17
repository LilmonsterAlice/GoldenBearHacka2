"""Read API models; see API_STAGE2.md for provisional team decisions."""

from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr, field_validator, model_validator

NonNegative = Annotated[float, Field(ge=0, allow_inf_nan=False)]
Percentage = Annotated[float, Field(ge=0, le=100, allow_inf_nan=False)]
Count = Annotated[StrictInt, Field(ge=0)]
Identifier = Annotated[StrictStr, Field(min_length=1, pattern=r"^\S+$")]
Confidence = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class Outcome(ContractModel):
    name: Annotated[StrictStr, Field(min_length=1)]
    jobs: Count | None
    gpu_hours: NonNegative | None
    cost_usd: NonNegative | None
    capacity_percent: Percentage | None


class Summary(ContractModel):
    total_gpu_hours: NonNegative | None
    total_cost_usd: NonNegative | None
    price_per_gpu_hour: NonNegative | None
    price_book_version: Annotated[StrictStr, Field(min_length=1)]
    completed_percent: Percentage | None
    outcomes: list[Outcome]
    scope_caveat: Annotated[StrictStr, Field(min_length=1)]


class Pricing(ContractModel):
    price_per_gpu_hour: NonNegative | None
    price_book_version: Annotated[StrictStr, Field(min_length=1)]


class OpportunitySummary(ContractModel):
    id: Identifier
    title: Annotated[StrictStr, Field(min_length=1)]
    action: StrictStr | None
    owner: StrictStr | None
    savings_usd_low: NonNegative | None
    savings_usd_high: NonNegative | None
    gpu_hours_low: NonNegative | None
    gpu_hours_high: NonNegative | None
    capacity_percent_low: Percentage | None
    capacity_percent_high: Percentage | None
    confidence: Confidence | None
    risk_level: StrictStr | None
    job_count: Count

    @model_validator(mode="after")
    def ordered_ranges(self):
        for prefix in ("savings_usd", "gpu_hours", "capacity_percent"):
            low, high = getattr(self, f"{prefix}_low"), getattr(self, f"{prefix}_high")
            if low is not None and high is not None and low > high:
                raise ValueError(f"{prefix}_low cannot exceed {prefix}_high")
        return self


class CostIfWrong(ContractModel):
    description: StrictStr | None
    usd_low: NonNegative | None
    usd_high: NonNegative | None
    reversible: bool | None
    mitigation: StrictStr | None

    @model_validator(mode="after")
    def ordered_range(self):
        if self.usd_low is not None and self.usd_high is not None and self.usd_low > self.usd_high:
            raise ValueError("usd_low cannot exceed usd_high")
        return self


class JobReference(ContractModel):
    job_id: Count


class OpportunityRecord(OpportunitySummary):
    method: StrictStr | None
    basis: StrictStr | None
    caveats: list[StrictStr]
    cost_if_wrong: CostIfWrong
    jobs: list[JobReference]


class JobRecord(ContractModel):
    job_id: Count
    state: StrictStr | None
    gpu_count: Count | None
    gpu_hours: NonNegative | None
    cost_usd: NonNegative | None
    sm_util_avg: Percentage | None
    sm_util_max: Percentage | None
    walltime_hours: NonNegative | None
    primary_node: StrictStr | None
    # Preserve upstream finding payloads without inventing a MantisGrid schema.
    findings: list[dict[str, Any]]


class OpportunityCard(OpportunitySummary, Pricing):
    pass


class OpportunityList(ContractModel):
    opportunities: list[OpportunityCard]


class JobPagination(ContractModel):
    total: Count
    offset: Count
    limit: Annotated[StrictInt, Field(ge=1, le=100)]


class OpportunityDetail(OpportunityRecord, Pricing):
    # API contract uses integer IDs; stored/AI-context references remain objects.
    jobs: list[Count]
    jobs_pagination: JobPagination


class JobDetail(JobRecord, Pricing):
    pass


class ErrorDetail(ContractModel):
    code: StrictStr
    message: StrictStr
    retryable: bool


class ErrorResponse(ContractModel):
    error: ErrorDetail


class ChatRequest(ContractModel):
    question: Annotated[StrictStr, Field(min_length=1, max_length=4000)]
    opportunity_id: Identifier | None = None
    job_id: Count | None = None

    @field_validator("question")
    @classmethod
    def nonblank_question(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Question cannot be blank")
        return value


class ChatResponse(ContractModel):
    answer: Annotated[StrictStr, Field(min_length=1)]
    evidence: list[dict[str, Any]]
    risk: StrictStr
    recommendation: StrictStr
    confidence: Confidence | None
    finding_ids: list[Identifier]
    job_ids: list[Count]
    caveats: list[StrictStr]


class AnalysisSnapshot(ContractModel):
    summary: Summary
    opportunities: list[OpportunityRecord]
    jobs: list[JobRecord]
    # Optional producer metadata is file-only and never part of API responses.
    metadata: dict[str, Any] = Field(default_factory=dict)
