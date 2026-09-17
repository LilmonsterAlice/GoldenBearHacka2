"""Build a summary-only snapshot from a teammate's local prepared jobs file."""

import argparse
import json
from pathlib import Path
import sys
import tempfile

# Support both module invocation and direct execution from another directory.
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from analytics.config import DataPaths, PROJECT_ROOT, project_path
from analytics.load_data import load_findings, load_gpus, load_jobs
from analytics.opportunity_analysis import build_opportunities
from analytics.outcomes import calculate_outcomes, validate_summary_jobs
from analytics.pricing import PRICE_BOOK_VERSION, PRICE_PER_GPU_HOUR, gpu_hours_to_usd, validate_price

OUTPUT_PATH = PROJECT_ROOT / "generated/analysis.json"


def build_summary(jobs, *, price_per_gpu_hour=PRICE_PER_GPU_HOUR, price_book_version=None):
    jobs = validate_summary_jobs(jobs)
    price = validate_price(price_per_gpu_hour)
    version = price_book_version if price_book_version is not None else (
        PRICE_BOOK_VERSION if price == PRICE_PER_GPU_HOUR else "custom-rate"
    )
    if not isinstance(version, str) or not version.strip():
        raise ValueError("Price book version must be a nonempty string")
    hours = float(jobs["gpu_hours"].sum())
    outcomes = calculate_outcomes(jobs, price)
    completed = next((outcome for outcome in outcomes if outcome["name"] == "COMPLETED"), None)
    return {
        "total_gpu_hours": hours,
        "total_cost_usd": gpu_hours_to_usd(hours, price),
        "price_per_gpu_hour": price,
        "price_book_version": version,
        "completed_percent": completed["capacity_percent"] if completed is not None else (0.0 if hours > 0 else None),
        "outcomes": outcomes,
        "scope_caveat": "Four-month workload sample",
    }


def write_analysis(analysis: dict, output_path: str | Path) -> Path:
    """Strict JSON and atomic replacement avoid half-written backend snapshots."""
    content = json.dumps(analysis, indent=2, allow_nan=False) + "\n"
    destination = project_path(output_path)
    if destination.suffix.lower() != ".json":
        raise ValueError("Analysis output must use a .json extension")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=destination.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(content)
        # Readable by the non-root backend container when mounted read-only.
        temporary.chmod(0o644)
        temporary.replace(destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return destination


def build_analysis(*, jobs_path=None, gpus_path=None, findings_path=None, data_dir=None, output_path=None,
                   price_per_gpu_hour=PRICE_PER_GPU_HOUR, price_book_version=None, with_opportunities=False):
    paths = DataPaths.resolve(data_dir=data_dir, jobs_path=jobs_path, gpus_path=gpus_path, findings_path=findings_path)
    selected = paths.jobs
    destination = project_path(output_path if output_path is not None else OUTPUT_PATH)
    if selected == destination:
        raise ValueError("Analysis output must not overwrite the input jobs file")
    jobs = load_jobs(selected)
    summary = build_summary(jobs, price_per_gpu_hour=price_per_gpu_hour, price_book_version=price_book_version)
    analysis = {
        "summary": summary,
        "opportunities": [],
        "jobs": [],
        "metadata": {"producer": "cutscope-analytics", "stage": "summary-only"},
    }
    if with_opportunities:
        opportunities, evidence_jobs, audit = build_opportunities(
            validate_summary_jobs(jobs), load_gpus(paths.gpus), load_findings(paths.findings),
            price_per_gpu_hour=summary["price_per_gpu_hour"], total_gpu_hours=summary["total_gpu_hours"],
        )
        analysis["opportunities"] = opportunities
        analysis["jobs"] = evidence_jobs
        analysis["metadata"] = {"producer": "cutscope-analytics", "stage": "evidence-backed", **audit}
    write_analysis(analysis, destination)
    return analysis


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", help="Your existing official data directory (or CUTSCOPE_DATA_DIR)")
    parser.add_argument("--jobs-path", help="Explicit prepared jobs parquet (or CUTSCOPE_JOBS_PATH)")
    parser.add_argument("--gpus-path", help="Explicit per-card GPU parquet (or CUTSCOPE_GPUS_PATH)")
    parser.add_argument("--findings-path", help="Explicit findings JSON (or CUTSCOPE_FINDINGS_PATH)")
    parser.add_argument("--with-opportunities", action="store_true", help="Build four evidence-backed opportunity estimates")
    parser.add_argument("--output", default=str(OUTPUT_PATH), help="Output JSON path; default generated/analysis.json")
    parser.add_argument("--price-per-gpu-hour", type=float, default=PRICE_PER_GPU_HOUR)
    parser.add_argument("--price-book-version")
    parser.add_argument("--check-data", action="store_true", help="Check jobs file/schema without generating output")
    args = parser.parse_args(argv)
    try:
        paths = DataPaths.resolve(data_dir=args.data_dir, jobs_path=args.jobs_path,
                                  gpus_path=args.gpus_path, findings_path=args.findings_path)
        if args.check_data:
            jobs = validate_summary_jobs(load_jobs(paths.jobs))
            print(f"Jobs data ready: {len(jobs)} rows. No output written.")
        else:
            result = build_analysis(jobs_path=paths.jobs, gpus_path=paths.gpus, findings_path=paths.findings,
                                    output_path=args.output, with_opportunities=args.with_opportunities,
                                    price_per_gpu_hour=args.price_per_gpu_hour, price_book_version=args.price_book_version)
            print(f"Analysis written to: {project_path(args.output)}")
            print(f"{len(result['opportunities'])} opportunities; {len(result['jobs'])} evidence jobs")
    except (OSError, ValueError, ImportError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
