# Analysis Method — Shared Invariants

Person 1 owns the detailed formulas and inclusion/exclusion methodology. This
file begins with the non-negotiable rules agreed by the team:

1. CANCELLED is a scenario decision, not automatic waste.
2. Finding `impact_gpu_hours` overlaps and must not be naively summed.
3. `lost`, `consumed`, `degraded`, and `unused_capacity` are distinct concepts.
4. A physical job-hour may enter at most one primary savings opportunity.
5. A job may retain multiple supporting finding IDs without duplicate pricing.
6. Cost analysis uses GPU-hour weighting rather than row weighting.
7. Card imbalance is calculated from `gpus.parquet`, not job-level averages.
8. Hardware analysis uses attempt history, `hit_node_failure`, and
   `nodefail_nodes`, not final state/placement alone.
9. Savings outputs include low/point/high, confidence, basis, and caveats.
10. Every result describes the four-month workload sample.

## First method to document

`idle-interactive-session`: Person 1 will add its exact inclusion rules,
deduplication priority, interval interpretation, and cost-if-wrong assumptions.
