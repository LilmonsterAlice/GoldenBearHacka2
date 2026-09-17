"""Build a summary-first snapshot. Candidate consumption is not savings."""

import argparse
import json
from pathlib import Path

from analytics.exploration import audit_data, candidate_diagnostics
from analytics.load_data import load_official_data
from analytics.outcomes import build_summary
from analytics.pricing import Pricing


def build_snapshot(data, pricing=Pricing()):
    audit = audit_data(data)
    for key in ("duplicate_gpu_keys", "orphan_gpu_rows", "unmatched_job_findings",
                "gpu_count_mismatch_jobs", "job_card_hours_mismatch_jobs", "invalid_card_hours_rows"):
        if audit[key]:
            raise ValueError(f"Data integrity failure: {key}={audit[key]}")
    cohorts, overlaps = candidate_diagnostics(data)
    return {"summary": build_summary(data.jobs, pricing), "opportunities": [], "jobs": [],
            "metadata": {"producer": "CutScope analytics2 baseline v1", "stage": "summary-first",
                         "provenance": data.provenance, "data_quality": audit,
                         "candidate_diagnostics": cohorts.to_dict(orient="records"),
                         "candidate_overlap": overlaps.to_dict(orient="records"),
                         "methodology": "ANALYSIS_METHOD.md",
                         "pricing_basis": "User-configurable scenario rate, not a verified provider price book",
                         "limitations": ["Candidate cohort hours are consumption, not recoverable savings; do not sum overlapping cohorts.",
                                         "Time-resolved utilization and exact idle-onset timestamps are not available in these summary tables.",
                                         "Savings scenarios, downside estimates and primary interval attribution are not implemented yet."]}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", help="Official repository, track-2 folder or data folder")
    parser.add_argument("--output", type=Path, default=Path("generated/analysis.json"))
    parser.add_argument("--price", type=float, default=2.5)
    parser.add_argument("--price-book-version", default="cutscope-assumption-v1")
    args = parser.parse_args()
    pricing = Pricing(args.price, args.price_book_version)
    snapshot = build_snapshot(load_official_data(args.data_dir), pricing)
    encoded = json.dumps(snapshot, indent=2, allow_nan=False) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encoded)
    print(f"Wrote {args.output}: {snapshot['metadata']['data_quality']['job_count']:,} jobs; summary only, no savings claims.")


if __name__ == "__main__":
    main()
