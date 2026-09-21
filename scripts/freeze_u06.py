"""Freeze the master U06 specification and configuration before implementation."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "results/master_revalidation_v01"


def main():
    baseline = json.loads((OUT / "baseline_manifest.json").read_text(encoding="utf-8"))
    if baseline["test_returncode"] != 0 or not baseline["repeat_snapshot_equal"]:
        raise RuntimeError("The pre-U06 baseline gate has not passed")
    paths = [ROOT / "data/input_24h.csv", ROOT / "444.docx", ROOT / "requirements.txt"]
    paths += sorted((ROOT / "config").glob("*.json"))
    paths += sorted((ROOT / "instructions/studies/U06-optimization-model").glob("*.md"))
    paths += [ROOT / "instructions/specs" / p for p in
              ("methods.md", "data.md", "question.md", "execution-policy.md")]
    paths += [OUT / "baseline_manifest.json", OUT / "baseline_tests.txt"]
    record = {
        "unit": "U06", "frozen_at": datetime.now(timezone.utc).isoformat(),
        "rule_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip(),
        "model": "continuous LP as specified on master; no binary variables",
        "tolerance": 1e-6,
        "baseline_test_count": 25,
        "sha256": {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        "config": {p.name: json.loads(p.read_text(encoding="utf-8")) for p in sorted((ROOT / "config").glob("*.json"))},
        "note": "External freeze of the existing master draft. Contradictory verdict clauses are not rewritten.",
    }
    with (OUT / "u06_freeze_record.json").open("x", encoding="utf-8") as handle:
        json.dump(record, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")
    print("U06 master specification and parameters frozen before implementation")


if __name__ == "__main__":
    main()
