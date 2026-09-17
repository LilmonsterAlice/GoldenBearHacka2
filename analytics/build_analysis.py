"""Build verified baseline plus assumption-based idle-session scenarios."""

import argparse
import json
from pathlib import Path

from analytics.exploration import audit_data, candidate_diagnostics
from analytics.load_data import load_official_data
from analytics.outcomes import build_summary
from analytics.pricing import Pricing
from analytics.scenarios import IdlePolicy
from analytics.opportunities.idle_interactive import build_idle_opportunity


def build_snapshot(data, pricing=Pricing(), idle_policy=IdlePolicy()):
    audit = audit_data(data)
    for key in ("duplicate_gpu_keys", "orphan_gpu_rows", "unmatched_job_findings",
                "gpu_count_mismatch_jobs", "job_card_hours_mismatch_jobs", "invalid_card_hours_rows"):
        if audit[key]:
            raise ValueError(f"Data integrity failure: {key}={audit[key]}")
    cohorts, overlaps = candidate_diagnostics(data)
    summary = build_summary(data.jobs, pricing)
    opportunity, jobs, idle_analysis = build_idle_opportunity(data, pricing, summary["total_gpu_hours"], idle_policy)
    return {"summary": summary, "opportunities": [opportunity], "jobs": jobs,
            "metadata": {"producer": "CutScope analytics2 idle v2", "stage": "idle-interactive",
                         "idle_analysis": idle_analysis,
                         "provenance": data.provenance, "data_quality": audit,
                         "candidate_diagnostics": cohorts.to_dict(orient="records"),
                         "candidate_overlap": overlaps.to_dict(orient="records"),
                         "methodology": "ANALYSIS_METHOD.md",
                         "pricing_basis": "User-configurable scenario rate, not a verified provider price book",
                         "limitations": ["Candidate cohort hours are consumption, not recoverable savings; do not sum overlapping cohorts.",
                                         "Time-resolved utilization and exact idle-onset timestamps are not available in these summary tables.",
                                         "Idle reclaim is a session-cap proxy with uncalibrated realization; actual confidence and downside USD remain unknown.",
                                         "Only one primary opportunity is implemented; whole-job ownership conservatively prevents overlap."]}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", help="Official repository, track-2 folder or data folder")
    parser.add_argument("--output", type=Path, default=Path("generated/analysis.json"))
    parser.add_argument("--price", type=float, default=2.5)
    parser.add_argument("--price-book-version", default="cutscope-assumption-v1")
    parser.add_argument("--idle-retained-hours", type=float, default=4.)
    parser.add_argument("--idle-point-realization", type=float, default=.5)
    args = parser.parse_args()
    pricing = Pricing(args.price, args.price_book_version)
    policy = IdlePolicy(args.idle_retained_hours, args.idle_point_realization)
    snapshot = build_snapshot(load_official_data(args.data_dir), pricing, policy)
    encoded = json.dumps(snapshot, indent=2, allow_nan=False) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encoded)
    print(f"Wrote {args.output}: verified baseline plus modeled idle scenarios for {len(snapshot['jobs']):,} jobs; not verified cash savings.")


if __name__ == "__main__":
    main()
