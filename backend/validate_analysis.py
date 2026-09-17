"""Read-only snapshot validation and optional in-process API compatibility check."""

import argparse
import json
import os
from pathlib import Path
import sys
from urllib.parse import quote

from backend.config import PROJECT_ROOT, STAGE1_MOCK, Settings
from backend.models import AnalysisSnapshot, JobDetail, OpportunityDetail, OpportunityList, Summary
from backend.services.analysis_store import AnalysisLoadError, AnalysisStore


class CompatibilityError(RuntimeError):
    pass


def check_api(settings: Settings, store: AnalysisStore) -> int:
    """Check read routes using supplied data. No live AI/network calls or writes."""
    try:
        from fastapi.testclient import TestClient
    except ImportError as exc:
        raise CompatibilityError("Install backend/requirements-dev.txt for --check-api") from exc
    from backend.application import create_app

    requests = 0
    with TestClient(create_app(settings)) as client:
        def get(path, model):
            nonlocal requests
            response = client.get(path)
            requests += 1
            if response.status_code != 200:
                raise CompatibilityError("Read API compatibility check failed")
            model.model_validate(response.json())
            if response.headers.get("X-Analysis-Mode") != settings.analysis_mode:
                raise CompatibilityError("Analysis-mode header mismatch")
            return response.json()

        summary = get("/api/summary", Summary)
        if summary != store.get_summary().model_dump():
            raise CompatibilityError("Summary values changed in the API")
        expected_cards = [{**card, **store.get_pricing()} for card in store.list_opportunity_cards()]
        cards = get("/api/opportunities", OpportunityList)["opportunities"]
        if cards != expected_cards:
            raise CompatibilityError("Opportunity ranking or card values changed in the API")
        # The loader checks every record; route checks sample up to three opportunities.
        checked_jobs = set()
        for card in cards[:3]:
            encoded = quote(card["id"], safe="")
            for offset in dict.fromkeys((0, max(0, card["job_count"] - 1), card["job_count"])):
                actual = get(f"/api/opportunities/{encoded}?offset={offset}&limit=1", OpportunityDetail)
                expected = {**store.get_opportunity_page(card["id"], offset, 1), **store.get_pricing()}
                if actual != expected:
                    raise CompatibilityError("Opportunity detail or pagination values changed in the API")
                for job_id in actual["jobs"]:
                    if job_id not in checked_jobs:
                        checked_jobs.add(job_id)
                        job = get(f"/api/jobs/{job_id}", JobDetail)
                        if job != {**store.get_job(job_id), **store.get_pricing()}:
                            raise CompatibilityError("Job values or evidence changed in the API")
    return requests


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", help="Snapshot path (default: mode path, or ANALYSIS_PATH)")
    parser.add_argument("--mode", choices=("real", "mock"), default="real")
    parser.add_argument("--schema", action="store_true", help="Print the current file JSON Schema and exit")
    parser.add_argument("--check-api", action="store_true", help="Also check read-route compatibility; requires dev dependencies")
    args = parser.parse_args(argv)
    if args.schema:
        if args.path or args.check_api:
            parser.error("--schema cannot be combined with a path or --check-api")
        print(json.dumps(AnalysisSnapshot.model_json_schema(), indent=2, allow_nan=False))
        return 0
    default = STAGE1_MOCK if args.mode == "mock" else PROJECT_ROOT / "generated/analysis.json"
    path = args.path or os.environ.get("ANALYSIS_PATH") or default
    try:
        # Ignore AI/CORS environment: this is an isolated data check.
        settings = Settings(args.mode, Path(path), cors_origins=())
        store = AnalysisStore.load(settings.analysis_path, mode=settings.analysis_mode)
        checks = check_api(settings, store) if args.check_api else None
    except (AnalysisLoadError, CompatibilityError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    report = {
        "valid": True,
        "mode": settings.analysis_mode,
        "counts": store.snapshot_counts(),
        "api_requests_checked": checks,
        "verification_scope": "Schema and reference compatibility only; not analytical or official-data verification",
    }
    print(json.dumps(report, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
