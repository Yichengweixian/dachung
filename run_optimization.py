"""Execute the master U06 primary case, preserving failed diagnostics by run ID."""

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys

import pandas as pd

from src.data_loader import load_input_data
from src.optimization_model import DispatchSolveError, solve_dispatch
from src.optimization_validation import audit_dispatch, summarize_dispatch


ROOT = Path(__file__).resolve().parent
FREEZE = ROOT / "results/master_revalidation_v01/u06_freeze_record.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def verify_freeze(frozen):
    for relative, expected in frozen["sha256"].items():
        # Findings are a pre-run snapshot; the result ledger is updated after execution.
        if relative.endswith("/findings.md"):
            continue
        if sha(ROOT / relative) != expected:
            raise ValueError(f"Frozen evidence changed: {relative}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default="U06-master-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", args.run_id):
        parser.error("run-id must be a simple directory name")
    out = ROOT / "results/optimization" / args.run_id
    out.mkdir(parents=True, exist_ok=False)
    source_paths = sorted((ROOT / "src").glob("*.py")) + sorted((ROOT / "tests").glob("test_*.py"))
    source_paths += [Path(__file__).resolve(), ROOT / "requirements.txt"]
    manifest = {
        "run_id": args.run_id, "started_at": datetime.now(timezone.utc).isoformat(),
        "status": "in_progress", "verdict": None,
        "data_scope": "24-hour constructed example, not real grid data; synthetic test costs",
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip(),
        "git_branch": subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT).decode().strip(),
        "code_state": "uncommitted implementation, exact source hashes below",
        "source_sha256": {p.relative_to(ROOT).as_posix(): sha(p) for p in source_paths},
        "python": sys.version, "executable": sys.executable, "platform": platform.platform(),
        "packages": {p: importlib.metadata.version(p) for p in ("numpy", "pandas", "matplotlib", "pulp")},
    }
    try:
        frozen = json.loads(FREEZE.read_text(encoding="utf-8"))
        verify_freeze(frozen)
        manifest["freeze_sha256"] = sha(FREEZE)
        manifest["frozen"] = frozen
        tests = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"],
            cwd=ROOT, capture_output=True, encoding="utf-8", errors="replace",
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
        (out / "tests.txt").write_text(tests.stdout + tests.stderr, encoding="utf-8")
        manifest["test_returncode"] = tests.returncode
        if tests.returncode:
            raise RuntimeError("Regression tests failed; dispatch was not run")
        cfg = frozen["config"]
        dt = cfg["simulation.json"]["time_step_hours"]
        storage = cfg["storage.json"]
        thermal = {"thermal_min_MW": cfg["optimization.json"]["thermal_min_MW"],
                   "thermal_max_MW": cfg["no_storage.json"]["thermal_max_MW"],
                   "thermal_ramp_MW_per_h": cfg["optimization.json"]["thermal_ramp_MW_per_h"]}
        costs = cfg["economics.json"]["parameters"]
        data = load_input_data(ROOT / "data/input_24h.csv", cfg["simulation.json"]["num_steps"], dt)
        result, solver = solve_dispatch(data, storage, thermal, costs, dt)
        manifest["solver"] = {k: v for k, v in solver.items() if k != "cbc_log"}
        (out / "cbc.log").write_text(solver["cbc_log"], encoding="utf-8")
        # An Optimal LP can still violate the separately specified acceptance rule.
        diagnostic = out / "dispatch_hourly.diagnostic.csv"
        result.to_csv(diagnostic, index=False, float_format="%.17g", encoding="utf-8")
        saved = pd.read_csv(diagnostic)
        in_memory = audit_dispatch(result, data, storage, thermal, dt)
        readback = audit_dispatch(saved, data, storage, thermal, dt)
        dump(out / "checks.json", {"in_memory": in_memory, "readback": readback})
        manifest["checks"] = {"in_memory": in_memory, "readback": readback}
        verify_freeze(frozen)
        if not in_memory["passed"] or not readback["passed"]:
            raise RuntimeError("U06 acceptance failed: " + ", ".join(readback["failed_checks"]))
        result.to_csv(out / "dispatch_hourly.csv", index=False, float_format="%.17g", encoding="utf-8")
        summary = summarize_dispatch(saved, costs, dt)
        summary.to_csv(out / "summary.csv", index=False, float_format="%.17g", encoding="utf-8")
        manifest["status"] = "primary_case_checked"
        manifest["verdict"] = "inconclusive"
        manifest["note"] = "Primary numerical checks passed; attribution and robustness remain pending. No U06 supported claim."
        dump(out / "run_manifest.json", manifest)
        print(manifest["note"])
        return 0
    except Exception as exc:
        if isinstance(exc, DispatchSolveError):
            manifest["solver"] = {"solver_status": exc.status}
            (out / "cbc.log").write_text(exc.log, encoding="utf-8")
        manifest.update(status="blocked", verdict="invalid", error=repr(exc))
        manifest["note"] = "Execution acceptance failed; not an economic or capacity conclusion. Dependent experiments stopped."
        dump(out / "failure.json", {"error": repr(exc), "status": "blocked", "verdict": "invalid"})
        dump(out / "run_manifest.json", manifest)
        print(str(exc))
        print("Diagnostics:", out)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
