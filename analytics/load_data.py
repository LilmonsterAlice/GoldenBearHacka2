"""Read official prepared data in place; never copy or modify the source."""

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

FILES = ("prepped/jobs.parquet", "prepped/gpus.parquet", "synthetic/findings.json")


def resolve_data_dir(path=None):
    """Accept the official repo, track-2 folder, or its data folder."""
    root = Path(path or os.environ.get("CUTSCOPE_DATA_DIR") or
                Path.home() / "Desktop/hackathon-2026-official/track-2/data").expanduser().resolve()
    for candidate in (root, root / "data", root / "track-2/data"):
        if all((candidate / name).is_file() for name in FILES):
            return candidate
    raise FileNotFoundError(f"Official prepared jobs, GPUs and findings not found under {root}")


def source_digest(path):
    """Match the official checksum algorithm (Parquet values, JSON bytes)."""
    digest = hashlib.sha256()
    if path.suffix == ".json":
        digest.update(path.read_bytes())
    else:
        table = pq.read_table(path)
        for name in table.column_names:
            digest.update(json.dumps([name, table.column(name).to_pylist()],
                                     default=str, separators=(",", ":")).encode())
    return digest.hexdigest()


@dataclass
class OfficialData:
    root: Path
    jobs: pd.DataFrame
    gpus: pd.DataFrame
    findings: list[dict]
    provenance: dict


def load_official_data(path=None):
    root = resolve_data_dir(path)
    expected = {}
    manifest = root / "checksums.txt"
    if manifest.exists():
        for line in manifest.read_text().splitlines():
            if line.strip() and not line.startswith("#"):
                checksum, name = line.split()
                expected[name] = checksum
    sources = {}
    for name in FILES:
        actual = source_digest(root / name)
        wanted = expected.get(name)
        if wanted is not None and wanted != actual:
            raise ValueError(f"Official checksum mismatch: {name}")
        sources[name] = {"sha256": actual, "matches_official_manifest":
                         actual == wanted if wanted is not None else None}
    findings = json.loads((root / FILES[2]).read_text())
    if not isinstance(findings, list) or not all(isinstance(x, dict) for x in findings):
        raise ValueError("Findings must be a JSON array of objects")
    return OfficialData(root, pd.read_parquet(root / FILES[0]),
                        pd.read_parquet(root / FILES[1]), findings,
                        {"sources": sources, "checksum_method": "official column-value SHA-256 for Parquet; byte SHA-256 for JSON"})
